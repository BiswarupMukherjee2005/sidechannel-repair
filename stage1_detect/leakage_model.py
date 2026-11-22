"""Leakage models: Hamming Weight (HW) and Hamming Distance (HD).

In side-channel analysis:
- Hamming Weight: Proportional to static power consumption (number of '1' bits).
- Hamming Distance: Proportional to dynamic switching power (number of bit toggles between consecutive cycles).
"""
from __future__ import annotations

from typing import Dict, List, Literal
import numpy as np


def hamming_weight_int(val: int) -> int:
    """Return the Hamming weight (number of 1s) of an integer."""
    return bin(abs(int(val))).count("1")


def hamming_distance_int(val_prev: int, val_curr: int) -> int:
    """Return the Hamming distance (number of bit transitions) between two integers."""
    return bin(abs(int(val_prev)) ^ abs(int(val_curr))).count("1")


def compute_signal_leakage(
    signal_values: List[List[int]],
    model: Literal["hamming_weight", "hamming_distance"] = "hamming_weight",
) -> np.ndarray:
    """Compute leakage matrix [num_traces, num_cycles] for a given signal."""
    num_traces = len(signal_values)
    num_cycles = len(signal_values[0]) if num_traces > 0 else 0
    leakage = np.zeros((num_traces, num_cycles), dtype=np.float64)

    for i in range(num_traces):
        prev_val = 0
        for c in range(num_cycles):
            curr_val = signal_values[i][c]
            if model == "hamming_weight":
                leakage[i, c] = hamming_weight_int(curr_val)
            elif model == "hamming_distance":
                leakage[i, c] = hamming_distance_int(prev_val, curr_val)
                prev_val = curr_val
            else:
                raise ValueError(f"Unknown leakage model: {model}")

    return leakage


def compute_all_leakage(
    signal_data: Dict[str, List[List[int]]],
    model: Literal["hamming_weight", "hamming_distance"] = "hamming_weight",
) -> Dict[str, np.ndarray]:
    """Compute leakage matrix for all monitored signals plus aggregate circuit activity."""
    leakage_by_signal: Dict[str, np.ndarray] = {}
    aggregate = None

    for sig_name, values in signal_data.items():
        mat = compute_signal_leakage(values, model=model)
        leakage_by_signal[sig_name] = mat
        if aggregate is None:
            aggregate = np.zeros_like(mat)
        aggregate += mat

    if aggregate is not None:
        leakage_by_signal["__aggregate__"] = aggregate

    return leakage_by_signal
