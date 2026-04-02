import cv2
import numpy as np
import onnxruntime as ort
from tqdm import tqdm
import time

class VideoUpscaler:
    def __init__(self, model_path='nexusnet_enhanced.onnx'):
        print(f"Loading model: {model_path}")
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

        # Get input details
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        # Warm up
        dummy = np.random.randn(1, 3, 720, 1280).astype(np.float32)
        self.session.run([self.output_name], {self.input_name: dummy})
        print("Model loaded successfully")

    def upscale_frame(self, frame):
        """Upscale single frame from 720p to 1080p"""
        # Prepare input
        original_h, original_w = frame.shape[:2]
        input_data = frame.astype(np.float32) / 255.0
        input_data = input_data.transpose(2, 0, 1)[np.newaxis, ...]

        # Run inference
        output = self.session.run([self.output_name], {self.input_name: input_data})[0]

        # Convert back (model output is already in 0-1 range)
        output = (output[0].transpose(1, 2, 0) * 255).astype(np.uint8)
        
        # Ensure exact dimensions
        expected_h, expected_w = int(original_h * 1.5), int(original_w * 1.5)
        if output.shape[0] != expected_h or output.shape[1] != expected_w:
            output = cv2.resize(output, (expected_w, expected_h), interpolation=cv2.INTER_LANCZOS4)

        return output

    def upscale_video(self, input_path, output_path):
        """Upscale entire video"""
        print(f"Processing video: {input_path}")

        # Open video
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Input: {width}x{height}, {fps} FPS, {total_frames} frames")

        # Output dimensions
        out_width = int(width * 1.5)
        out_height = int(height * 1.5)

        print(f"Output: {out_width}x{out_height}")

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (out_width, out_height))

        # Process frames
        frame_count = 0
        start_time = time.time()
        pbar = tqdm(total=total_frames, desc="Upscaling")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            upscaled = self.upscale_frame(frame)
            out.write(upscaled)
            frame_count += 1
            pbar.update(1)

            if frame_count % 100 == 0:
                elapsed = time.time() - start_time
                fps_actual = frame_count / elapsed
                pbar.set_postfix({'FPS': f'{fps_actual:.1f}'})

        cap.release()
        out.release()
        pbar.close()

        elapsed = time.time() - start_time
        print(f'\n✓ Complete! {frame_count} frames in {elapsed:.1f}s ({frame_count/elapsed:.1f} FPS)')
        print(f'  Output saved to: {output_path}')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Upscale 720p video to 1080p')
    parser.add_argument('input', help='Input video file')
    parser.add_argument('output', help='Output video file')
    parser.add_argument('--model', default='nexusnet_enhanced.onnx', help='Model file')
    args = parser.parse_args()

    upscaler = VideoUpscaler(args.model)
    upscaler.upscale_video(args.input, args.output)
