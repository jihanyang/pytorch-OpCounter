from .utils import clever_format
from .profile import profile, profile_origin, profile_acts
from .onnx_profile import OnnxProfile
import torch

default_dtype = torch.float64
