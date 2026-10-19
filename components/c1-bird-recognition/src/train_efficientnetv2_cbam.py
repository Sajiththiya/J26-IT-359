"""Train EfficientNetV2-S with CBAM through the baseline experiment pipeline."""

import train_efficientnetv2_baseline as baseline
from efficientnetv2_cbam import EfficientNetV2CBAM


def build_cbam_model(number_of_classes):
    return EfficientNetV2CBAM(
        num_classes=number_of_classes,
        pretrained=True,
    )


# Reuse the existing training and evaluation pipeline while replacing only
# the model-construction function.
baseline.build_model = build_cbam_model


if __name__ == "__main__":
    baseline.main()
