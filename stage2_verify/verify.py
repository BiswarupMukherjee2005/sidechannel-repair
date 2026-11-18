"""Stage 2 (Duo 2). STAND-IN: replace the body of run() with the real formal check.
Keep the signature and the returned format (docs/interfaces.md)."""
import re
from pathlib import Path

# Stand-in rule for designs/flawed_and.v only: the bug is XOR-ing two shares of the same secret.
UNMASK = re.compile(r"\b(a0\s*\^\s*a1|a1\s*\^\s*a0|b0\s*\^\s*b1|b1\s*\^\s*b0)\b")


def strip_comments(code: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)


def run(verilog_path: str, top_module: str) -> dict:
    text = strip_comments(Path(verilog_path).read_text(encoding="utf-8"))
    match = UNMASK.search(text)
    passed = match is None
    cex = None if passed else {
        "description": "Output depends on both shares of one secret without remasking",
        "signals": ["a0", "a1", "b0", "b1"],
        "details": f"stand-in counterexample: found '{match.group(0)}'",
    }
    return {"design": verilog_path, "top_module": top_module, "property": "non_interference",
            "passed": passed, "counterexample": cex}