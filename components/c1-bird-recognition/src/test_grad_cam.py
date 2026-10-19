"""Functional test for Grad-CAM heatmaps and predicted class indices."""

import torch
import torch.nn as nn

from grad_cam import GradCAM


def main():
    print("=== C1 GRAD-CAM FUNCTIONAL TEST ===")
    torch.manual_seed(42)

    # Small model for a fast CPU test.
    model = nn.Sequential(
        nn.Conv2d(3, 8, kernel_size=3, padding=1),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Linear(8, 10),
    )
    model.eval()
    target_layer = model[1]
    x = torch.randn(2, 3, 32, 32)

    cam_generator = GradCAM(model, target_layer)
    try:
        heatmaps, class_indices = cam_generator.generate(x)
        assert heatmaps.shape == (2, 1, 32, 32)
        assert class_indices.shape == (2,)
        assert torch.isfinite(heatmaps).all().item()
        assert heatmaps.min().item() >= 0
        assert heatmaps.max().item() <= 1
        assert ((class_indices >= 0) & (class_indices < 10)).all().item()

        print("Heatmap shape:", tuple(heatmaps.shape))
        print("Class-index shape:", tuple(class_indices.shape))
        print("Class indices:", class_indices.tolist())
        print("Heatmaps finite:", torch.isfinite(heatmaps).all().item())
        print("Heatmap minimum:", heatmaps.min().item())
        print("Heatmap maximum:", heatmaps.max().item())
        print("GRAD-CAM FUNCTIONAL TEST: PASS")
    finally:
        cam_generator.close()


if __name__ == "__main__":
    main()
