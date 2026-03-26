# test_gpu.py - Test DirectML GPU acceleration

import torch_directml
import torch
import time
import psutil
import os

print("=" * 60)
print("DIRECTML GPU TEST")
print("=" * 60)

# Get DirectML device
dml = torch_directml.device()
print(f"✓ DirectML Device: {dml}")
print(f"✓ Device Name: {torch_directml.device_name(0)}")

# Create a large tensor on GPU
size = (16, 32, 720, 1280)  # Large tensor to stress GPU
print(f"\nCreating tensor of size {size} on GPU...")

# Monitor CPU before
cpu_before = psutil.cpu_percent(interval=1)
print(f"CPU before: {cpu_before}%")

# Create tensor and do operations
start_time = time.time()
x = torch.randn(size).to(dml)
y = torch.randn(size).to(dml)

# Do many operations on GPU
for i in range(100):
    z = x + y
    z = z * 0.5
    z = z.mean()
    
    # Force GPU to execute
    if i % 10 == 0:
        print(f"  Iteration {i}: {z.item():.4f}")

elapsed = time.time() - start_time
print(f"\n✓ GPU operations completed in {elapsed:.2f}s")

# Monitor CPU after
cpu_after = psutil.cpu_percent(interval=1)
print(f"CPU after: {cpu_after}%")

print(f"\nCPU Usage Change: {cpu_before}% → {cpu_after}%")
print("\nIf CPU is still high, GPU is not being used properly.")