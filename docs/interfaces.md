# Interfaces between stages (DRAFT - team must agree before coding)

Every stage is a Python function that takes a Verilog file path and returns a plain dict (JSON-serialisable).

## Stage 1: `stage1_detect.detect.run(verilog_path: str, top_module: str) -> dict`
Leakage Report:
```json
{
  "design": "designs/flawed_and.v",
  "top_module": "flawed_and",
  "leakage_model": "hamming_weight",
  "num_traces": 10000,
  "leaky": true,
  "findings": [
    {"signal": "y", "cycles": [3, 4], "t_statistic": 7.8, "threshold": 4.5}
  ]
}
```
`leaky` is true when any finding is above the threshold. `findings` is empty when `leaky` is false.

## Stage 2: `stage2_verify.verify.run(verilog_path: str, top_module: str) -> dict`
Verdict:
```json
{
  "design": "designs/flawed_and.v",
  "top_module": "flawed_and",
  "property": "non_interference",
  "passed": false,
  "counterexample": {
    "description": "Output y depends on both shares of a without remasking",
    "signals": ["a0", "a1", "y"],
    "details": "free text from the tool"
  }
}
```
`counterexample` is `null` when `passed` is true.

## Stage 3/4: `pipeline.loop.repair_loop(...) -> dict`
Result:
```json
{
  "status": "secure | needs_manual_review",
  "attempts": 2,
  "final_design": "out/flawed_and_fixed.v",
  "history": [ {"attempt": 1, "leaky": true, "passed": false, "note": "..."} ]
}
```

## Open questions to settle as a team
1. Call style: Python functions (as above) or command-line scripts?
2. Is "secure" = Stage 1 says not leaky AND Stage 2 says passed? (proposed: yes, both)
3. Max repair attempts (proposed: 5)
4. Which sample designs do all three duos share? (`designs/`)
