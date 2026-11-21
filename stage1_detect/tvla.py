"""Test Vector Leakage Assessment (TVLA) engine using Welch's t-test.

Evaluates whether physical traces from Group 0 (Fixed) and Group 1 (Random)
differ significantly at any clock cycle. Threshold |t| > 4.5 corresponds to
leakage with p < 0.00001 (NIST / CRI standard).
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np
from scipy import stats


def compute_welch_t_test(
    group0_traces: np.ndarray,
    group1_traces: np.ndarray,
) -> np.ndarray:
    """Compute Welch's t-statistic for each cycle across traces.

    Args:
        group0_traces: shape [N0, num_cycles]
        group1_traces: shape [N1, num_cycles]

    Returns:
        1D np.ndarray of t-statistics for each cycle of length num_cycles.
    """
    n0 = group0_traces.shape[0]
    n1 = group1_traces.shape[0]

    if n0 < 2 or n1 < 2:
        return np.zeros(group0_traces.shape[1], dtype=np.float64)

    m0 = np.mean(group0_traces, axis=0)
    m1 = np.mean(group1_traces, axis=0)

    # Sample variance (ddof=1)
    s0_sq = np.var(group0_traces, axis=0, ddof=1)
    s1_sq = np.var(group1_traces, axis=0, ddof=1)

    denom = np.sqrt((s0_sq / n0) + (s1_sq / n1))

    # Handle zero-variance cases
    t_stat = np.zeros_like(m0)
    nonzero_mask = denom > 1e-12
    t_stat[nonzero_mask] = (m0[nonzero_mask] - m1[nonzero_mask]) / denom[nonzero_mask]

    # If variance is 0 but means differ, leakage is deterministic
    zero_var_diff = (~nonzero_mask) & (np.abs(m0 - m1) > 1e-9)
    t_stat[zero_var_diff] = np.sign(m0[zero_var_diff] - m1[zero_var_diff]) * 999.0

    return t_stat


def evaluate_tvla(
    synthetic_traces: Dict[str, np.ndarray],
    groups: List[int],
    threshold: float = 4.5,
) -> Tuple[bool, List[Dict[str, Any]], Dict[str, np.ndarray]]:
    """Perform TVLA on all signals and detect significant leaky cycles.

    Args:
        synthetic_traces: Dict mapping signal names to trace matrices [N, C].
        groups: List of group indices (0 = Fixed, 1 = Random) for each trace.
        threshold: Threshold for leakage detection (default 4.5).

    Returns:
        (is_leaky, findings_list, t_stats_by_signal)
    """
    groups_arr = np.array(groups)
    idx_g0 = np.where(groups_arr == 0)[0]
    idx_g1 = np.where(groups_arr == 1)[0]

    findings: List[Dict[str, Any]] = []
    t_stats_by_signal: Dict[str, np.ndarray] = {}

    for sig_name, traces in synthetic_traces.items():
        g0 = traces[idx_g0, :]
        g1 = traces[idx_g1, :]

        t_stat = compute_welch_t_test(g0, g1)
        t_stats_by_signal[sig_name] = t_stat

        # Ignore the synthetic __aggregate__ helper in findings unless needed
        if sig_name == "__aggregate__":
            continue

        abs_t = np.abs(t_stat)
        leaky_cycles = np.where(abs_t > threshold)[0].tolist()

        if leaky_cycles:
            max_t = float(np.max(abs_t))
            findings.append({
                "signal": sig_name,
                "cycles": leaky_cycles,
                "t_statistic": round(max_t, 2),
                "threshold": threshold,
            })

    # Sort findings by highest t_statistic descending
    findings.sort(key=lambda x: x["t_statistic"], reverse=True)
    is_leaky = len(findings) > 0

    return is_leaky, findings, t_stats_by_signal
