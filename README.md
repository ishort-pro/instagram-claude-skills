# Instagram Claude Skills: free AI skills for Instagram content creation

**Instagram Claude skills** that write Reels the way creators who grow actually
work: find the outlier Reels in your niche, extract and reverse-engineer their
scripts, write a scored Reel script, generate an **SEO caption from the video
script**, build carousels, plan the week, analyze competitors and fix your bio.
Nine free, MIT-licensed agent skills for **Claude Code, Claude.ai, Claude
Desktop, Codex, Cursor** and any Agent Skills client, with real reel data from
the [IShort MCP](https://ishort.pro/mcp?utm_source=github&utm_medium=readme&utm_campaign=instagram-claude-skills).

> **Nothing gets posted.** These skills write; you post. No Instagram login,
> no scraping, no password ever asked for.

## The 9 skills

| Skill | What it does | IShort MCP tools it uses |
| --- | --- | --- |
| [**instagram-reels-research**](skills/instagram-reels-research/SKILL.md) | Finds viral **outlier Reels** in your niche: ranks by views ÷ the account's own median (not raw views), names the hook formula, writes a swipe file. | `list_my_scripts`, `get_competitor_report`, `get_reel_details` |
| [**instagram-reel-script-extractor**](skills/instagram-reel-script-extractor/SKILL.md) | **Reel script extractor**: pulls the transcript from any reel URL, splits it into timed hook/body/CTA beats, explains why it worked, returns a fill-in template and *your* version. | `transcribe_reel`, `get_reel_details` |
| [**instagram-reel-script-generator**](skills/instagram-reel-script-generator/SKILL.md) | **Reel script generator**: 3 hooks from 26 formulas scored by a hook scorer, the spoken script, on-screen text and a timed beat sheet. | `search_my_scripts`, `list_my_scripts` |
| [**instagram-seo-caption-generator**](skills/instagram-seo-caption-generator/SKILL.md) | **Instagram SEO caption generator from the video script**: mines the keywords the video actually says, puts the primary keyword in the first 125 characters, writes the on-screen title, alt text and 3-5 hashtags, scores the caption /100. | `transcribe_reel`, `search_my_scripts` |
| [**instagram-carousel-generator**](skills/instagram-carousel-generator/SKILL.md) | **Carousel generator**: cover that earns the swipe, one idea per slide, recap slide, alt text per slide. Repurposes your best Reel. | `list_my_scripts` |
| [**instagram-content-calendar**](skills/instagram-content-calendar/SKILL.md) | **Content calendar**: the week of Reels, carousels and stories from evidence, with format, hook formula and keyword per slot. | `list_my_scripts`, `get_bio_analytics` |
| [**instagram-competitor-analysis**](skills/instagram-competitor-analysis/SKILL.md) | **Competitor analysis**: median views, posting pace, outliers, best day/hour, duration and audio vs yours, then a 2-week action list. | `get_competitor_report`, `transcribe_reel` |
| [**instagram-bio-generator**](skills/instagram-bio-generator/SKILL.md) | **Bio generator + profile optimizer**: scores the profile /100, rewrites the searchable name field and bio, reorders your link in bio by real clicks. | `get_my_bio_page`, `get_bio_analytics`, `update_bio_page` |
| [**instagram-humanizer**](skills/instagram-humanizer/SKILL.md) | **Humanizer**: strips em dashes, AI slop words and invisible characters, scores the text on a 5-check AI-detection panel. | — |

They chain: **research → extract → script → SEO caption → humanize → plan**.
A router skill ([`instagram-claude-skills`](skills/instagram-claude-skills/SKILL.md)) sends each request to the right one.

## Install

**Claude Code (plugin, includes the IShort MCP server):**

```
/plugin marketplace add ishort-pro/instagram-claude-skills
/plugin install instagram-claude-skills@instagram-claude-skills
```

**Any agent (skills CLI):**

```bash
npx skills add ishort-pro/instagram-claude-skills --skill '*'   # or one: --skill instagram-seo-caption-generator
```

**Manual (Claude Code, Codex, Cursor, Hermes):**

```bash
git clone https://github.com/ishort-pro/instagram-claude-skills.git
cp -r instagram-claude-skills/skills/* ~/.claude/skills/        # Claude Code
# Codex: ~/.codex/skills/   Hermes: ~/.hermes/skills/
```

**Claude.ai / Claude Desktop:** zip a skill folder (for example
`skills/instagram-seo-caption-generator`) and upload it in
Customize → Skills → Upload a skill. Python tools run where code execution is on.

Then fill in [`templates/brand-voice.md`](templates/brand-voice.md) once (copy
to `~/.instagram-claude-skills/brand-voice.md`). Every writing skill reads it.

## Connect IShort for real data (optional)

Every skill runs on what you paste. Connect the **IShort MCP server**
(`https://ishort.pro/mcp`) and they use real data instead: transcripts of any
reel, your saved script library with views, competitor breakdowns and your
link-in-bio analytics. IShort is a Chrome extension that sorts any public
Instagram profile's Reels by views and outlier score and exports them to CSV;
the free plan includes 500 reels and 10 transcriptions.

- Claude.ai / Desktop / ChatGPT: add a custom connector with the URL above and
  sign in with Google, no key needed.
- Claude Code: installed with the plugin (run `/mcp` to sign in), or
  `claude mcp add --transport http ishort https://ishort.pro/mcp`.
- Full setup and the tool list: [CONNECT-ISHORT.md](CONNECT-ISHORT.md) ·
  [Get the extension](https://chromewebstore.google.com/detail/ljjhbiolkeopnaglmnepmlboldpohohl?utm_source=github&utm_medium=readme&utm_campaign=instagram-claude-skills)

## Tools that actually run

Standard-library Python 3.8+, no network, nothing uploaded.

```bash
# Instagram SEO keywords from a video script, then a caption SEO score /100
python3 skills/instagram-seo-caption-generator/scripts/seo_caption.py \
  --script script.txt --caption caption.txt --primary "instagram posting schedule"

# Rank reels by outlier multiple from an IShort CSV export or MCP JSON
python3 skills/instagram-reels-research/scripts/outliers.py export.csv --min 3

# Score hooks, time a script
python3 skills/instagram-reel-script-generator/scripts/hookscore.py hooks.txt
python3 skills/instagram-reel-script-generator/scripts/beats.py script.txt --target 30

# Humanize and score
python3 skills/instagram-humanizer/scripts/humanize.py draft.txt --report
python3 skills/instagram-humanizer/scripts/detect.py draft.txt
```

Run every tool against the fixtures: `bash tests/run_tests.sh`.

### Measured, not claimed

A caption written the way many big accounts write them (vague first line, a
bracketed keyword dump, `#explore`, two asks) scores **40/100** on the SEO lint.
Rewritten from the same transcript with the primary keyword
`instagram posting schedule`: **94/100**. The one warning left is honest: the
video says every word of the keyword but never as one phrase, so the fix is
one voiceover line. Reproduce it: `bash tests/run_tests.sh` (fixtures in
[`tests/fixtures`](tests/fixtures)). On a real 3.3M-view Reel's caption (not
included; it isn't ours) the same rewrite moved it from 52 to 87.

The hook scorer catches bad hooks well and does **not** pick winners between
two decent ones (the original author measured AUC 0.56 for that). We cap any
hook with a dealbreaker ("stop scrolling", greeting, emoji) at 45 so it can
never outrank a clean hook, which the original did.

## Instagram facts the skills enforce (2026)

- **5 hashtags max** per post or Reel (Instagram, 18 Dec 2025). Hashtags label
  the topic for search; they do not add reach.
- About **125 caption characters** show before "more". That line is the hook
  and, for SEO, the headline.
- Since **10 July 2025**, Google and Bing index public posts from
  professional accounts: caption, alt text, on-screen text. Instagram SEO is
  now regular SEO too.
- Keywords go in the caption, not in a comment.

## FAQ

**What are Claude skills?** Folders with a `SKILL.md` (instructions) and
optional scripts that Claude loads when a task matches. These follow the open
Agent Skills format, so Codex, Cursor and other agents can use them too.

**Can these skills post to Instagram?** No, by design. Automated posting
outside Meta's official API breaks Instagram's terms and gets accounts
restricted. You get a copy-ready block and post it yourself.

**How does the SEO caption generator work?** It mines search phrases from what
the video says (weighted toward the first seconds), you pick and validate a
primary keyword, it writes the caption package, then a lint scores keyword
placement, spoken-keyword match, secondary coverage, hashtags, stuffing,
first line, length and the single ask.

**Do I need IShort?** No. Every skill has a paste-it-in path. IShort replaces
the copy-paste with real transcripts and reel numbers.

**Which languages?** Any. Scripts and captions are written in the video's
language; the keyword miner works on any script, the stop-word list is English.

## Credits

Built by [IShort](https://ishort.pro?utm_source=github&utm_medium=readme&utm_campaign=instagram-claude-skills).
Hook formulas, hook scorer, beat timer, humanizer and profile rubric adapted
from [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill)
by Jake Schincariol (MIT), with fixes listed in [NOTICE](NOTICE). Outlier
method credit: Ava Yuergens (@personalbrandlaunch). MIT licensed.
