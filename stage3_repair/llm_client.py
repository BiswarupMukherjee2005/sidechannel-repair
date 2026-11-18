"""One small interface for all LLM providers. Add a provider by adding a class."""
import os
import re


class MockLLM:
    """Offline stand-in. Removes the unmasking XORs from the sample design so the loop can be tested."""
    def complete(self, system: str, prompt: str) -> str:
        code = re.search(r"Design \(module.*?```verilog\n(.*?)```", prompt, re.S).group(1)
        code = code.replace("a0 ^ a1", "a0").replace("b0 ^ b1", "b0")
        return f"```verilog\n{code}```\nMock fix."

class GeminiLLM:
    def __init__(self, model="gemini-2.5-flash"):
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model

    def complete(self, system, prompt):
        from google.genai import types
        r = self.client.models.generate_content(
            model=self.model, contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system))
        return r.text


class OpenAILLM:
    def __init__(self, model="gpt-4o"):
        from openai import OpenAI
        self.client, self.model = OpenAI(), model

    def complete(self, system, prompt):
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
        return r.choices[0].message.content


class ClaudeLLM:
    def __init__(self, model="claude-sonnet-4-5"):
        import anthropic
        self.client, self.model = anthropic.Anthropic(), model

    def complete(self, system, prompt):
        r = self.client.messages.create(
            model=self.model, max_tokens=4000, system=system,
            messages=[{"role": "user", "content": prompt}])
        return r.content[0].text


class GroqLLM(OpenAILLM):
    """Groq (not xAI Grok). Needs GROQ_API_KEY."""
    def __init__(self, model="openai/gpt-oss-120b"):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ["GROQ_API_KEY"],
                             base_url="https://api.groq.com/openai/v1")
        self.model = model


PROVIDERS = {"mock": MockLLM, "gemini": GeminiLLM, "openai": OpenAILLM,
             "claude": ClaudeLLM, "groq": GroqLLM}


def get_llm(name: str):
    return PROVIDERS[name]()
