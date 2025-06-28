#!/usr/bin/env python3
"""
Example script demonstrating PromptKit usage.

This script shows how to use PromptKit programmatically
to load prompts and generate responses.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import promptkit
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path modification to avoid issues
from promptkit.core.loader import load_prompt  # noqa: E402
from promptkit.core.runner import run_prompt  # noqa: E402
from promptkit.engines.ollama import OllamaEngine  # noqa: E402
from promptkit.engines.openai import OpenAIEngine  # noqa: E402
from promptkit.utils.tokens import (  # noqa: E402
    estimate_cost,
    estimate_tokens,
    format_cost,
)


def main() -> int:
    """Main example function."""
    print("🤖 PromptKit Example Script")
    print("=" * 40)

    # Load the greeting prompt
    prompt_path = Path(__file__).parent / "greet_user.yaml"
    print(f"Loading prompt from: {prompt_path}")

    try:
        prompt = load_prompt(prompt_path)
        print(f"✅ Loaded prompt: {prompt.name}")
        print(f"   Description: {prompt.description}")
        print(f"   Required inputs: {prompt.get_required_inputs()}")
        print(f"   Optional inputs: {prompt.get_optional_inputs()}")
        print()

        # Example inputs
        inputs = {"name": "Alice", "context": "This is a demo of PromptKit"}

        # Render the prompt
        rendered = prompt.render(inputs)
        print("📝 Rendered Prompt:")
        print("-" * 20)
        print(rendered)
        print("-" * 20)
        print()

        # Estimate tokens and cost
        tokens = estimate_tokens(rendered)
        cost = estimate_cost(tokens, 100, "gpt-4o-mini")

        print(f"📊 Estimated tokens: {tokens}")
        if cost:
            print(f"💰 Estimated cost (gpt-4o-mini): {format_cost(cost)}")
        print()

        # Try to use an engine if API key is available
        api_key = os.getenv("OPENAI_API_KEY")

        if api_key:
            print("🚀 Running with OpenAI...")
            engine = OpenAIEngine(api_key=api_key, model="gpt-4o-mini")

            try:
                response = run_prompt(prompt, inputs, engine)
                print("🤖 AI Response:")
                print("-" * 20)
                print(response)
                print("-" * 20)

            except Exception as e:
                print(f"❌ Error running prompt: {e}")
        else:
            print("ℹ️  Set OPENAI_API_KEY environment variable to test with OpenAI")
            print("   You can also try with Ollama if you have it running locally:")
            print("   ollama pull llama2")

        # Show how to use with Ollama (if available)
        print("\n🦙 Ollama Example (if available):")
        try:
            ollama_engine = OllamaEngine(model="llama2")
            print(f"   Engine info: {ollama_engine.get_model_info()}")
            print("   (Uncomment the next lines to actually run with Ollama)")

            # Uncomment these lines if you have Ollama running:
            # response = run_prompt(prompt, inputs, ollama_engine)
            # print(f"   Response: {response[:100]}...")

        except Exception as e:
            print(f"   Ollama not available: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    print("\n✅ Example completed successfully!")
    print("\nNext steps:")
    print("- Try the CLI: promptkit render examples/greet_user.yaml --name Bob")
    print("- Create your own prompt YAML files")
    print("- Explore the API documentation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
