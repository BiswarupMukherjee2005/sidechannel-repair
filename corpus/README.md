# Corpus of bug/fix examples
One JSON file per example, named `example_NNN_short_name.json`:
```json
{
  "title": "short description",
  "status": "verified | PLACEHOLDER",
  "buggy_code": "full Verilog of the flawed design",
  "fixed_code": "full Verilog of the correct fix",
  "explanation": "1-3 sentences: why it leaked and why the fix works",
  "source": "paper / repo / written by the team (with link)"
}
```
Rules
- Only add a fix after Stage 2 (or a teammate who knows masking) has checked it.
- Note the source and its licence for anything copied.
- Currently the first 2 files are put into the prompt as few-shot examples.
- If we add RAG later, the vector index is rebuilt from this folder and is NOT committed.
