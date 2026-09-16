# Recording the demo

A 30-second asciinema cast showing a prompt typo caught before it costs anything.
This is the single most persuasive asset the project has — it shows a *bug being
found*, which no feature list can do.

## Once

```bash
brew install asciinema     # or: pipx install asciinema
pip install 'promptkit-core[openai]'
```

## Record

```bash
cd scripts/demo
./setup.sh                 # builds a scratch prompt with a deliberate typo
```

Record the cassette once, so step 7 replays offline during the demo and costs nothing
while you retake it:

```bash
sed -i '' 's/prodcut/product/' support_reply.yaml
export OPENAI_API_KEY=sk-...
promptkit test support_reply.yaml --record --engine openai
./setup.sh                 # puts the typo back, keeps the cassette
```

Now record:

```bash
asciinema rec promptkit.cast \
  --cols 88 --rows 24 --idle-time-limit 1.5 \
  --title "PromptKit: catch prompt typos before you pay for them"
```

Then type the script below. Do not paste — typing reads as real, and the pauses are
what make it legible.

## The script

Seven commands, roughly 30 seconds. Beats matter more than speed.

| # | Command | Beat |
| --- | --- | --- |
| 1 | `cat support_reply.yaml` | Establish: a prompt is a file. Let it sit ~2s |
| 2 | `promptkit lint support_reply.yaml` | **The moment.** Two findings, exit 1. Pause ~3s |
| 3 | `sed -i '' 's/prodcut/product/' support_reply.yaml` | The one-word fix |
| 4 | `promptkit lint support_reply.yaml` | Green tick |
| 5 | `promptkit render support_reply.yaml --set product=Acme --messages` | Roles are real; no API key needed |
| 6 | `promptkit cost support_reply.yaml --model gpt-4o-mini` | Exact tokens, real rates |
| 7 | `promptkit test support_reply.yaml` | Evals pass, replayed from the cassette — no API call |

Stop the recording right after step 7. Resist adding an eighth command.

## What the viewer should take away

Step 2 is the whole pitch: a prompt typo found in 200ms, for free, before a single
token is spent. Everything after it is proof the tool is real.

## Publish

```bash
asciinema upload promptkit.cast
```

Put the link in the README under the tagline, and use the same cast as the first
thing in the Show HN post.

## Notes

- Use a light terminal theme; dark casts are hard to read embedded in a README.
- 88 columns keeps the lint output from wrapping.
- `--idle-time-limit 1.5` trims your typing pauses without making it feel robotic.
- Re-record rather than edit. It takes two minutes and edited casts feel off.
