"""Verilog simulation runner using Icarus Verilog (iverilog & vvp).

Dynamically synthesizes a testbench, applies TVLA input stimulus,
and records internal signal and register values at each clock cycle.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple


def generate_testbench(
    top_module: str,
    ports_info: Dict[str, Any],
    test_inputs: Dict[str, Any],
    log_filename: str = "sim_signals.log",
) -> str:
    """Generate a Verilog testbench that feeds input traces and logs all signals per cycle."""
    clk_name = ports_info["clock"]
    inputs = ports_info["inputs"]
    outputs = ports_info["outputs"]
    internal_signals = ports_info["internal_signals"]

    # Filter out clock from inputs
    data_inputs = [inp for inp in inputs if inp["name"] != clk_name]

    # Combine signals to monitor: all internal signals + outputs
    monitored = internal_signals + outputs
    # If no internal signals were found, monitor outputs and data inputs
    if not monitored:
        monitored = outputs + data_inputs

    # Signal declarations
    decl_lines = []
    decl_lines.append(f"reg {clk_name} = 0;")
    for inp in data_inputs:
        w_str = f"[{inp['msb']}:{inp['lsb']}] " if inp["width"] > 1 else ""
        decl_lines.append(f"reg {w_str}{inp['name']} = 0;")

    for out in outputs:
        w_str = f"[{out['msb']}:{out['lsb']}] " if out["width"] > 1 else ""
        decl_lines.append(f"wire {w_str}{out['name']};")

    # Instance instantiation
    port_maps = [f".{clk_name}({clk_name})"]
    for inp in data_inputs:
        port_maps.append(f".{inp['name']}({inp['name']})")
    for out in outputs:
        port_maps.append(f".{out['name']}({out['name']})")

    inst_line = f"{top_module} uut (\n        " + ",\n        ".join(port_maps) + "\n    );"

    # Clock generation: period = 10 units (posedge every 10 units)
    clk_gen = f"always #5 {clk_name} = ~{clk_name};"

    # Monitor format string and arguments
    # We will write: trace_idx cycle_idx val1 val2 val3...
    format_parts = ["%0d", "%0d"]
    args = ["t_idx", "c_idx"]
    for sig in monitored:
        format_parts.append("%0d")
        if sig in internal_signals:
            args.append(f"uut.{sig['name']}")
        else:
            args.append(f"{sig['name']}")

    fmt_str = " ".join(format_parts)
    args_str = ", ".join(args)

    # Initial block feeding all traces
    traces = test_inputs["traces"]
    stimulus_lines = []
    stimulus_lines.append("integer log_file;")
    stimulus_lines.append("integer t_idx;")
    stimulus_lines.append("integer c_idx;")
    stimulus_lines.append("initial begin")
    stimulus_lines.append(f'    log_file = $fopen("{log_filename}", "w");')
    stimulus_lines.append("    if (!log_file) begin")
    stimulus_lines.append('        $display("ERROR: Could not open signal log file.");')
    stimulus_lines.append("        $finish;")
    stimulus_lines.append("    end")
    stimulus_lines.append("    #1;")  # small offset from time 0

    for trace in traces:
        t_id = trace["trace_id"]
        stimulus_lines.append(f"    t_idx = {t_id};")
        for c_idx, cycle_data in enumerate(trace["cycles"]):
            stimulus_lines.append(f"    c_idx = {c_idx};")
            # Apply inputs at negedge before posedge
            for sig_name, val in cycle_data.items():
                stimulus_lines.append(f"    {sig_name} = {val};")
            # Wait for posedge clk and settle
            stimulus_lines.append(f"    @(posedge {clk_name});")
            stimulus_lines.append("    #1;")  # allow combinational logic / register update to settle
            stimulus_lines.append(f'    $fdisplay(log_file, "{fmt_str}", {args_str});')

    stimulus_lines.append("    $fclose(log_file);")
    stimulus_lines.append("    $finish;")
    stimulus_lines.append("end")

    tb_code = f"""`timescale 1ns/1ps
module tb_{top_module};
    // Signals
    {chr(10).join("    " + l for l in decl_lines)}

    // Unit Under Test
    {inst_line}

    // Clock
    {clk_gen}

    // Stimulus and Logging
    {chr(10).join("    " + l for l in stimulus_lines)}
endmodule
"""
    return tb_code, [sig["name"] for sig in monitored]


def run_simulation(
    verilog_path: str | Path,
    top_module: str,
    ports_info: Dict[str, Any],
    test_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """Compile and simulate using iverilog, returning signal activity matrices.

    Returns:
        {
            "monitored_signals": [sig1, sig2, ...],
            "signal_values": {
                signal_name: 2D list of shape [num_traces, num_cycles]
            },
            "groups": [group_0_or_1 for each trace]
        }
    """
    if not shutil.which("iverilog") or not shutil.which("vvp"):
        raise EnvironmentError(
            "Icarus Verilog ('iverilog' and 'vvp') is required for simulation. "
            "Please install iverilog via 'sudo apt-get install iverilog'."
        )

    verilog_path = Path(verilog_path).resolve()
    if not verilog_path.exists():
        raise FileNotFoundError(f"Verilog design file not found: {verilog_path}")

    num_traces = len(test_inputs["traces"])
    num_cycles = len(test_inputs["traces"][0]["cycles"])
    groups = [t["group"] for t in test_inputs["traces"]]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        log_file = tmp_path / "sim_signals.log"
        tb_file = tmp_path / f"tb_{top_module}.v"
        vvp_file = tmp_path / f"sim_{top_module}.vvp"

        tb_code, monitored_names = generate_testbench(
            top_module=top_module,
            ports_info=ports_info,
            test_inputs=test_inputs,
            log_filename=str(log_file),
        )
        tb_file.write_text(tb_code, encoding="utf-8")

        # Compile with iverilog
        cmd_compile = [
            "iverilog",
            "-g2005-sv",
            "-o",
            str(vvp_file),
            str(verilog_path),
            str(tb_file),
        ]
        res_compile = subprocess.run(
            cmd_compile,
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )
        if res_compile.returncode != 0:
            raise RuntimeError(
                f"Icarus Verilog compilation failed:\n{res_compile.stderr}\n{res_compile.stdout}"
            )

        # Run with vvp
        cmd_run = ["vvp", str(vvp_file)]
        res_run = subprocess.run(
            cmd_run,
            capture_output=True,
            text=True,
            cwd=tmpdir,
        )
        if res_run.returncode != 0:
            raise RuntimeError(
                f"vvp simulation run failed:\n{res_run.stderr}\n{res_run.stdout}"
            )

        if not log_file.exists():
            raise RuntimeError("Simulation finished but signal log file was not generated.")

        # Initialize matrices
        signal_data: Dict[str, List[List[int]]] = {
            sig: [[0] * num_cycles for _ in range(num_traces)]
            for sig in monitored_names
        }

        # Parse log file
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 2 + len(monitored_names):
                    continue
                t_idx = int(parts[0])
                c_idx = int(parts[1])
                vals = [int(v) if v.isdigit() or (v.startswith('-') and v[1:].isdigit()) else 0 for v in parts[2:]]
                for sig_idx, sig_name in enumerate(monitored_names):
                    if t_idx < num_traces and c_idx < num_cycles:
                        signal_data[sig_name][t_idx][c_idx] = vals[sig_idx]

    return {
        "monitored_signals": monitored_names,
        "signal_values": signal_data,
        "groups": groups,
        "num_traces": num_traces,
        "num_cycles": num_cycles,
    }
