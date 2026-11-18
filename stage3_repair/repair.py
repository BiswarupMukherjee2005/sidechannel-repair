"""Stage 3: ask the LLM for a candidate fix and clean up its answer."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .corpus import load_examples
from .prompt import SYSTEM, build_prompt


def extract_verilog(answer: str) -> str | None:
    m = re.search(r"```(?:verilog|v|systemverilog)?\n(.*?)```", answer, re.S)
    return m.group(1).strip() + "\n" if m else None


def syntax_ok(code: str) -> tuple[bool, str]:
    """Cheap gate before the expensive stages. Skipped if Icarus Verilog is not installed."""
    if not shutil.which("iverilog"):
        return True, "iverilog not installed, syntax check skipped"
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "x.v"
        f.write_text(code, encoding="utf-8")
        r = subprocess.run(["iverilog", "-t", "null", str(f)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        return r.returncode == 0, r.stderr.strip()


def ports(code: str) -> str:
    """Rough fingerprint of a module's port list, ignoring comments and spacing."""
    s = re.sub(r"/\*.*?\*/|//[^\n]*", "", code, flags=re.S)
    m = re.search(r"module\s+\w+\s*\((.*?)\)\s*;", s, re.S)
    h = re.sub(r"\b(input|output|inout|reg|wire|logic)\b", "", m.group(1)) if m else ""
    return re.sub(r"\s+", "", h)


def propose_fix(llm, code: str, top: str, report: dict, verdict: dict, history: list[dict]) -> dict:
    """Returns {"code": str|None, "raw": str, "note": str}."""
    raw = llm.complete(SYSTEM, build_prompt(code, top, report, verdict, history, load_examples()))
    new = extract_verilog(raw)
    if new is None:
        return {"code": None, "raw": raw, "note": "LLM reply had no code block"}
    if ports(new) != ports(code):
        return {"code": None, "raw": raw, "note": "fix changed the module's port list"}
    ok, msg = syntax_ok(new)
    if not ok:
        return {"code": None, "raw": raw, "note": f"fix did not compile: {msg[:200]}"}
    return {"code": new, "raw": raw, "note": "candidate produced"}