"""Check normalized tensors from one real image in each experiment split."""

import torch

from bird_dataset import BirdDataset


def main():
    print("=== C1 NORMALIZATION TEST ===")
    for split in ("train", "val", "test"):
        dataset = BirdDataset(split)
        image, label = dataset[0]
        assert tuple(image.shape) == (3, 384, 384)
        assert image.dtype == torch.float32
        assert torch.isfinite(image).all().item()
        assert 0 <= label < 10
        print(
            f"{split} | "
            f"Shape: {tuple(image.shape)} | "
            f"Min: {image.min().item():.4f} | "
            f"Max: {image.max().item():.4f} | "
            f"Mean: {image.mean().item():.4f} | "
            f"Label: {label}"
        )
    print("NORMALIZATION TEST: PASS")


if __name__ == "__main__":
    main()
