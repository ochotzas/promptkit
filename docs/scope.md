# Scope

PromptKit manages prompts: authoring, validating, versioning, rendering, executing, and
testing them. It is deliberately **not** an agent framework.

## Out of scope, permanently

| Not provided | Use instead |
| --- | --- |
| Tool / function calling | The provider SDK directly, or an agent framework |
| Agent loops, planning, multi-step orchestration | LangGraph, the provider Agents SDKs |
| Conversation state and memory across turns | Your application, or a framework |
| Vector stores, retrieval, RAG pipelines | A dedicated retrieval library |
| Fine-tuning and training | Provider tooling |

This is a boundary, not a gap. PromptKit does one layer well and gets out of the way for
the rest. Feature requests for the left column are closed with a pointer to this page.

## The escape hatch

Nothing here traps you. Every engine exposes its underlying SDK client, and every
completion carries the raw provider response:

```python
engine.client  # the openai / anthropic / ollama client
completion.raw  # the provider's own response object
```

So a tool-calling flow that starts from a PromptKit prompt is one attribute access away:

```python
prompt = load_prompt("classify.yaml")
messages = prompt.render_messages({"text": document})

response = engine.client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": m.role, "content": m.content} for m in messages],
    tools=my_tools,
)
```

You keep the prompt as data — versioned, linted, evaluated — and do the agentic part
with the tool built for it.

## Why the boundary exists

Agent frameworks are large, they move quickly, and they disagree with each other. A
prompt-management library that also tried to be one would be worse at both and would
take its abstractions from whichever framework it copied.

The narrow thing PromptKit does — prompts as versioned, lintable, testable data — is the
part nothing else does well, and it composes with every framework precisely because it
does not compete with them.
