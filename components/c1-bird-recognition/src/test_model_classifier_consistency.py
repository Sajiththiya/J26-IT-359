"""Verify identical classifier structure for baseline and CBAM models."""

import torch
from torchvision.models import efficientnet_v2_s

from efficientnetv2_cbam import EfficientNetV2CBAM


def main():
    baseline = efficientnet_v2_s(
        weights=None,
        num_classes=10,
    )
    research = EfficientNetV2CBAM(
        num_classes=10,
        pretrained=False,
    )

    print("=== C1 CLASSIFIER CONSISTENCY CHECK ===")
    print("Baseline classifier:", baseline.classifier)
    print("CBAM classifier:", research.classifier)

    assert isinstance(baseline.classifier[0], torch.nn.Dropout)
    assert isinstance(research.classifier[0], torch.nn.Dropout)
    assert (
        baseline.classifier[0].p == research.classifier[0].p
    ), "Dropout probabilities differ"
    assert (
        baseline.classifier[-1].in_features
        == research.classifier[-1].in_features
    ), "Classifier input dimensions differ"
    assert (
        baseline.classifier[-1].out_features
        == research.classifier[-1].out_features
    ), "Classifier output dimensions differ"

    print("Dropout probability:", baseline.classifier[0].p)
    print("Classifier input features:", baseline.classifier[-1].in_features)
    print("Classifier output features:", baseline.classifier[-1].out_features)
    print("CLASSIFIER CONSISTENCY: PASS")


if __name__ == "__main__":
    main()
