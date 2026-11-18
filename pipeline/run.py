import argparse
import json

try:
    from dotenv import load_dotenv
    load_dotenv()          # reads API keys from .env if python-dotenv is installed
except ImportError:
    pass

from stage3_repair.llm_client import PROVIDERS, get_llm
from .loop import repair_loop

p = argparse.ArgumentParser()
p.add_argument("design")
p.add_argument("--top", required=True)
p.add_argument("--llm", default="mock", choices=list(PROVIDERS))
p.add_argument("--max-attempts", type=int, default=5)
a = p.parse_args()
print(json.dumps(repair_loop(a.design, a.top, get_llm(a.llm), a.max_attempts), indent=2))
