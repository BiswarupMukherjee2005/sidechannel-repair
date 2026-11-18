# AI-Assisted Detection and Repair of Side-Channel Vulnerabilities

EPICS project, DSN3099 Engineering Projects in Community Service, VIT Bhopal.

A four-stage pipeline: find where a hardware design leaks, prove whether it is secure, ask an AI model to propose a fix, and re-check the fix with the same tools until the design is secure or the attempt limit is reached.

```
Verilog design -> [1 Detect] -> Leakage Report -> [2 Verify] -> Verdict
                       ^                                           |
                       |                       secure? -> done     |
                       +---- [4 Re-verify] <---- [3 Repair (LLM)] <-+
```

## Who owns what

| Stage       | Folder           | Owner                  | Output                               |
| ----------- | ---------------- | ---------------------- | ------------------------------------ |
| 1 Detect    | `stage1_detect/` | Duo 1: Aashish, Naitik | Leakage Report (JSON)                |
| 2 Verify    | `stage2_verify/` | Duo 2: Dev, Pragya     | Verdict (pass/fail + counterexample) |
| 3 Repair    | `stage3_repair/` | Duo 3: Biswa, Aanchal  | Candidate fixed design               |
| 4 Re-verify | `pipeline/`      | Duo 3                  | Loop result                          |

## Folder structure

```
sidechannel-repair/
  README.md
  requirements.txt
  .env.example            copy to .env and add your API key
  designs/                shared sample Verilog designs (add secure + flawed ones)
  docs/
    interfaces.md         formats every stage must follow
    GITHUB_SETUP.md       how to create the repo and set it up
  stage1_detect/          Duo 1 (currently a stand-in)
  stage2_verify/          Duo 2 (currently a stand-in)
  stage3_repair/          prompt, LLM clients, fix extraction, corpus loader
  pipeline/               repair loop and command-line entry point
  corpus/                 bug/fix examples used in the prompt
  tests/
  .vscode/                editor settings (VS Code)
  .github/                pull request template
```

## Setup

Requires Python 3.10 or newer. Icarus Verilog (`iverilog`) is optional now and needed by Stage 1.

```
python -m venv .venv
.venv\Scripts\activate          # Windows;  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env   then add your key
```

## Run

```
python -m pipeline.run designs/flawed_and.v --top flawed_and --llm mock
python -m pipeline.run designs/flawed_and.v --top flawed_and --llm groq     # or gemini, openai, claude
python -m pytest tests -q
```

Stages 1 and 2 are stand-ins that return fake results until Duo 1 and Duo 2 replace them, so `--llm mock` runs the whole loop offline.

## Team rules

- One branch per stage: `stage1-detect`, `stage2-verify`, `stage3-4-repair`. Merge to `main` by pull request.
- Do not change formats in `docs/interfaces.md` without telling everyone.
- Each stage folder has its own README: how to run it and what it outputs.
- Never commit API keys; `.env` is git-ignored.
- Only Stage 1 + Stage 2 decide if a design is secure. The LLM's own claim is never trusted.

## Setting up the repo

See `docs/GITHUB_SETUP.md`.
