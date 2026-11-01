#!/usr/bin/env python3
"""
seo_caption.py - turn a Reel's video script (transcript) into Instagram SEO
keywords, then lint a caption against them so the post can be found in
Instagram Search AND in Google/Bing.

Why the script matters: Instagram Search matches what people type against the
caption, the on-screen text, the spoken audio (auto-captions) and the profile.
Since 10 July 2025, public posts from professional accounts are also indexed by
Google and Bing (caption, alt text, on-screen text). A caption whose keywords
the video never says, or a video whose topic the caption never names, is
invisible to both. So the keywords come FROM the script, and the caption has
to carry them in the places search engines weigh.

Two modes, one command:

  keywords   python3 seo_caption.py --script script.txt
             -> ranked keyword phrases mined from the script, a suggested
                primary keyword, and where it was spoken (first 3s or not)

  lint       python3 seo_caption.py --script script.txt --caption caption.txt \
                                    --primary "instagram reels analytics"
             -> SEO score /100 with PASS/WARN/FAIL per check, the feed window
                (first ~125 chars), and the fixes in priority order

Options: --secondary "a,b"  --json  --lang en  --truncate 125
The script may be a raw transcript, an IShort transcribe_reel result (the JSON
metadata line at the end is ignored), or a written script with timecodes.

Heuristics, not a ranking guarantee. Nothing here calls Instagram or Google.
Python 3.8+, standard library only.
"""

import argparse
import collections
import json
import re
import sys

TRUNCATE = 125
LIMIT = 2200
HASHTAG_LIMIT = 5            # Instagram cap per post/Reel since 18 Dec 2025
HASHTAG_RE = re.compile(r"(?:^|\s)#([\w]+)", re.UNICODE)
WORD_RE = re.compile(r"[^\W_][\w'’-]*", re.UNICODE)
FILLER_TAGS = {"viral", "fyp", "explore", "explorepage", "foryou", "foryoupage", "reels",
               "reelsinstagram", "instagood", "trending", "instadaily", "follow", "like4like",
               "followforfollowback", "reelitfeelit", "instareels"}

STOP = set("""
a an the and or but if then so to of in on at by for with from as is are was were be been being
it its it's this that these those there here i me my we our us you your you're yours he she they
them their his her what which who whom whose when where why how all any both each few more most
other some such no nor not only own same than too very can will just don't dont should now do does
did doing have has had having am im i'm i've ive you've we're they're let's lets get got go going
gonna wanna like really actually basically literally okay ok yeah yes hey hi guys one two also
into out up down over under again further once about after before because while during until
make made thing things way something anything everything someone video reel today here's that's
what's it'll you'll we'll i'll would could might must need want know think say said see look
right well even still back much many lot lots every
""".split())
WEAK_HEADS = {"want", "need", "know", "think", "make", "get", "go", "say", "see", "look", "use"}


def clean_script(raw):
    lines = []
    for l in raw.splitlines():
        s = l.strip()
        if not s:
            continue
        if s.startswith("{") and s.endswith("}") and '"cached"' in s or '"language"' in s and s.startswith("{"):
            continue                                   # IShort transcribe_reel metadata line
        s = re.sub(r"^\[?\(?\d{1,2}:\d{2}(?:[.:]\d+)?\)?\]?\s*[-–:]?\s*", "", s)   # timecodes
        s = re.sub(r"^(HOOK|STAKE|BODY|PAYOFF|CTA|LOOP|MID|BEAT \d+)\s*[:\-–]\s*", "", s, flags=re.I)
        lines.append(s)
    return " ".join(lines)


def tokens(text):
    return [w.lower().strip("'’-") for w in WORD_RE.findall(text)]


def ngrams(toks, n):
    for i in range(len(toks) - n + 1):
        yield i, tuple(toks[i:i + n])


INTERNAL_OK = {"of", "for", "to", "on", "in", "with", "and", "from", "vs", "&"}
WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}


def is_content(w):
    return (w not in STOP and w not in WEEKDAYS and len(w) >= 3 and not w.isdigit()
            and w not in WEAK_HEADS)


def stem(w):
    for suf in ("ings", "ing", "ers", "er", "ies", "es", "s", "ed"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def segments(script):
    """Phrases never cross a sentence or clause break."""
    return [tokens(seg) for seg in re.split(r"[.!?;:,\n।]+", script) if seg.strip()]


def mine_keywords(script, top=15):
    """Rank search phrases a viewer might type, mined from what the video says.

    A phrase scores on how often its content words recur in the script (topic
    weight), how often the whole phrase recurs, and whether it is said in the
    hook. Only prepositions may sit inside a phrase ("posting schedule for
    beginners" yes, "post or carousel" no)."""
    toks = tokens(script)
    total = max(1, len(toks))
    early = max(8, int(total * 0.12))           # roughly the first 3-5 seconds
    freq = collections.Counter(stem(w) for w in toks if is_content(w))
    cands = {}
    offset = 0
    grams = []
    for seg in segments(script):
        for n in (1, 2, 3, 4):
            for i, g in ngrams(seg, n):
                grams.append((offset + i, g))
        offset += len(seg)
    for i, g in grams:
        if True:
            if not (is_content(g[0]) and is_content(g[-1])):
                continue
            if any(not is_content(w) and w not in INTERNAL_OK for w in g[1:-1]):
                continue
            if len(set(g)) < len(g):
                continue
            c = cands.setdefault(g, {"count": 0, "first": i})
            c["count"] += 1
    scored = []
    for g, c in cands.items():
        content = [w for w in g if is_content(w)]
        topic = sum(freq[stem(w)] for w in content) / (len(content) ** 0.5)
        sc = topic * (c["count"] ** 0.7)
        if len(g) in (2, 3):
            sc *= 1.6                           # how people actually search
        elif len(g) == 4:
            sc *= 1.2
        if c["first"] < early:
            sc *= 1.5                           # said in the hook: Instagram hears it first
        if len(g) == 1 and freq[stem(g[0])] < 2:
            continue
        scored.append((g, round(sc, 1), c))
    scored.sort(key=lambda t: (-t[1], t[2]["first"]))
    kept = []
    for g, sc, c in scored:
        words = set(stem(w) for w in g if is_content(w))
        clash = False
        for k in kept:
            kw = set(stem(w) for w in k["phrase"].split())
            if words <= kw or (len(words & kw) >= 2):
                clash = True
                break
        if clash:
            continue
        kept.append({"phrase": " ".join(g), "score": sc, "count": c["count"],
                     "in_hook": c["first"] < early, "words": len(g)})
        if len(kept) >= top:
            break
    return kept, early


def suggest_primary(kws):
    # Prefer a 2-4 word phrase said more than once or said in the hook.
    for k in kws:
        if 2 <= k["words"] <= 4:
            return k["phrase"]
    return kws[0]["phrase"] if kws else ""


def contains(text, phrase):
    """Loose match: every word of the phrase, in order, allowing up to 2 words between."""
    words = [re.escape(w) for w in phrase.lower().split()]
    if not words:
        return False
    pat = r"\b" + r"(?:\W+\w+){0,2}?\W+".join(words) + r"(?:s|es)?\b"
    return re.search(pat, text.lower()) is not None


def lint(script, caption, primary, secondary, cut=TRUNCATE):
    cap = caption.strip()
    flat = re.sub(r"\s+", " ", cap)
    window = flat[:cut]
    first_line = cap.split("\n")[0].strip()
    first_sentence = re.split(r"(?<=[.!?])\s", flat, maxsplit=1)[0]
    tags = HASHTAG_RE.findall(cap)
    body_wo_tags = HASHTAG_RE.sub(" ", cap)
    script_l = script.lower()
    script_toks = tokens(script)
    hook_text = " ".join(script_toks[:max(8, int(len(script_toks) * 0.12))])
    checks = []

    def add(name, status, weight, detail, fix=""):
        checks.append({"check": name, "status": status, "weight": weight, "detail": detail, "fix": fix})

    # 1. primary keyword placement
    if not primary:
        add("PRIMARY KEYWORD", "FAIL", 20, "no primary keyword given or found",
            "Pick the 2-4 word phrase a viewer would type to find this Reel.")
    elif contains(first_sentence, primary):
        add("PRIMARY KEYWORD", "PASS", 20, f"\"{primary}\" is in the first sentence")
    elif contains(window, primary):
        add("PRIMARY KEYWORD", "WARN", 20, f"\"{primary}\" is visible before \"more\" but not in the first sentence",
            "Move it into the first sentence, the part Instagram and Google weigh as the headline.")
    elif contains(body_wo_tags, primary):
        add("PRIMARY KEYWORD", "FAIL", 20, f"\"{primary}\" only appears below the fold",
            f"Rewrite line one so it names \"{primary}\" in plain words within {cut} characters.")
    else:
        add("PRIMARY KEYWORD", "FAIL", 20, f"\"{primary}\" is not in the caption at all",
            f"Name \"{primary}\" in the first line. A hashtag alone does not count.")

    # 2. the video says it too (audio + auto-captions are searchable)
    if primary:
        if contains(hook_text, primary):
            add("SPOKEN IN HOOK", "PASS", 12, "the script says the primary keyword in the first seconds")
        elif contains(script_l, primary):
            add("SPOKEN IN HOOK", "WARN", 12, "the script says it, but not in the hook",
                "Say the keyword in the first 3 seconds and put it in the on-screen title.")
        elif all(stem(w) in {stem(t) for t in script_toks} for w in primary.split() if is_content(w)):
            add("SPOKEN IN HOOK", "WARN", 12, "the video says every word of the keyword, but not as one phrase",
                f"Say \"{primary}\" as one phrase in the hook, and put it in the on-screen title.")
        else:
            add("SPOKEN IN HOOK", "FAIL", 12, "the video never says the primary keyword",
                "Either pick a keyword the script actually says, or add one line to the voiceover that says it.")

    # 3. secondary keyword coverage
    if secondary:
        hit = [k for k in secondary if contains(body_wo_tags, k)]
        st = "PASS" if len(hit) >= min(2, len(secondary)) else ("WARN" if hit else "FAIL")
        add("SECONDARY KEYWORDS", st, 12, f"{len(hit)}/{len(secondary)} in the caption body"
            + (f"; missing: {', '.join(k for k in secondary if k not in hit)}" if len(hit) < len(secondary) else ""),
            "Work the missing ones into the body as natural sentences, not a list.")

    # 4. script <-> caption topical match
    kws, _ = mine_keywords(script, top=10)
    multi = [k["phrase"] for k in kws if k["words"] >= 2][:6] or [k["phrase"] for k in kws[:6]]
    covered = [p for p in multi if contains(body_wo_tags, p)]
    ratio = len(covered) / max(1, len(multi))
    add("SCRIPT MATCH", "PASS" if ratio >= 0.34 else ("WARN" if covered else "FAIL"), 12,
        f"{len(covered)}/{len(multi)} of the script's top phrases appear in the caption"
        + (f" ({', '.join(covered[:3])})" if covered else ""),
        "Reuse the exact words the video says; search matches audio and caption together. "
        f"Candidates: {', '.join(p for p in multi if p not in covered)[:140]}")

    # 5. hashtags
    low_tags = [t.lower() for t in tags]
    filler = [t for t in low_tags if t in FILLER_TAGS]
    prim_tag = primary.replace(" ", "").lower() if primary else ""
    tag_has_kw = any(prim_tag and (prim_tag in t or t in prim_tag) for t in low_tags) or any(
        all(w in t for w in primary.lower().split()[:2]) for t in low_tags) if primary else False
    if len(tags) > HASHTAG_LIMIT:
        add("HASHTAGS", "FAIL", 10, f"{len(tags)} hashtags; Instagram allows {HASHTAG_LIMIT} since Dec 2025 and rejects more",
            "Keep 3-5: one topic tag with the keyword, one niche tag, one community tag.")
    elif not tags:
        add("HASHTAGS", "WARN", 10, "no hashtags", "Add 3-5 specific tags; they label the topic for search (not reach).")
    elif filler:
        add("HASHTAGS", "WARN", 10, f"filler tags carry no topic: #{', #'.join(filler)}",
            "Swap them for tags someone would actually search in your niche.")
    elif not tag_has_kw:
        add("HASHTAGS", "WARN", 10, f"{len(tags)} tags, none carries the primary keyword",
            f"Make one tag the keyword itself, e.g. #{prim_tag[:30]}.")
    else:
        add("HASHTAGS", "PASS", 10, f"{len(tags)} tags, keyword tag present")

    # 6. keyword stuffing
    worst = 0
    for k in [primary] + list(secondary or []):
        if k:
            worst = max(worst, len(re.findall(re.escape(k.lower()), cap.lower())))
    bracket_dump = re.search(r"\[[^\]]*(,[^\]]*){3,}\]", cap) or re.search(r"(?im)^\s*(keywords?|tags?)\s*:", cap)
    if worst > 3 or bracket_dump:
        add("NO STUFFING", "WARN", 8,
            ("a bracketed keyword list" if bracket_dump else f"a keyword repeated {worst} times"),
            "Say each keyword once or twice in real sentences. Lists read as spam to people and to Instagram.")
    else:
        add("NO STUFFING", "PASS", 8, "keywords used naturally")

    # 7. hook / first line hygiene
    if not first_line or first_line.startswith(("#", "@")):
        add("FIRST LINE", "FAIL", 8, "opens on a hashtag, mention or blank line",
            "Line one is the search headline. Open with the keyword-bearing hook.")
    elif re.match(r"(?i)^\s*(hey|hi|hello|in today'?s|in this (video|reel)|stop scrolling)", first_line):
        add("FIRST LINE", "WARN", 8, "opens on a greeting or preamble", "Open on the payoff, with the keyword.")
    else:
        add("FIRST LINE", "PASS", 8, f"{len(first_line)} chars, opens on content")

    # 8. length: room for search terms without becoming an essay
    n = len(cap)
    if n > LIMIT:
        add("LENGTH", "FAIL", 6, f"{n}/{LIMIT} chars, over the limit", "Cut it.")
    elif n < 140:
        add("LENGTH", "WARN", 6, f"{n} chars, too short to carry secondary keywords",
            "Add 2-4 short lines of context that use the secondary keywords.")
    elif n > 1500:
        add("LENGTH", "WARN", 6, f"{n} chars; long captions get skimmed", "Aim for 300-1,200.")
    else:
        add("LENGTH", "PASS", 6, f"{n} chars")

    # 9. one clear ask
    asks = re.findall(r"(?i)\b(comment|save this|save it|share this|send this|dm me|link in bio|follow)\b", cap)
    kinds = {a.lower().split()[0] for a in asks}
    add("ONE ASK", "PASS" if len(kinds) == 1 else "WARN", 6,
        f"{len(kinds)} different asks" + (f": {', '.join(sorted(kinds))}" if kinds else ""),
        "One ask. Saves and sends are the strongest signals; pick one.")

    pts = {"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0}
    total_w = sum(c["weight"] for c in checks)
    score = round(100 * sum(pts[c["status"]] * c["weight"] for c in checks) / total_w)
    verdict = "READY" if score >= 80 and not any(c["status"] == "FAIL" for c in checks) else "FIX"
    return {"score": score, "verdict": verdict, "window": window, "truncated": len(flat) > cut,
            "primary": primary, "secondary": secondary, "checks": checks}


def render_keywords(kws, early, primary, out=sys.stdout):
    print("\nKEYWORDS FROM THE SCRIPT", file=out)
    print("=" * 62, file=out)
    for k in kws:
        mark = "HOOK" if k["in_hook"] else "    "
        print(f"  {k['score']:>5}  {mark}  x{k['count']:<2} {k['phrase']}", file=out)
    print("-" * 62, file=out)
    print(f"  suggested primary: \"{primary}\"", file=out)
    print("  HOOK = said in roughly the first 3-5 seconds (first "
          f"{early} words). Validate volume before you commit:\n"
          "  type the phrase into Instagram Search and Google; keep it if real posts rank for it.\n", file=out)


def render_lint(a, out=sys.stdout):
    print(f"\nINSTAGRAM SEO CAPTION  ·  score {a['score']}/100  ·  {a['verdict']}", file=out)
    print("=" * 66, file=out)
    print("  WHAT THE FEED (AND GOOGLE'S SNIPPET) SHOWS FIRST", file=out)
    w = a["window"]
    for i in range(0, len(w), 56):
        print(f"  | {w[i:i + 56]:<56} |", file=out)
    print(f"  +{'-' * 46}{' ... more' if a['truncated'] else '-' * 9}-+\n", file=out)
    for c in a["checks"]:
        print(f"  {c['status']:<5} {c['check']:<19} {c['detail']}", file=out)
    fixes = [c for c in a["checks"] if c["status"] != "PASS" and c["fix"]]
    fixes.sort(key=lambda c: (c["status"] != "FAIL", -c["weight"]))
    if fixes:
        print("-" * 66 + "\n  FIX, IN THIS ORDER", file=out)
        for i, c in enumerate(fixes, 1):
            print(f"  {i}. [{c['check']}] {c['fix']}", file=out)
    print("", file=out)


def read(path):
    if path == "-":
        return sys.stdin.read()
    return open(path, encoding="utf-8").read()


def main():
    ap = argparse.ArgumentParser(description="Instagram SEO keywords from a video script, and a caption SEO lint.")
    ap.add_argument("--script", required=True, help="transcript / video script file (or - for stdin)")
    ap.add_argument("--caption", help="caption draft to lint")
    ap.add_argument("--primary", help="primary keyword (default: suggested from the script)")
    ap.add_argument("--secondary", default="", help="comma-separated secondary keywords")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--truncate", type=int, default=TRUNCATE)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    script = clean_script(read(args.script))
    kws, early = mine_keywords(script, top=args.top)
    primary = (args.primary or suggest_primary(kws)).strip().lower()
    secondary = [s.strip().lower() for s in args.secondary.split(",") if s.strip()]
    result = {"keywords": kws, "suggested_primary": suggest_primary(kws), "primary": primary}
    if args.caption:
        result["lint"] = lint(script, read(args.caption), primary, secondary, args.truncate)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    render_keywords(kws, early, result["suggested_primary"])
    if args.caption:
        render_lint(result["lint"])


if __name__ == "__main__":
    main()
