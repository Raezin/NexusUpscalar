# export_to_onnx.py - Updated for OpenVINO

import torch
import torch.nn as nn
from pathlib import Path
import numpy as np

# Define your model architecture (must match training)
class DetailPreservingBlock(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.conv1 = nn.Conv2d(features, features, 3, 1, 1)
        self.conv2 = nn.Conv2d(features, features, 5, 1, 2)
        self.fuse = nn.Conv2d(features * 2, features, 1, 1, 0)
        self.prelu = nn.PReLU()
        
    def forward(self, x):
        feat1 = self.prelu(self.conv1(x))
        feat2 = self.prelu(self.conv2(x))
        concat = torch.cat([feat1, feat2], dim=1)
        fused = self.fuse(concat)
        return x + fused


class DetailUpscale(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.up1 = nn.Sequential(
            nn.Conv2d(features, features * 4, 3, 1, 1),
            nn.PixelShuffle(2),
            nn.PReLU()
        )
        self.up2 = nn.Sequential(
            nn.Conv2d(features, features * 4, 3, 1, 1),
            nn.PixelShuffle(2),
            nn.PReLU()
        )
        self.refine = nn.Sequential(
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU()
        )
        
    def forward(self, x):
        x = self.up1(x)
        x = self.up2(x)
        h, w = x.shape[2], x.shape[3]
        target_h, target_w = int(h * 0.75), int(w * 0.75)
        x = torch.nn.functional.interpolate(x, size=(target_h, target_w), 
                                            mode='bilinear', align_corners=False)
        x = self.refine(x)
        return x


class NexusNetEnhanced(nn.Module):
    def __init__(self, in_ch=3, out_ch=3, features=32, num_blocks=4):
        super().__init__()
        self.head = nn.Sequential(
            nn.Conv2d(in_ch, features, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU(),
        )
        self.body = nn.Sequential(
            *[DetailPreservingBlock(features) for _ in range(num_blocks)]
        )
        self.residual = nn.Conv2d(features, features, 1, 1, 0)
        self.upscale = DetailUpscale(features)
        self.tail = nn.Sequential(
            nn.Conv2d(features, features // 2, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features // 2, out_ch, 3, 1, 1),
        )
        
    def forward(self, x):
        feat = self.head(x)
        feat = self.body(feat)
        feat = feat + self.residual(feat)
        feat = self.upscale(feat)
        out = self.tail(feat)
        out = torch.clamp(out, 0, 1)
        return out


# Load your trained model
print("Loading PyTorch model...")
checkpoint_path = "model_custom/nexusnet_enhanced_best.pth"
if not Path(checkpoint_path).exists():
    print(f"Model not found at {checkpoint_path}")
    print("Trying alternative paths...")
    alt_paths = [
        "model_custom/nexusnet_best.pth",
        "model_custom/nexusnet_enhanced.pth",
    ]
    for p in alt_paths:
        if Path(p).exists():
            checkpoint_path = p
            break
    else:
        print("❌ No model found!")
        exit(1)

print(f"Using model: {checkpoint_path}")
checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)

# Detect architecture from checkpoint
features = 32
num_blocks = 4
for key in checkpoint['model'].keys():
    if 'head.0.weight' in key:
        features = checkpoint['model'][key].shape[0]
        break
for key in checkpoint['model'].keys():
    if 'body.' in key and 'conv1.weight' in key:
        block_id = int(key.split('.')[1])
        num_blocks = max(num_blocks, block_id + 1)

print(f"Detected: {features} features, {num_blocks} blocks")

# Create model
model = NexusNetEnhanced(in_ch=3, out_ch=3, features=features, num_blocks=num_blocks)
model.load_state_dict(checkpoint['model'])
model.eval()
print("✓ Model loaded")

# Export to ONNX
print("Exporting to ONNX...")
dummy_input = torch.randn(1, 3, 720, 1280)
onnx_path = "model_custom/nexusnet_enhanced.onnx"

# Simplified export for better compatibility
torch.onnx.export(
    model,
    dummy_input,
    onnx_path,
    opset_version=11,
    input_names=['input'],
    output_names=['output'],
    export_params=True,
    do_constant_folding=True,
    verbose=False
)

# Verify the ONNX file
import onnx
onnx_model = onnx.load(onnx_path)
onnx.checker.check_model(onnx_model)
print(f"✓ ONNX model verified")

size_mb = Path(onnx_path).stat().st_size / 1024**2
print(f"✓ Model exported to {onnx_path}")
print(f"  Size: {size_mb:.2f} MB")