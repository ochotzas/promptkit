#!/usr/bin/env bash
set -euo pipefail

# Builds the scratch prompt used by the demo recording.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

rm -rf _partials support_reply.yaml support_reply.evals.yaml
mkdir -p _partials

cat > _partials/house_style.j2 <<'PARTIAL'
Answer in plain language. Prefer short sentences.
PARTIAL

cat > support_reply.yaml <<'PROMPT'
name: support_reply
description: Drafts a customer support reply in the house style
version: 1.0.0
messages:
  - role: system
    template: |
      You are a support agent for {{ prodcut }}.
      {% include '_partials/house_style.j2' %}
  - role: user
    template: |
      Customer wrote: {{ message }}
input_schema:
  product: str
  message: str
PROMPT

cat > support_reply.evals.yaml <<'EVALS'
cases:
  - name: mentions_the_product
    inputs:
      product: Acme Cloud
      message: My invoice looks wrong.
    assert:
      - contains: Acme
      - max_tokens: 400
EVALS

echo "demo scratch built in $here"
echo
echo "Before recording, capture a cassette once so step 7 replays offline:"
echo "  sed -i '' 's/prodcut/product/' support_reply.yaml"
echo "  promptkit test support_reply.yaml --record --engine openai"
echo "  ./setup.sh   # puts the typo back, keeps the cassette"
echo
echo "Then: asciinema rec promptkit.cast --cols 88 --rows 24 --idle-time-limit 1.5"
