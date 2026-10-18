"""Train the C1 EfficientNetV2-S baseline on the provisional manifest."""

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import __version__ as torchvision_version
from torchvision.models import EfficientNet_V2_S_Weights, efficientnet_v2_s

from bird_dataset import BirdDataset
from bird_transforms import IMAGE_SIZE, get_eval_transforms, get_train_transforms


EXPECTED_SPLIT_COUNTS = {"train": 3792, "val": 814, "test": 814}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train an ImageNet-pretrained EfficientNetV2-S C1 baseline."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)


def seed_worker(worker_id):
    del worker_id
    worker_seed = torch.initial_seed() % (2**32)
    random.seed(worker_seed)
    np.random.seed(worker_seed)


def build_datasets():
    datasets = {
        "train": BirdDataset("train", transform=get_train_transforms()),
        "val": BirdDataset("val", transform=get_eval_transforms()),
        "test": BirdDataset("test", transform=get_eval_transforms()),
    }
    actual_counts = {split: len(dataset) for split, dataset in datasets.items()}
    if actual_counts != EXPECTED_SPLIT_COUNTS:
        raise ValueError(
            f"Unexpected included split counts: {actual_counts}; "
            f"expected {EXPECTED_SPLIT_COUNTS}"
        )
    mappings = [dataset.class_to_idx for dataset in datasets.values()]
    if not all(mapping == mappings[0] for mapping in mappings[1:]):
        raise ValueError("Class mappings differ across dataset splits")
    if len(mappings[0]) != 10:
        raise ValueError(f"Expected 10 species, found {len(mappings[0])}")
    return datasets


def build_loaders(datasets, batch_size, num_workers, seed, device):
    generator = torch.Generator()
    generator.manual_seed(seed)
    common = {
        "batch_size": batch_size,
        "num_workers": num_workers,
        "pin_memory": device.type == "cuda",
        "worker_init_fn": seed_worker,
        "persistent_workers": num_workers > 0,
    }
    return {
        "train": DataLoader(
            datasets["train"],
            shuffle=True,
            generator=generator,
            **common,
        ),
        "val": DataLoader(datasets["val"], shuffle=False, **common),
    }


def class_weights(dataset, device):
    counts = Counter(row["species"] for row in dataset.samples)
    total = len(dataset)
    number_of_classes = len(dataset.class_to_idx)
    weights = [
        total / (number_of_classes * counts[species])
        for species in dataset.species
    ]
    return torch.tensor(weights, dtype=torch.float32, device=device), counts


def build_model(number_of_classes):
    model = efficientnet_v2_s(weights=EfficientNet_V2_S_Weights.DEFAULT)
    input_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(input_features, number_of_classes)
    return model


def metrics_from_confusion(confusion, class_names):
    confusion = confusion.to(torch.float64)
    true_positives = confusion.diag()
    predicted = confusion.sum(dim=0)
    actual = confusion.sum(dim=1)
    precision = torch.where(predicted > 0, true_positives / predicted, 0.0)
    recall = torch.where(actual > 0, true_positives / actual, 0.0)
    denominator = precision + recall
    f1 = torch.where(denominator > 0, 2 * precision * recall / denominator, 0.0)
    total = confusion.sum()
    accuracy = (true_positives.sum() / total).item() if total > 0 else 0.0
    per_class = {
        name: {
            "precision": precision[index].item(),
            "recall": recall[index].item(),
            "f1": f1[index].item(),
            "support": int(actual[index].item()),
        }
        for index, name in enumerate(class_names)
    }
    return {
        "accuracy": accuracy,
        "macro_precision": precision.mean().item(),
        "macro_recall": recall.mean().item(),
        "macro_f1": f1.mean().item(),
        "confusion_matrix": confusion.to(torch.int64).tolist(),
        "per_class": per_class,
    }


def run_epoch(model, loader, criterion, device, optimizer=None, scaler=None):
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_images = 0
    confusion = torch.zeros(10, 10, dtype=torch.int64)

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        if training:
            optimizer.zero_grad(set_to_none=True)

        with torch.set_grad_enabled(training):
            with torch.amp.autocast(
                device_type=device.type,
                enabled=device.type == "cuda",
            ):
                logits = model(images)
                loss = criterion(logits, labels)
            if training:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

        batch_size = labels.size(0)
        total_loss += loss.item() * batch_size
        total_images += batch_size
        predictions = logits.argmax(dim=1)
        encoded = labels.detach().cpu() * 10 + predictions.detach().cpu()
        confusion += torch.bincount(encoded, minlength=100).reshape(10, 10)

    return total_loss / total_images, confusion


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def main():
    args = parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.num_workers < 0:
        raise ValueError("Epochs and batch size must be positive; workers cannot be negative")

    set_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("CUDA GPU is required for this 384x384 training run")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    datasets = build_datasets()
    class_to_idx = datasets["train"].class_to_idx
    class_names = datasets["train"].species
    weights, train_counts = class_weights(datasets["train"], device)
    loaders = build_loaders(
        datasets,
        args.batch_size,
        args.num_workers,
        args.seed,
        device,
    )

    model = build_model(len(class_names)).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="max",
        factor=0.5,
        patience=2,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    config = {
        "model": "efficientnet_v2_s",
        "weights": "EfficientNet_V2_S_Weights.IMAGENET1K_V1",
        "image_size": IMAGE_SIZE,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "num_workers": args.num_workers,
        "learning_rate": args.learning_rate,
        "weight_decay": args.weight_decay,
        "seed": args.seed,
        "device": str(device),
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "torchvision": torchvision_version,
        "split_counts": EXPECTED_SPLIT_COUNTS,
        "class_to_idx": class_to_idx,
        "training_class_counts": dict(train_counts),
        "class_weights": weights.detach().cpu().tolist(),
        "checkpoint_selection": "highest validation macro F1",
        "test_set_used_during_training": False,
    }
    write_json(args.output_dir / "config.json", config)

    history = []
    best_macro_f1 = -1.0
    print("=== C1 EFFICIENTNETV2-S BASELINE ===")
    print("Device:", device, "| GPU:", config["gpu"])
    print("Train:", len(datasets["train"]), "| Validation:", len(datasets["val"]))

    for epoch in range(1, args.epochs + 1):
        started = time.time()
        train_loss, train_confusion = run_epoch(
            model,
            loaders["train"],
            criterion,
            device,
            optimizer=optimizer,
            scaler=scaler,
        )
        val_loss, val_confusion = run_epoch(
            model,
            loaders["val"],
            criterion,
            device,
        )
        train_metrics = metrics_from_confusion(train_confusion, class_names)
        val_metrics = metrics_from_confusion(val_confusion, class_names)
        scheduler.step(val_metrics["macro_f1"])

        record = {
            "epoch": epoch,
            "elapsed_seconds": round(time.time() - started, 2),
            "learning_rate": optimizer.param_groups[0]["lr"],
            "train_loss": train_loss,
            "train_accuracy": train_metrics["accuracy"],
            "train_macro_f1": train_metrics["macro_f1"],
            "validation_loss": val_loss,
            "validation_accuracy": val_metrics["accuracy"],
            "validation_macro_f1": val_metrics["macro_f1"],
        }
        history.append(record)
        write_json(args.output_dir / "history.json", history)
        print(
            f"Epoch {epoch:02d}/{args.epochs} | "
            f"train loss {train_loss:.4f} acc {train_metrics['accuracy']:.4f} "
            f"macro-F1 {train_metrics['macro_f1']:.4f} | "
            f"val loss {val_loss:.4f} acc {val_metrics['accuracy']:.4f} "
            f"macro-F1 {val_metrics['macro_f1']:.4f}"
        )

        if val_metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = val_metrics["macro_f1"]
            best_metrics = {
                "epoch": epoch,
                "loss": val_loss,
                **val_metrics,
            }
            write_json(
                args.output_dir / "best_validation_metrics.json",
                best_metrics,
            )
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "class_to_idx": class_to_idx,
                    "validation_metrics": best_metrics,
                    "config": config,
                },
                args.output_dir / "best_model.pt",
            )

    print("Best validation macro F1:", round(best_macro_f1, 6))
    print("Artifacts:", args.output_dir)
    print("TRAINING COMPLETE")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
