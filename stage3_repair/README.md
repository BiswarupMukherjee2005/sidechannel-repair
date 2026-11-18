# Stage 3: Repair
`repair.propose_fix()` builds a prompt (code + Leakage Report + counterexample + earlier failed attempts),
calls the LLM, extracts the Verilog, and does a quick compile check.
`pipeline/loop.py` then re-runs Stage 1 and Stage 2 on the candidate (Stage 4) and repeats up to N times.
Run tests: `python -m pytest tests -q`
