"""Repair loop (Stage 3 + Stage 4): propose -> re-check with Stage 1 and 2 -> repeat.
We never trust the LLM's claim; only Stage 1 + Stage 2 decide if the design is secure."""
import json
from pathlib import Path

from stage1_detect import detect
from stage2_verify import verify
from stage3_repair.repair import propose_fix


def check(path: str, top: str):
    report = detect.run(path, top)
    verdict = verify.run(path, top)
    secure = (not report["leaky"]) and verdict["passed"]
    return report, verdict, secure


def repair_loop(design: str, top: str, llm, max_attempts: int = 5, out_dir: str = "out") -> dict:
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    code = Path(design).read_text(encoding="utf-8")
    current = design
    history: list[dict] = []

    report, verdict, secure = check(current, top)
    if secure:
        return {"status": "secure", "attempts": 0, "final_design": design, "history": history}

    for attempt in range(1, max_attempts + 1):
        fix = propose_fix(llm, code, top, report, verdict, history)
        if fix["code"] is None:
            history.append({"attempt": attempt, "leaky": None, "passed": None, "note": fix["note"]})
            continue
        current = str(out / f"{top}_attempt{attempt}.v")
        Path(current).write_text(fix["code"], encoding="utf-8")
        new_report, new_verdict, secure = check(current, top)
        history.append({"attempt": attempt, "leaky": new_report["leaky"], "passed": new_verdict["passed"],
                        "note": (new_verdict["counterexample"] or {}).get("description", "verified secure")})
        if secure:
            final = out / f"{top}_fixed.v"
            final.write_text(fix["code"], encoding="utf-8")
            return {"status": "secure", "attempts": attempt, "final_design": str(final), "history": history}
        code, report, verdict = fix["code"], new_report, new_verdict   # refine from the latest failure

    return {"status": "needs_manual_review", "attempts": max_attempts,
            "final_design": current, "history": history}
