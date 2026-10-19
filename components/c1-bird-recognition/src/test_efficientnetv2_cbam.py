"""Compare baseline and CBAM model structure using synthetic CPU input."""

import torch
from torchvision.models import efficientnet_v2_s

from efficientnetv2_cbam import EfficientNetV2CBAM


def main():
    print("=== C1 EFFICIENTNETV2 + CBAM TEST ===")
    torch.manual_seed(42)

    baseline = efficientnet_v2_s(
        weights=None,
        num_classes=10,
    )
    research_model = EfficientNetV2CBAM(
        num_classes=10,
        pretrained=False,
    )

    baseline_params = sum(
        parameter.numel() for parameter in baseline.parameters()
    )
    cbam_params = sum(
        parameter.numel() for parameter in research_model.parameters()
    )
    additional_params = cbam_params - baseline_params

    print("Baseline parameters:", baseline_params)
    print("CBAM model parameters:", cbam_params)
    print("Additional parameters:", additional_params)
    assert additional_params == 8290

    feature_shapes = {}

    def record_cbam_shapes(module, inputs, output):
        del module
        feature_shapes["input"] = tuple(inputs[0].shape)
        feature_shapes["output"] = tuple(output.shape)

    hook = research_model.cbam.register_forward_hook(record_cbam_shapes)
    baseline.eval()
    research_model.eval()
    x = torch.randn(1, 3, 128, 128)
    try:
        with torch.no_grad():
            baseline_output = baseline(x)
            cbam_output = research_model(x)
    finally:
        hook.remove()

    assert baseline_output.shape == (1, 10)
    assert cbam_output.shape == (1, 10)
    assert torch.isfinite(baseline_output).all().item()
    assert torch.isfinite(cbam_output).all().item()
    assert feature_shapes["input"] == (1, 256, 4, 4)
    assert feature_shapes["output"] == feature_shapes["input"]

    print("CBAM feature input:", feature_shapes["input"])
    print("CBAM feature output:", feature_shapes["output"])
    print("Baseline output:", tuple(baseline_output.shape))
    print("CBAM output:", tuple(cbam_output.shape))
    print("Outputs finite: True")
    print("CBAM MODEL TEST: PASS")


if __name__ == "__main__":
    main()
