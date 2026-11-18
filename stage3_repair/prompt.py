"""Builds the prompt sent to the LLM."""
import json

SYSTEM = (
    "You are a hardware security engineer. You fix Verilog designs so that they do not leak "
    "secret data through power or EM side channels. Return the COMPLETE corrected Verilog "
    "module inside a single ```verilog code block. Keep the module name and the port list "
    "unchanged. Use plain ASCII characters only, including in comments. After the code block, "
    "write at most three sentences explaining the change."
)

TEMPLATE = """Design (module `{top}`):
```verilog
{code}
```

Stage 1 Leakage Report:
{report}

Stage 2 formal counterexample:
{cex}
{history}
Task: fix the vulnerability so the design is secure. Do not just remove the logic; the circuit
must still compute the same function."""

HISTORY_BLOCK = """
Previous attempts failed. Do not repeat them:
{items}
"""


EXAMPLE_BLOCK = """Example of a flawed design and its correct fix (for reference only):
Flawed:
```verilog
{buggy}
```
Fixed:
```verilog
{fixed}
```
Why: {why}

"""


def build_prompt(code: str, top: str, report: dict, verdict: dict, history: list[dict],
                 examples: list[dict] | None = None) -> str:
    ex = "".join(EXAMPLE_BLOCK.format(buggy=e["buggy_code"], fixed=e["fixed_code"], why=e["explanation"])
                 for e in (examples or []))
    hist = ""
    if history:
        items = "\n".join(f"- Attempt {h['attempt']}: {h['note']}" for h in history)
        hist = HISTORY_BLOCK.format(items=items)
    return ex + TEMPLATE.format(
        top=top, code=code,
        report=json.dumps(report.get("findings", []), indent=2),
        cex=json.dumps(verdict.get("counterexample"), indent=2),
        history=hist,
    )
