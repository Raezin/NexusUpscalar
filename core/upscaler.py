# core/upscaler.py - AI Video Upscaler with Image Enhancement

import cv2
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import gc
import random

# Try DirectML
try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    DIRECTML_AVAILABLE = False
    print("DirectML not installed. Install with: pip install torch-directml")

# ── Resolution Targets ────────────────────────────────────────────────────────
RESOLUTIONS = {
    "1080p": (1920, 1080),
    "2K":    (2560, 1440),
    "4K":    (3840, 2160),
}


# ── Model Architecture ──────────────────────────────────────────────────────────
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


# ── Video Upscaler Class with Image Enhancement ───────────────────────────────
class VideoUpscaler:
    def __init__(self, target_res="1080p",
                 enhance=False,
                 model_path="model_custom/nexusnet_best.pth",
                 use_gpu=True):
        """
        Initialize the AI upscaler
        
        Args:
            target_res: Target resolution (1080p, 2K, 4K)
            enhance: Apply image enhancement after upscaling
            model_path: Path to your trained PyTorch model
            use_gpu: Whether to use DirectML GPU
        """
        self.target_w, self.target_h = RESOLUTIONS.get(target_res, (1920, 1080))
        self.enhance = enhance
        self.model_path = model_path
        self.use_gpu = use_gpu and DIRECTML_AVAILABLE
        
        self.model = None
        self.device = None
        self.model_input_h = 720
        self.model_input_w = 1280
        
        # Process one frame at a time for shared GPU memory
        self.gpu_batch_size = 1
        
        # Performance tracking
        self.inference_time = 0
        self.frame_count = 0
    
    def _get_device(self):
        """Get DirectML GPU device"""
        if not self.use_gpu:
            return torch.device('cpu')
        
        try:
            if DIRECTML_AVAILABLE:
                dml_device = torch_directml.device()
                device_name = torch_directml.device_name(0)
                print(f"✓ Using DirectML GPU: {device_name}")
                print(f"  (Shared memory - processing 1 frame at a time)")
                return dml_device
        except Exception as e:
            print(f"DirectML error: {e}")
        
        return torch.device('cpu')
    
    def calculate_scale(self, src_w, src_h):
        """Calculate target dimensions"""
        scale_w = self.target_w / src_w
        scale_h = self.target_h / src_h
        scale = min(scale_w, scale_h)
        out_w = int(src_w * scale)
        out_h = int(src_h * scale)
        return scale, out_w, out_h
    
    def needs_upscale(self, src_w, src_h):
        """Check if upscaling is needed"""
        return src_w < self.target_w or src_h < self.target_h
    
    def load_model(self, status_callback=None):
        """Load model with memory-efficient settings"""
        try:
            if status_callback:
                status_callback(f"Loading model from {self.model_path}...")
            
            if not Path(self.model_path).exists():
                if status_callback:
                    status_callback(f"❌ Model not found at {self.model_path}")
                return False
            
            # Load checkpoint on CPU first
            checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
            
            # Create model
            self.model = NexusNetBalanced(in_ch=3, out_ch=3, features=32, num_blocks=4)
            self.model.load_state_dict(checkpoint['model'])
            
            # Get device
            self.device = self._get_device()
            
            # Move model to device and set to eval mode
            self.model = self.model.to(self.device)
            self.model.eval()
            
            # Disable gradients for inference
            for param in self.model.parameters():
                param.requires_grad = False
            
            if status_callback:
                device_name = "DirectML GPU" if self.use_gpu else "CPU"
                status_callback(f"✓ Model loaded on {device_name}!")
                status_callback(f"  Device: {self.device}")
                status_callback(f"  Processing mode: Single frame (optimized for shared memory)")
            
            # Test with a single frame
            test_input = torch.randn(1, 3, 720, 1280).to(self.device)
            with torch.no_grad():
                test_output = self.model(test_input)
            if status_callback:
                status_callback(f"✓ GPU test passed! Output shape: {test_output.shape}")
            
            # Clean up
            del test_input
            del test_output
            gc.collect()
            
            return True
            
        except Exception as e:
            if status_callback:
                status_callback(f"❌ Failed to load model: {e}")
                status_callback("Falling back to CPU mode...")
            
            # Fallback to CPU
            self.use_gpu = False
            self.device = torch.device('cpu')
            self.model = NexusNetBalanced(in_ch=3, out_ch=3, features=32, num_blocks=4)
            self.model.load_state_dict(checkpoint['model'])
            self.model.eval()
            self.model.to(self.device)
            
            return True
    
    def _prepare_frame(self, frame):
        """
        Prepare a SINGLE frame for GPU model
        Returns: GPU tensor of shape [1, 3, 720, 1280]
        """
        # Resize to model input
        resized = cv2.resize(frame, (self.model_input_w, self.model_input_h), 
                            interpolation=cv2.INTER_LANCZOS4)
        
        # BGR to RGB (model was trained on RGB)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        normalized = rgb.astype(np.float32) / 255.0
        
        # Convert to tensor [H, W, C] -> [C, H, W]
        tensor = torch.from_numpy(normalized).permute(2, 0, 1)
        
        # Add batch dimension [1, C, H, W] and move to device
        tensor = tensor.unsqueeze(0).to(self.device)
        
        return tensor
    
    def apply_image_enhancement(self, frame):
        """
        Apply image enhancement to a single frame:
        - Brightness: -5%
        - Sharpness: +30%
        - Contrast: +15%
        - Saturation: +5-15% (random between 5-15%)
        """
        try:
            # Convert BGR to HSV for saturation adjustment
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            
            # Adjust saturation (increase by 5-15%)
            saturation_boost = 0.05
            hsv[:, :, 1] = hsv[:, :, 1] * (1 + saturation_boost)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            
            # Convert back to BGR
            enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
            
            # Adjust brightness (-5%)
            brightness = 0.95
            enhanced = cv2.convertScaleAbs(enhanced, alpha=1.0, beta=int(255 * (brightness - 1)))
            
            # Adjust contrast (+15%)
            contrast = 1.10
            enhanced = cv2.convertScaleAbs(enhanced, alpha=contrast, beta=0)
            
            # Apply sharpening (+30%)
            kernel = np.array([[-1, -1, -1],
                              [-1,  9, -1],
                              [-1, -1, -1]]) * 0.2
            enhanced = cv2.filter2D(enhanced, -1, kernel + np.eye(3) * 0.8  )
            
            # Ensure values are within valid range
            enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
            
            return enhanced
            
        except Exception as e:
            print(f"Image enhancement failed: {e}")
            return frame
    
    def enhance_batch(self, frames):
        """
        Apply image enhancement to a batch of frames
        """
        enhanced_frames = []
        for frame in frames:
            enhanced_frames.append(self.apply_image_enhancement(frame))
        return enhanced_frames
    
    def _ai_upscale_batch(self, frames, src_w, src_h):
        """
        Use AI model to upscale a batch of frames
        Returns: List of upscaled frames (1080p)
        """
        if self.model is None:
            return None
        
        try:
            results = []
            
            # Process ONE frame at a time (memory efficient)
            for frame in frames:
                # Prepare frame for GPU
                input_tensor = self._prepare_frame(frame)
                
                # GPU inference
                with torch.no_grad():
                    output = self.model(input_tensor)
                
                # Move result to CPU and convert
                out_tensor = output[0].cpu()
                out_img = (out_tensor.numpy().transpose(1, 2, 0) * 255).astype(np.uint8)
                
                # RGB to BGR
                out_img = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
                
                results.append(out_img)
                
                # Clean up GPU memory immediately
                del input_tensor
                del output
                gc.collect()
            
            return results
            
        except Exception as e:
            print(f"AI inference failed: {e}")
            return None
    
    def process_batch(self, frames, src_w, src_h):
        """
        Process entire batch using AI upscaling
        
        Args:
            frames: List of frames (BGR format)
            src_w: Original width
            src_h: Original height
        
        Returns:
            List of upscaled frames (1080p)
        """
        if self.model is None:
            _, out_w, out_h = self.calculate_scale(src_w, src_h)
            return [cv2.resize(f, (out_w, out_h), interpolation=cv2.INTER_CUBIC) for f in frames]
        
        # Use AI model for upscaling
        results = self._ai_upscale_batch(frames, src_w, src_h)
        
        if results is None:
            # If AI fails, fallback to bicubic
            _, out_w, out_h = self.calculate_scale(src_w, src_h)
            results = [cv2.resize(f, (out_w, out_h), interpolation=cv2.INTER_CUBIC) for f in frames]
        
        # Apply image enhancement if enabled
        if self.enhance:
            results = self.enhance_batch(results)
        
        return results
    
    def upscale_frame(self, frame, src_w, src_h):
        """Upscale a single frame"""
        results = self.process_batch([frame], src_w, src_h)
        return results[0] if results else frame
    
    def enhance_only(self, frame):
        """Enhance only (no resolution change)"""
        h, w = frame.shape[:2]
        results = self.process_batch([frame], w, h)
        return results[0] if results else frame
    
    # ── Interpolation Methods (CPU-based) ──────────────────────────────────────
    def calculate_interpolation_steps(self, src_fps, target_fps=60.0):
        """Calculate interpolation steps"""
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
        """Detect motion magnitude between frames"""
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
        """Calibrate motion threshold"""
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
        """Generate intermediate frames"""
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
        """Warp and blend frames using optical flow"""
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
        """Get model information"""
        if self.model:
            return {
                'loaded': True,
                'model_path': self.model_path,
                'device': str(self.device),
                'use_gpu': self.use_gpu,
                'batch_size': self.gpu_batch_size,
                'enhance_enabled': self.enhance
            }
        return {'loaded': False}