from stage3_repair.llm_client import MockLLM
from pipeline.loop import repair_loop


def test_mock_repair_succeeds(tmp_path):
    r = repair_loop("designs/flawed_and.v", "flawed_and", MockLLM(), out_dir=str(tmp_path))
    assert r["status"] == "secure" and r["attempts"] == 1


class BadLLM:
    def complete(self, system, prompt):
        return "no code here"


def test_gives_up_after_max_attempts(tmp_path):
    r = repair_loop("designs/flawed_and.v", "flawed_and", BadLLM(), max_attempts=2, out_dir=str(tmp_path))
    assert r["status"] == "needs_manual_review" and r["attempts"] == 2
