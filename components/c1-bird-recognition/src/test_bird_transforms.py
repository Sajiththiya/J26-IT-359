"""Check shared transformations on real C1 images and evaluation repeatability."""

import torch

from bird_dataset import BirdDataset
from bird_transforms import get_eval_transforms, get_train_transforms


def main():
    print("=== C1 BIRD TRANSFORM TEST ===")
    datasets = {
        "train": BirdDataset("train", transform=get_train_transforms()),
        "val": BirdDataset("val", transform=get_eval_transforms()),
        "test": BirdDataset("test", transform=get_eval_transforms()),
    }
    expected_counts = {"train": 3792, "val": 814, "test": 814}
    for split, dataset in datasets.items():
        assert len(dataset) == expected_counts[split]
        image, label = dataset[0]
        assert image.shape == (3, 384, 384)
        assert image.dtype == torch.float32
        assert torch.isfinite(image).all().item()
        assert 0 <= label < 10
        print(
            f"{split} | "
            f"Images: {len(dataset)} | "
            f"Shape: {tuple(image.shape)} | "
            f"Label: {label}"
        )

    # Evaluation transformations must be deterministic.
    val_image_1, _ = datasets["val"][0]
    val_image_2, _ = datasets["val"][0]
    assert torch.equal(val_image_1, val_image_2), (
        "Validation transformation is not deterministic"
    )
    print("Validation deterministic: True")
    print("BIRD TRANSFORM TEST: PASS")


if __name__ == "__main__":
    main()
