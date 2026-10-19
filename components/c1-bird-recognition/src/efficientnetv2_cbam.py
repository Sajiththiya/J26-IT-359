"""EfficientNetV2-S with CBAM inserted after feature stage 6."""

import torch
import torch.nn as nn
from torchvision.models import (
    EfficientNet_V2_S_Weights,
    efficientnet_v2_s,
)

from cbam import CBAM


class EfficientNetV2CBAM(nn.Module):
    def __init__(self, num_classes=10, pretrained=False):
        super().__init__()
        weights = (
            EfficientNet_V2_S_Weights.IMAGENET1K_V1
            if pretrained
            else None
        )
        backbone = efficientnet_v2_s(weights=weights)
        feature_stages = list(backbone.features.children())

        # Stages 0-6 produce a 256-channel feature map.
        self.features_before_cbam = nn.Sequential(*feature_stages[:7])
        self.cbam = CBAM(
            channels=256,
            reduction=16,
            spatial_kernel=7,
        )
        self.features_after_cbam = nn.Sequential(*feature_stages[7:])
        self.avgpool = backbone.avgpool
        self.classifier = backbone.classifier
        classifier_inputs = self.classifier[1].in_features
        self.classifier[1] = nn.Linear(classifier_inputs, num_classes)

    def forward(self, x):
        x = self.features_before_cbam(x)
        x = self.cbam(x)
        x = self.features_after_cbam(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)
