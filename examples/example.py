#!/usr/bin/env python3
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from promptkit.core.loader import load_prompt
from promptkit.core.runner import run_prompt
from promptkit.engines.ollama import OllamaEngine
from promptkit.engines.openai import OpenAIEngine
from promptkit.utils.tokens import estimate_cost, estimate_tokens, format_cost


def main() -> int:
    print("PromptKit Example")
    print("=" * 40)

    prompt_path = Path(__file__).parent / "greet_user.yaml"
    print(f"Loading: {prompt_path}")

    try:
        prompt = load_prompt(prompt_path)
        print(f"Loaded: {prompt.name}")
        print(f"Required: {prompt.get_required_inputs()}")
        print(f"Optional: {prompt.get_optional_inputs()}")

        inputs = {"name": "Alice", "context": "PromptKit demo"}

        rendered = prompt.render(inputs)
        print(f"\nRendered:\n{rendered}")

        tokens = estimate_tokens(rendered)
        cost = estimate_cost(tokens, 100, "gpt-4o-mini")
        print(f"\nTokens: {tokens}")
        if cost:
            print(f"Cost: {format_cost(cost)}")

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("\nRunning with OpenAI...")
            engine = OpenAIEngine(api_key=api_key, model="gpt-4o-mini")
            try:
                response = run_prompt(prompt, inputs, engine)
                print(f"Response:\n{response}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("\nSet OPENAI_API_KEY to test with OpenAI")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
