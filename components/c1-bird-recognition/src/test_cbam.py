"""Verify CBAM shape preservation, finite outputs and gradient flow."""

import torch

from cbam import CBAM


def main():
    print("=== C1 CBAM MODULE TEST ===")
    torch.manual_seed(42)
    model = CBAM(
        channels=256,
        reduction=16,
        spatial_kernel=7,
    )

    # Feature shape observed after EfficientNetV2-S stage 6.
    x = torch.randn(
        2,
        256,
        4,
        4,
        requires_grad=True,
    )
    output = model(x)

    assert output.shape == x.shape, "CBAM changed tensor shape"
    assert torch.isfinite(output).all().item(), "Non-finite output"

    # Verify gradients flow through CBAM.
    loss = output.mean()
    loss.backward()
    assert x.grad is not None, "Input gradient missing"
    assert torch.isfinite(x.grad).all().item(), "Invalid input gradient"

    parameters = list(model.parameters())
    assert all(
        parameter.grad is not None for parameter in parameters
    ), "Some CBAM parameters have no gradients"
    assert all(
        torch.isfinite(parameter.grad).all().item()
        for parameter in parameters
    ), "Invalid parameter gradients"

    print("Input shape:", tuple(x.shape))
    print("Output shape:", tuple(output.shape))
    print("Output finite:", torch.isfinite(output).all().item())
    print("Input gradients valid:", x.grad is not None)
    print("Parameter gradients valid: True")
    print("Trainable parameters:", sum(
        parameter.numel() for parameter in model.parameters()
    ))
    print("CBAM MODULE TEST: PASS")


if __name__ == "__main__":
    main()
