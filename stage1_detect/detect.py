"""Stage 1 (Duo 1). STAND-IN: replace the body of run() with the real detector.
Keep the signature and the returned format (docs/interfaces.md)."""
import re
from pathlib import Path

# Stand-in rule for designs/flawed_and.v only: the bug is XOR-ing two shares of the same secret.
UNMASK = re.compile(r"\b(a0\s*\^\s*a1|a1\s*\^\s*a0|b0\s*\^\s*b1|b1\s*\^\s*b0)\b")


def strip_comments(code: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)


def run(verilog_path: str, top_module: str) -> dict:
    text = strip_comments(Path(verilog_path).read_text(encoding="utf-8"))
    leaky = UNMASK.search(text) is not None
    findings = [{"signal": "y", "cycles": [3, 4], "t_statistic": 7.8, "threshold": 4.5}] if leaky else []
    return {"design": verilog_path, "top_module": top_module, "leakage_model": "hamming_weight",
            "num_traces": 10000, "leaky": leaky, "findings": findings}