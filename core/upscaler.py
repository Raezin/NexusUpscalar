# core/upscaler.py - Auto-Detect Architecture from Checkpoint

import cv2
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import gc
import inspect

# Try DirectML
try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    DIRECTML_AVAILABLE = False
    print("DirectML not installed. Install with: pip install torch-directml")

RESOLUTIONS = {
    "1080p": (1920, 1080),
    "2K":    (2560, 1440),
    "4K":    (3840, 2160),
}


# ── Both Model Architectures ───────────────────────────────────────────────────
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


class EfficientResidualBlock(nn.Module):
    def __init__(self, features, reduction=4):
        super().__init__()
        self.conv1 = nn.Conv2d(features, features, 3, 1, 1)
        self.prelu1 = nn.PReLU()
        self.conv2 = nn.Conv2d(features, features, 3, 1, 1)
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(features, features // reduction, 1),
            nn.PReLU(),
            nn.Conv2d(features // reduction, features, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        residual = self.conv1(x)
        residual = self.prelu1(residual)
        residual = self.conv2(residual)
        attention = self.attention(residual)
        residual = residual * attention
        return x + residual


class EfficientUpscale(nn.Module):
    def __init__(self, features):
        super().__init__()
        self.conv = nn.Conv2d(features, features * 9, 3, 1, 1)
        self.shuffle = nn.PixelShuffle(3)
        self.refine = nn.Sequential(
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU()
        )
    
    def forward(self, x):
        x = self.conv(x)
        x = self.shuffle(x)
        x = nn.functional.avg_pool2d(x, 2, stride=2)
        x = self.refine(x)
        return x


class NexusNetBalanced(nn.Module):
    def __init__(self, in_ch=3, out_ch=3, features=32, num_blocks=4):
        super().__init__()
        self.head = nn.Sequential(
            nn.Conv2d(in_ch, features, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features, features, 3, 1, 1),
            nn.PReLU()
        )
        self.body = nn.Sequential(
            *[EfficientResidualBlock(features) for _ in range(num_blocks)]
        )
        self.upscale = EfficientUpscale(features)
        self.tail = nn.Sequential(
            nn.Conv2d(features, features // 2, 3, 1, 1),
            nn.PReLU(),
            nn.Conv2d(features // 2, out_ch, 3, 1, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        feat = self.head(x)
        feat = self.body(feat)
        feat = self.upscale(feat)
        return self.tail(feat)


# ── Video Upscaler with Auto-Architecture Detection ───────────────────────────
class VideoUpscaler:
    def __init__(self, target_res="1080p",
                 enhance=False,
                 model_path="model_custom/nexusnet_enhanced_best.pth",
                 use_gpu=True):
        self.target_w, self.target_h = RESOLUTIONS.get(target_res, (1920, 1080))
        self.enhance = enhance
        self.model_path = model_path
        self.use_gpu = use_gpu and DIRECTML_AVAILABLE
        
        self.model = None
        self.device = None
        self.model_input_h = 720
        self.model_input_w = 1280
        self.gpu_batch_size = 1
    
    def calculate_scale(self, src_w, src_h):
        scale_w = self.target_w / src_w
        scale_h = self.target_h / src_h
        scale = min(scale_w, scale_h)
        out_w = int(src_w * scale)
        out_h = int(src_h * scale)
        return scale, out_w, out_h
    
    def needs_upscale(self, src_w, src_h):
        return src_w < self.target_w or src_h < self.target_h
    
    def _detect_architecture(self, state_dict):
        """Detect which model architecture was used"""
        keys = list(state_dict.keys())
        
        # Check for Enhanced model features
        has_residual = any('residual.weight' in k for k in keys)
        has_fuse = any('fuse.weight' in k for k in keys)
        has_up1 = any('up1' in k for k in keys)
        has_attention = any('attention' in k for k in keys)
        
        # Detect features
        features = 32
        for key in keys:
            if 'head.0.weight' in key:
                features = state_dict[key].shape[0]
                break
        
        # Detect number of blocks
        num_blocks = 0
        for key in keys:
            if 'body.' in key and 'conv1.weight' in key:
                block_id = int(key.split('.')[1])
                num_blocks = max(num_blocks, block_id + 1)
        if num_blocks == 0:
            num_blocks = 4
        
        # Determine architecture
        if has_residual and has_fuse:
            arch = "enhanced"
        elif has_attention:
            arch = "balanced"
        else:
            arch = "enhanced"  # default
        
        return arch, features, num_blocks
    
    def load_model(self, status_callback=None):
        try:
            if status_callback:
                status_callback(f"Loading model from {self.model_path}...")
            
            if not Path(self.model_path).exists():
                if status_callback:
                    status_callback(f"❌ Model not found at {self.model_path}")
                return False
            
            # Load checkpoint
            checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
            state_dict = checkpoint['model']
            
            # Detect architecture
            arch, features, num_blocks = self._detect_architecture(state_dict)
            
            if status_callback:
                status_callback(f"Detected: {arch.upper()} model")
                status_callback(f"  Features: {features}, Blocks: {num_blocks}")
            
            # Create the correct model
            if arch == "enhanced":
                self.model = NexusNetEnhanced(
                    in_ch=3, out_ch=3, 
                    features=features, 
                    num_blocks=num_blocks
                )
            else:
                self.model = NexusNetBalanced(
                    in_ch=3, out_ch=3, 
                    features=features, 
                    num_blocks=num_blocks
                )
            
            # Load weights
            self.model.load_state_dict(state_dict)
            
            # Get device
            if self.use_gpu and DIRECTML_AVAILABLE:
                self.device = torch_directml.device()
                device_name = torch_directml.device_name(0)
                if status_callback:
                    status_callback(f"✓ Using DirectML GPU: {device_name}")
            else:
                self.device = torch.device('cpu')
                if status_callback:
                    status_callback(f"✓ Using CPU")
            
            # Move model to device
            self.model = self.model.to(self.device)
            self.model.eval()
            
            for param in self.model.parameters():
                param.requires_grad = False
            
            if status_callback:
                status_callback(f"✓ Model loaded successfully!")
                status_callback(f"  Device: {self.device}")
                status_callback(f"  Processing: 1 frame at a time")
            
            # Test with minimal input
            test_input = torch.randn(1, 3, 64, 64).to(self.device)
            with torch.no_grad():
                test_output = self.model(test_input)
            
            del test_input, test_output
            gc.collect()
            
            return True
            
        except Exception as e:
            if status_callback:
                status_callback(f"❌ Failed to load model: {e}")
                status_callback("Using simple OpenCV upscaling as fallback")
            self.model = None  # Fallback to OpenCV
            return True  # Return True to continue with fallback
    
    def _prepare_frame(self, frame):
        resized = cv2.resize(frame, (self.model_input_w, self.model_input_h), 
                            interpolation=cv2.INTER_LANCZOS4)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        tensor = torch.from_numpy(normalized).permute(2, 0, 1)
        tensor = tensor.unsqueeze(0).to(self.device)
        return tensor
    
    def process_batch(self, frames, src_w, src_h):
        # Fallback if model failed to load
        if self.model is None:
            _, out_w, out_h = self.calculate_scale(src_w, src_h)
            results = []
            for frame in frames:
                upscaled = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_LANCZOS4)
                if self.enhance:
                    # Simple enhancement
                    blurred = cv2.GaussianBlur(upscaled, (0, 0), 1.0)
                    upscaled = cv2.addWeighted(upscaled, 1.2, blurred, -0.2, 0)
                results.append(upscaled)
            return results
        
        try:
            results = []
            for frame in frames:
                input_tensor = self._prepare_frame(frame)
                
                with torch.no_grad():
                    output = self.model(input_tensor)
                
                out_tensor = output[0].cpu()
                out_img = (out_tensor.numpy().transpose(1, 2, 0) * 255).astype(np.uint8)
                out_img = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
                
                # Resize to target if needed
                if out_img.shape[0] != self.target_h or out_img.shape[1] != self.target_w:
                    out_img = cv2.resize(out_img, (self.target_w, self.target_h), 
                                        interpolation=cv2.INTER_LANCZOS4)
                
                results.append(out_img)
                
                del input_tensor
                del output
                gc.collect()
            
            return results
            
        except Exception as e:
            print(f"Processing failed: {e}")
            _, out_w, out_h = self.calculate_scale(src_w, src_h)
            return [cv2.resize(f, (out_w, out_h)) for f in frames]
    
    def upscale_frame(self, frame, src_w, src_h):
        results = self.process_batch([frame], src_w, src_h)
        return results[0] if results else frame
    
    def enhance_only(self, frame):
        h, w = frame.shape[:2]
        results = self.process_batch([frame], w, h)
        return results[0] if results else frame
    
    # ── Interpolation Methods ──────────────────────────────────────────────────
    def calculate_interpolation_steps(self, src_fps, target_fps=60.0):
        if src_fps >= target_fps - 0.5:
            return 0, src_fps, "none"
        gap = target_fps - src_fps
        steps = 1
        while src_fps * (steps + 1) < target_fps:
            steps += 1
            if steps > 4:
                break
        output_fps = src_fps * (steps + 1)
        if gap <= 10:
            method = "blend"
        elif gap <= 25:
            method = "light_flow"
        else:
            method = "full_flow"
        return steps, output_fps, method
    
    def detect_motion_magnitude(self, frame_a, frame_b):
        try:
            small_a = cv2.resize(frame_a, (320, 180))
            small_b = cv2.resize(frame_b, (320, 180))
            gray_a = cv2.cvtColor(small_a, cv2.COLOR_BGR2GRAY)
            gray_b = cv2.cvtColor(small_b, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray_a, gray_b)
            return float(np.mean(diff))
        except Exception:
            return 0.0
    
    def calibrate_motion_threshold(self, sample_frames, percentile=60):
        if len(sample_frames) < 2:
            return 10.0
        magnitudes = []
        for i in range(len(sample_frames) - 1):
            mag = self.detect_motion_magnitude(sample_frames[i], sample_frames[i + 1])
            magnitudes.append(mag)
        if not magnitudes:
            return 10.0
        magnitudes.sort()
        idx = int(len(magnitudes) * percentile / 100)
        return magnitudes[min(idx, len(magnitudes) - 1)]
    
    def interpolate_frames(self, frame_a, frame_b, steps=1, method="blend",
                           motion_magnitude=None, motion_threshold=None):
        if steps == 0:
            return []
        if (motion_magnitude is not None and motion_threshold is not None):
            if motion_magnitude > motion_threshold:
                return []
        
        total_steps = steps + 1
        results = []
        
        if method == "blend":
            for i in range(1, total_steps):
                alpha = i / total_steps
                blended = cv2.addWeighted(frame_a, 1.0 - alpha, frame_b, alpha, 0).astype(np.uint8)
                results.append(blended)
        else:
            h, w = frame_a.shape[:2]
            gray_a = cv2.cvtColor(frame_a, cv2.COLOR_BGR2GRAY)
            gray_b = cv2.cvtColor(frame_b, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            
            for i in range(1, total_steps):
                alpha = i / total_steps
                results.append(self._warp_blend(frame_a, frame_b, flow, alpha))
        
        return results
    
    def _warp_blend(self, frame_a, frame_b, flow, alpha):
        h, w = flow.shape[:2]
        grid_x = np.tile(np.arange(w), (h, 1)).astype(np.float32)
        grid_y = np.tile(np.arange(h), (w, 1)).T.astype(np.float32)
        
        map_ax = np.clip(grid_x + flow[:, :, 0] * alpha, 0, w - 1)
        map_ay = np.clip(grid_y + flow[:, :, 1] * alpha, 0, h - 1)
        warped_a = cv2.remap(frame_a, map_ax, map_ay, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        
        map_bx = np.clip(grid_x - flow[:, :, 0] * (1 - alpha), 0, w - 1)
        map_by = np.clip(grid_y - flow[:, :, 1] * (1 - alpha), 0, h - 1)
        warped_b = cv2.remap(frame_b, map_bx, map_by, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        
        return cv2.addWeighted(warped_a, 1.0 - alpha, warped_b, alpha, 0).astype(np.uint8)
    
    def get_model_info(self):
        if self.model:
            return {
                'loaded': True,
                'device': str(self.device),
                'use_gpu': self.use_gpu,
                'batch_size': self.gpu_batch_size
            }
        return {'loaded': False}