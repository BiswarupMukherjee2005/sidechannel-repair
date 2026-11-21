"""Stage 1: Side-Channel Leakage Detection using Simulation and TVLA.

Executes the full pipeline:
1. Parse Verilog and load/generate Test Inputs (Fixed vs Random).
2. Run simulation with Icarus Verilog to obtain cycle-by-cycle signal activity.
3. Compute Leakage Model (Hamming Weight or Hamming Distance).
4. Generate Synthetic Power Traces with realistic Gaussian noise.
5. Perform TVLA (Welch's t-test) to detect significant leaking cycles.
6. Return the standard Leakage Report conforming to docs/interfaces.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .inputs import generate_tvla_inputs, load_test_inputs, parse_verilog_ports
from .leakage_model import compute_all_leakage
from .simulation import run_simulation
from .traces import generate_synthetic_traces
from .tvla import evaluate_tvla


def run(
    verilog_path: str,
    top_module: str,
    test_inputs: Optional[str | Dict[str, Any]] = None,
    num_traces: int = 1000,
    leakage_model: Literal["hamming_weight", "hamming_distance"] = "hamming_weight",
    threshold: float = 4.5,
    noise_std: float = 0.5,
    seed: int = 42,
) -> Dict[str, Any]:
    """Analyze a Verilog design for side-channel leakage.

    Args:
        verilog_path: Path to the target .v design file.
        top_module: Top module name inside the Verilog file.
        test_inputs: Optional path to JSON test vectors or preloaded dict.
        num_traces: Number of traces to simulate for TVLA (default: 1000).
        leakage_model: 'hamming_weight' or 'hamming_distance'.
        threshold: TVLA t-statistic threshold (default: 4.5).
        noise_std: Gaussian noise standard deviation for traces (default: 0.5).
        seed: Random seed for repeatability.

    Returns:
        Dict conforming to docs/interfaces.md:
        {
            "design": str,
            "top_module": str,
            "leakage_model": str,
            "num_traces": int,
            "leaky": bool,
            "findings": [
                {"signal": str, "cycles": List[int], "t_statistic": float, "threshold": float}
            ]
        }
    """
    vpath = Path(verilog_path).resolve()
    if not vpath.exists():
        raise FileNotFoundError(f"Verilog file not found: {verilog_path}")

    code = vpath.read_text(encoding="utf-8")
    ports_info = parse_verilog_ports(code, top_module)

    # 1. Load or Generate Test Inputs
    if test_inputs is not None:
        if isinstance(test_inputs, (str, Path)):
            inputs_data = load_test_inputs(test_inputs)
        elif isinstance(test_inputs, dict):
            inputs_data = test_inputs
        else:
            raise TypeError("test_inputs must be a filepath string, Path, or dict.")
        actual_num_traces = len(inputs_data.get("traces", []))
    else:
        inputs_data = generate_tvla_inputs(
            parsed_ports=ports_info,
            num_traces=num_traces,
            cycles_per_trace=4,
            seed=seed,
        )
        actual_num_traces = num_traces

    # 2. Simulation & Signal Activity Extraction
    sim_result = run_simulation(
        verilog_path=vpath,
        top_module=top_module,
        ports_info=ports_info,
        test_inputs=inputs_data,
    )

    # 3. Leakage Model (Hamming Weight / Distance)
    leakage_by_signal = compute_all_leakage(
        signal_data=sim_result["signal_values"],
        model=leakage_model,
    )

    # 4. Synthetic Traces with Realistic Noise
    synthetic_traces = generate_synthetic_traces(
        leakage_by_signal=leakage_by_signal,
        noise_std=noise_std,
        seed=seed,
    )

    # 5. TVLA Analysis
    is_leaky, findings, _ = evaluate_tvla(
        synthetic_traces=synthetic_traces,
        groups=sim_result["groups"],
        threshold=threshold,
    )

    # 6. Format Report according to docs/interfaces.md
    return {
        "design": str(verilog_path),
        "top_module": top_module,
        "leakage_model": leakage_model,
        "num_traces": actual_num_traces,
        "leaky": is_leaky,
        "findings": findings if is_leaky else [],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Stage 1 Detect: Side-channel leakage detection via simulation, power traces, and TVLA."
    )
    parser.add_argument("design", help="Path to Verilog design file (.v)")
    parser.add_argument("--top", required=True, help="Name of top module")
    parser.add_argument("--test-inputs", default=None, help="Path to JSON test inputs file")
    parser.add_argument("--traces", type=int, default=1000, help="Number of traces to simulate (default: 1000)")
    parser.add_argument(
        "--model",
        choices=["hamming_weight", "hamming_distance"],
        default="hamming_weight",
        help="Leakage model (default: hamming_weight)",
    )
    parser.add_argument("--threshold", type=float, default=4.5, help="TVLA threshold (default: 4.5)")
    parser.add_argument("--noise-std", type=float, default=0.5, help="Trace noise std dev (default: 0.5)")
    parser.add_argument("--out", default=None, help="Save JSON report to output file")

    args = parser.parse_args()

    report = run(
        verilog_path=args.design,
        top_module=args.top,
        test_inputs=args.test_inputs,
        num_traces=args.traces,
        leakage_model=args.model,
        threshold=args.threshold,
        noise_std=args.noise_std,
    )

    output_json = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(output_json, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
