"""Verify the container's actual GPU execution before downloading model weights."""
import importlib.metadata
import json
import torch
from earth2studio.models.px import FCN
from earth2studio.models.dx import PrecipitationAFNO
from earth2studio.data import GFS

assert torch.cuda.is_available(), 'CUDA unavailable'
x = torch.arange(16, device='cuda', dtype=torch.float32).reshape(4, 4)
y = x @ x.T
torch.cuda.synchronize()
assert torch.isfinite(y).all().item()
print(json.dumps({
    'torch': torch.__version__, 'cuda': torch.version.cuda,
    'earth2studio': importlib.metadata.version('earth2studio'),
    'gpu': torch.cuda.get_device_name(0),
    'capability': torch.cuda.get_device_capability(0),
    'gpu_matrix_test': 'passed',
    'model_inference': 'not tested by this script',
}, indent=2))
