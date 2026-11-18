"""Loads bug/fix examples from corpus/*.json for use as few-shot examples in the prompt."""
import json
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent.parent / "corpus"


def load_examples(n: int = 2) -> list[dict]:
    files = sorted(CORPUS_DIR.glob("*.json"))[:n]
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]
