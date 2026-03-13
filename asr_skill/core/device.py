"""Hardware detection module for ASR pipeline.

This module provides automatic device detection for optimal hardware utilization
across different platforms (CUDA GPU, Apple MPS, and CPU fallback).

Detection Priority: MPS > CUDA > CPU
- MPS (Metal Performance Shaders) is prioritized for Apple Silicon Macs
- CUDA is used for NVIDIA GPU systems
- CPU is the universal fallback

The priority order ensures:
1. Apple Silicon users get GPU acceleration via MPS
2. NVIDIA GPU users get CUDA acceleration
3. All other systems gracefully fall back to CPU
"""

import os
import torch


def get_device() -> str:
    """Detect the optimal compute device for inference.

    Detection priority is MPS > CUDA > CPU to prioritize Apple Silicon support.

    Returns:
        str: Device string - "mps", "cuda:0", or "cpu"
    """
    # Allow forcing CPU via environment variable
    if os.environ.get("ASR_FORCE_CPU") == "1":
        return "cpu"

    # NOTE: MPS (Metal Performance Shaders) on Apple Silicon has issues with float64.
    # We now handle this in models.py by setting default dtype to float32 when MPS is used.
    # So we can safely default to MPS on macOS.
    
    # Check Apple Silicon MPS first (highest priority)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    # Check NVIDIA CUDA
    if torch.cuda.is_available():
        return "cuda:0"

    # Fallback to CPU
    return "cpu"


def get_device_with_fallback() -> tuple[str, bool]:
    """Detect device and indicate if GPU fallback occurred.

    This function helps notify users when GPU acceleration is not available
    and CPU fallback is being used, which has significant performance impact
    (typically 10x slower than GPU).

    Returns:
        tuple[str, bool]: A tuple of (device_string, fallback_occurred)
            - device_string: "mps", "cuda:0", or "cpu"
            - fallback_occurred: True if using CPU when GPU was expected
    """
    device = get_device()

    # CPU is considered a fallback only if a GPU was expected but unavailable
    # This occurs when the system has GPU hardware but it's not accessible
    if device == "cpu":
        # Check if any GPU capability exists but is not available
        has_cuda_hardware = False
        has_mps_hardware = False

        try:
            has_cuda_hardware = torch.cuda.device_count() > 0
        except Exception:
            pass

        try:
            has_mps_hardware = (
                hasattr(torch.backends, "mps")
                and torch.backends.mps.is_built()
            )
        except Exception:
            pass

        # Fallback occurred if GPU hardware exists but is unavailable
        fallback = has_cuda_hardware or has_mps_hardware
        return "cpu", fallback

    return device, False
