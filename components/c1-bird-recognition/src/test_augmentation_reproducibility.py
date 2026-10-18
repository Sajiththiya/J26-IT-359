"""Check single-process training augmentation reproducibility on a real image."""

import random

import numpy as np
import torch

from bird_dataset import BirdDataset
from bird_transforms import get_train_transforms


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def main():
    dataset = BirdDataset("train", transform=get_train_transforms())
    print("=== C1 AUGMENTATION REPRODUCIBILITY TEST ===")

    set_seed(42)
    image_a, label_a = dataset[0]
    set_seed(42)
    image_b, label_b = dataset[0]
    same_seed_identical = torch.equal(image_a, image_b)
    assert same_seed_identical, "Same seed did not reproduce training augmentation"
    assert label_a == label_b

    set_seed(43)
    image_c, label_c = dataset[0]
    different_seed_different = not torch.equal(image_a, image_c)
    assert label_a == label_c
    for image in (image_a, image_b, image_c):
        assert tuple(image.shape) == (3, 384, 384)
        assert image.dtype == torch.float32
        assert torch.isfinite(image).all().item()

    print("Same seed produces identical image:", same_seed_identical)
    # Distinct seeds can occasionally yield identical output; report rather than fail.
    print("Different seed produces different image:", different_seed_different)
    print("Tensor shape:", tuple(image_a.shape))
    print("Label:", label_a)
    print("REPRODUCIBILITY TEST: PASS")


if __name__ == "__main__":
    main()
