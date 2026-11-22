"""Test input vector generation and file loading for TVLA side-channel analysis.

Supports:
1. Loading custom test vectors from a JSON file.
2. Auto-generating Fixed vs. Random (non-specific TVLA) test vectors for masked designs.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_verilog_ports(code: str, top_module: str) -> Dict[str, Any]:
    """Extract inputs, outputs, and internal signals from a Verilog module."""
    # Strip comments
    clean_code = re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)

    # Find the target module definition
    mod_pattern = rf"module\s+{re.escape(top_module)}\s*(?:#\s*\(.*?\)\s*)?\((.*?)\)\s*;(.*?)endmodule"
    m = re.search(mod_pattern, clean_code, re.S)
    if not m:
        # Check if ports are declared inside body: module top; input ...; ... endmodule
        mod_pattern_body = rf"module\s+{re.escape(top_module)}\s*(?:#\s*\(.*?\)\s*)?(?:\((.*?)\))?\s*;(.*?)endmodule"
        m = re.search(mod_pattern_body, clean_code, re.S)
        if not m:
            raise ValueError(f"Module '{top_module}' not found in Verilog code.")

    header_text = m.group(1) or ""
    body_text = m.group(2) or ""
    combined = header_text + "\n" + body_text

    inputs: List[Dict[str, Any]] = []
    outputs: List[Dict[str, Any]] = []
    signals: List[Dict[str, Any]] = []

    # Helper to parse declarations like: input [7:0] a, b; or input a0, a1,
    def extract_decls(keyword: str, text: str) -> List[Dict[str, Any]]:
        results = []
        pattern = rf"\b{keyword}\b(?:\s+(?:reg|wire|logic))?(?:\s*\[(\d+):(\d+)\])?(.*?)(?=(?:\b(?:input|output|inout|wire|reg)\b)|;|\)|$)"
        for match in re.finditer(pattern, text, re.S):
            msb = int(match.group(1)) if match.group(1) is not None else 0
            lsb = int(match.group(2)) if match.group(2) is not None else 0
            width = abs(msb - lsb) + 1
            raw_names = match.group(3)
            names = [n.strip() for n in raw_names.split(",") if n.strip()]
            for name in names:
                clean_name = re.split(r"[\s=]", name)[0].strip()
                if clean_name and re.match(r"^[a-zA-Z_]\w*$", clean_name):
                    results.append({"name": clean_name, "width": width, "msb": msb, "lsb": lsb})
        return results

    inputs = extract_decls("input", combined)
    outputs = extract_decls("output", combined)

    # Internal wires and registers
    wires = extract_decls("wire", body_text)
    regs = extract_decls("reg", body_text)
    input_names = {inp["name"] for inp in inputs}
    output_names = {out["name"] for out in outputs}

    seen = set()
    for item in wires + regs:
        if item["name"] not in input_names and item["name"] not in seen:
            signals.append(item)
            seen.add(item["name"])

    # Clock detection
    clk_name = "clk"
    for inp in inputs:
        if "clk" in inp["name"].lower() or "clock" in inp["name"].lower():
            clk_name = inp["name"]
            break

    return {
        "top_module": top_module,
        "clock": clk_name,
        "inputs": inputs,
        "outputs": outputs,
        "internal_signals": signals,
    }


def generate_tvla_inputs(
    parsed_ports: Dict[str, Any],
    num_traces: int = 1000,
    cycles_per_trace: int = 4,
    seed: int = 42,
) -> Dict[str, Any]:
    """Auto-generate TVLA stimulus vectors for Fixed vs. Random evaluation.

    Traces are split 50/50:
    - Group 0 (Fixed secret): Secret bit(s) are held constant (e.g., 0) while
      shares are generated randomly.
    - Group 1 (Random secret): Secret bit(s) are randomly chosen per trace.
    Random masks/noise inputs (like 'r', 'mask', 'rnd') are purely random across all traces.
    """
    rng = random.Random(seed)
    inputs = parsed_ports["inputs"]
    clk_name = parsed_ports["clock"]

    # Filter out clock
    data_inputs = [inp for inp in inputs if inp["name"] != clk_name]

    # Identify share pairs if available (e.g. a0/a1, b0/b1 or _share0/_share1)
    # Group inputs by root prefix
    name_to_input = {inp["name"]: inp for inp in data_inputs}
    share_pairs = []
    used_names = set()

    # Look for pair patterns: a0 and a1, or a_0 and a_1
    for name in name_to_input:
        if name in used_names:
            continue
        m = re.match(r"^([a-zA-Z_]\w*?)(?:_)?([01])$", name)
        if m:
            root, share_idx = m.group(1), m.group(2)
            sibling = f"{root}1" if share_idx == "0" else f"{root}0"
            alt_sibling = f"{root}_1" if share_idx == "0" else f"{root}_0"
            partner = sibling if sibling in name_to_input else (alt_sibling if alt_sibling in name_to_input else None)
            if partner and partner not in used_names:
                share_pairs.append((root, name_to_input[name], name_to_input[partner]))
                used_names.add(name)
                used_names.add(partner)

    unpaired_inputs = [inp for inp in data_inputs if inp["name"] not in used_names]

    traces = []
    for i in range(num_traces):
        # Even indices = Group 0 (Fixed), Odd indices = Group 1 (Random)
        group = 0 if (i % 2 == 0) else 1
        trace_cycles: List[Dict[str, int]] = []

        # For fixed group, secret is constant 0; for random group, secret is randomly 0 or 1
        secret_vals = {}
        for root, s0, s1 in share_pairs:
            width = s0["width"]
            max_val = (1 << width) - 1
            if group == 0:
                secret_vals[root] = 0
            else:
                secret_vals[root] = rng.randint(0, max_val)

        for c in range(cycles_per_trace):
            cycle_inputs: Dict[str, int] = {}

            # Generate shares: share0 = random, share1 = secret ^ share0
            for root, s0, s1 in share_pairs:
                width = s0["width"]
                max_val = (1 << width) - 1
                val_s0 = rng.randint(0, max_val)
                val_s1 = secret_vals[root] ^ val_s0
                cycle_inputs[s0["name"]] = val_s0
                cycle_inputs[s1["name"]] = val_s1

            # Other inputs (masks, random bits, control)
            for inp in unpaired_inputs:
                width = inp["width"]
                max_val = (1 << width) - 1
                cycle_inputs[inp["name"]] = rng.randint(0, max_val)

            trace_cycles.append(cycle_inputs)

        traces.append({
            "trace_id": i,
            "group": group,  # 0: Fixed, 1: Random
            "cycles": trace_cycles,
        })

    return {
        "num_traces": num_traces,
        "cycles_per_trace": cycles_per_trace,
        "traces": traces,
    }


def load_test_inputs(filepath: str | Path) -> Dict[str, Any]:
    """Load test inputs from a JSON file."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Test inputs file not found: {filepath}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_test_inputs(data: Dict[str, Any], filepath: str | Path) -> None:
    """Save test inputs to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
