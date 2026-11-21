"""Synthetic power trace generation with realistic electronic noise.

Models physical oscilloscope measurement of power consumption:
P_trace(t) = P_leakage(t) + N(0, sigma^2)
"""
from __future__ import annotations

from typing import Dict
import numpy as np


def add_gaussian_noise(
    traces: np.ndarray,
    noise_std: float = 0.5,
    seed: int | None = None,
) -> np.ndarray:
    """Add zero-mean Gaussian noise to simulated power traces."""
    if noise_std <= 0:
        return traces.copy()
    rng = np.random.default_rng(seed)
    noise = rng.normal(loc=0.0, scale=noise_std, size=traces.shape)
    return traces + noise


def generate_synthetic_traces(
    leakage_by_signal: Dict[str, np.ndarray],
    noise_std: float = 0.5,
    seed: int = 12345,
) -> Dict[str, np.ndarray]:
    """Generate noisy synthetic power traces for each signal and overall circuit."""
    noisy_traces: Dict[str, np.ndarray] = {}
    for sig_name, mat in leakage_by_signal.items():
        noisy_traces[sig_name] = add_gaussian_noise(mat, noise_std=noise_std, seed=seed)
    return noisy_traces
