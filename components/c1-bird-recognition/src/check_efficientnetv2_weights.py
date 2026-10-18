"""Print installed Torchvision EfficientNetV2-S pretrained preprocessing."""

from torchvision.models import EfficientNet_V2_S_Weights


def main():
    weights = EfficientNet_V2_S_Weights.DEFAULT
    preprocessing = weights.transforms()
    print("=== C1 EFFICIENTNETV2 WEIGHTS CHECK ===")
    print("Model: EfficientNetV2-S")
    print("Weights:", weights)
    print("Preprocessing:", preprocessing)
    print("====================================")


if __name__ == "__main__":
    main()
