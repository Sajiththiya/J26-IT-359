"""Check single-process batch loading of real C1 experiment images."""

import torch
from torch.utils.data import DataLoader

from bird_dataset import BirdDataset
from bird_transforms import get_eval_transforms, get_train_transforms


def main():
    print("=== C1 BIRD DATALOADER TEST ===")
    datasets = {
        "train": BirdDataset("train", transform=get_train_transforms()),
        "val": BirdDataset("val", transform=get_eval_transforms()),
        "test": BirdDataset("test", transform=get_eval_transforms()),
    }
    for split, dataset in datasets.items():
        loader = DataLoader(
            dataset,
            batch_size=4,
            shuffle=(split == "train"),
            num_workers=0,
        )
        images, labels = next(iter(loader))
        assert images.shape == (4, 3, 384, 384)
        assert labels.shape == (4,)
        assert images.dtype == torch.float32
        assert labels.dtype == torch.int64
        assert torch.isfinite(images).all().item()
        assert ((labels >= 0) & (labels < 10)).all().item()
        print(
            f"{split} | "
            f"Dataset: {len(dataset)} | "
            f"Batch: {tuple(images.shape)} | "
            f"Labels: {labels.tolist()}"
        )
    print("DATALOADER TEST: PASS")


if __name__ == "__main__":
    main()
