"""Minimal Grad-CAM implementation for C1 model interpretation."""

import torch
import torch.nn.functional as F


class GradCAM:
    """Grad-CAM for a chosen feature layer."""

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.activations = None
        self.gradients = None
        self.forward_handle = target_layer.register_forward_hook(
            self._save_activations
        )

    def _save_activations(self, module, inputs, output):
        del module, inputs
        self.activations = output
        if output.requires_grad:
            output.register_hook(self._save_gradients)

    def _save_gradients(self, gradient):
        self.gradients = gradient.detach()

    def generate(self, input_tensor, class_idx=None):
        """Return normalized ``(N, 1, H, W)`` heatmaps and class indices."""

        self.model.eval()
        self.model.zero_grad(set_to_none=True)
        self.activations = None
        self.gradients = None

        with torch.enable_grad():
            logits = self.model(input_tensor)
            if logits.ndim != 2:
                raise ValueError("Expected model logits with shape (N, classes)")

            batch_size = logits.shape[0]
            if class_idx is None:
                class_indices = logits.argmax(dim=1)
            elif isinstance(class_idx, int):
                class_indices = torch.full(
                    (batch_size,),
                    class_idx,
                    dtype=torch.long,
                    device=logits.device,
                )
            else:
                class_indices = torch.as_tensor(
                    class_idx,
                    dtype=torch.long,
                    device=logits.device,
                ).reshape(-1)
                if class_indices.numel() != batch_size:
                    raise ValueError(
                        "class_idx must contain one class index per input"
                    )

            if torch.any(class_indices < 0) or torch.any(
                class_indices >= logits.shape[1]
            ):
                raise ValueError("class_idx is outside the model output range")

            scores = logits.gather(1, class_indices.unsqueeze(1)).sum()
            scores.backward()

        if self.activations is None:
            raise RuntimeError("Target layer did not produce activations")
        if self.gradients is None:
            raise RuntimeError("Target layer did not receive gradients")
        if self.activations.shape != self.gradients.shape:
            raise RuntimeError("Activation and gradient shapes differ")

        channel_weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        heatmaps = torch.sum(
            channel_weights * self.activations,
            dim=1,
            keepdim=True,
        )
        heatmaps = F.relu(heatmaps)
        heatmaps = F.interpolate(
            heatmaps,
            size=input_tensor.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )

        flattened = heatmaps.flatten(start_dim=1)
        minimum = flattened.min(dim=1).values.reshape(-1, 1, 1, 1)
        maximum = flattened.max(dim=1).values.reshape(-1, 1, 1, 1)
        heatmaps = (heatmaps - minimum) / (maximum - minimum).clamp_min(1e-8)
        return heatmaps.detach(), class_indices.detach()

    def close(self):
        """Remove the forward hook registered on the target layer."""

        self.forward_handle.remove()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
