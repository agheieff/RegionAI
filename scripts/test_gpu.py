#!/usr/bin/env python3
"""Test GPU availability and PyTorch configuration."""

import torch
import sys


def test_gpu():
    print("PyTorch Version:", torch.__version__)
    print("-" * 50)
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Number of GPUs: {torch.cuda.device_count()}")
        
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            print(f"\nGPU {i}: {props.name}")
            print(f"  Memory: {props.total_memory / 1024**3:.2f} GB")
            print(f"  Compute Capability: {props.major}.{props.minor}")
    
    print("\n" + "-" * 50)
    print("Testing tensor operations...")
    
    device = "cuda" if cuda_available else "cpu"
    print(f"Using device: {device}")
    
    try:
        x = torch.randn(1000, 1000, device=device)
        y = torch.randn(1000, 1000, device=device)
        z = torch.matmul(x, y)
        print(f"Matrix multiplication successful on {device}")
        print(f"Result shape: {z.shape}")
        
        if cuda_available:
            torch.cuda.synchronize()
            print("GPU synchronization successful")
    except Exception as e:
        print(f"Error during tensor operations: {e}")
        return False
    
    print("\n✓ GPU test completed successfully!" if cuda_available else "\n✓ CPU test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_gpu()
    sys.exit(0 if success else 1)