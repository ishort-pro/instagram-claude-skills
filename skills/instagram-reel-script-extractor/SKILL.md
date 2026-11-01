---
name: instagram-reel-script-extractor
description: >-
  Reverse-engineer any Instagram Reel: extract the script (transcript) from a
  reel URL, split it into hook / stake / body / payoff / CTA beats with timings,
  name the hook formula, explain why it worked against the account's average,
  and turn it into a fill-in-the-blank template rewritten for the user's own
  brand. Use when the user pastes a reel link and says "get the script", "reel
  script extractor", "transcribe this reel", "break down this reel", "why did
  this go viral", "reverse engineer", "steal this format", or "make my version".
  Uses the IShort MCP transcribe_reel and get_reel_details tools.
---

# Instagram Reel script extractor (reverse engineering)

**Rule one: never write "your version" from the caption.** The caption is not
the script. Get what was actually said, then take it apart.

## Step 1. Get the real script and the numbers

| Have | Do |
| --- | --- |
| IShort MCP connected | `transcribe_reel(url)` for the transcript (cached = free; new = 1 quota). `get_reel_details(url)` for views, likes, comments, duration. If the account has a report, `get_competitor_report(handle)` gives `stats.medianViews` for the multiple. |
| User pasted a transcript | use it; ask for views and the account's typical views if they want the "why". |
| Only a URL, no IShort | ask for the transcript, or point once to IShort's free transcription (`../../CONNECT-ISHORT.md`). Never guess what a video says. |

If a tool reports Instagram is blocking lookups, wait a few minutes or ask the
user to paste. Do not loop.

Also ask for (or watch, if the session can) the visuals: what is on screen in
the first frame, cuts per 10 seconds, on-screen text, face vs screen-record.
Text-only analysis misses half of why a Reel holds.

## Step 2. Time it and split it into beats

Save the transcript and run the beat timer from the script generator:

```bash
python3 ../instagram-reel-script-generator/scripts/beats.py transcript.txt
python3 ../instagram-reel-script-generator/scripts/hookscore.py --hook "<first line>"
```

Label every line with its job:

```
HOOK     0:00-0:03  the claim or promise. Name the formula (hooks.json id).
STAKE    0:03-0:07  why the viewer should care.
BODY     ...        one idea per beat. Note where the frame changes.
PAYOFF              where the hook's promise is delivered.
CTA                 the one ask (or none).
LOOP                does the last line echo the first? (rewatch fuel)
```

## Step 3. Explain why it worked (with numbers, not vibes)

- **Multiple**: views / account median. Under 1.5x it did not "go viral",
  it had a normal day; say so and stop pretending to explain a hit.
- **Hook**: formula, words, seconds to say, where the payload sits.
- **Retention mechanics**: open loop, list count ("3 mistakes"), pattern
  interrupt, payoff placement, length vs the niche norm.
- **Engagement shape**: comments/likes ratio high = debate or keyword bait;
  saves/shares (when the export has them) = reference value.

## Step 4. The template, then the user's version

```
TEMPLATE  (blanks in {curly})
  HOOK    "{number} {thing your audience does} that {cost} - and the {fix} nobody uses"
  STAKE   ...
  BODY    {step 1} / {step 2} / {step 3}
  PAYOFF  ...
  CTA     ...

YOUR VERSION  (from brand-voice.md + the user's topic)
  full script, same beat count, same length +-10%
```

Read `~/.instagram-claude-skills/brand-voice.md` for voice. If missing, ask
for 3 of the user's reels (IShort: `search_my_scripts` / `list_my_scripts`
with their own handle) and infer it.

Then hand off: script to `instagram-reel-script-generator` for hook scoring
and the beat sheet, caption to `instagram-seo-caption-generator`.

## Rules

- Copy structure, never words. Lines lifted from someone else's script are
  theirs. Their numbers and stories are never "yours".
- No invented results. Missing a number: `{{your number}}` and a flag.
- One reel is an anecdote. Recommend running `instagram-reels-research` before
  betting a content month on one breakdown.
