#!/usr/bin/env python3
"""
outliers.py - find the Instagram Reels that beat their own account, name the
hook formula each one used, and write a swipe file you can script from.

Raw views are not evidence. A 2M-follower account doing 400K views had a quiet
day; a 4K-follower account doing 400K found something you can copy. This
ranks every reel on its OUTLIER MULTIPLE = views / that account's median views.

  >= 5x  breakout     copy the structure today
  >= 3x  outlier      worth a transcript
  >= 1.5x above par   a pattern, not proof
  <  1.5x normal day  teaches nothing, however big the number

Input (auto-detected, mix freely):
  * IShort CSV/Excel-CSV export from the Chrome extension
    (URL, Caption, Type, Views, Likes, Comments, ..., Transcript)
  * IShort MCP JSON: list_my_scripts / search_my_scripts output ({"rows": [...]})
  * IShort MCP JSON: get_competitor_report output (uses its medianViews)
  * a hand-made TSV: account  followers  median  views  hook

The median is computed per account from the file itself when an account has
at least 5 reels in it (an IShort export of one profile always does). With
fewer, pass --median or include a `median` column, or the multiple is marked "?".

Usage
  python3 outliers.py export.csv
  python3 outliers.py scripts.json --min 3 --out swipe.md
  python3 outliers.py a.csv b.csv report.json --json

Python 3.8+, standard library only. Hook formulas come from
../../instagram-reel-script-generator/references/hooks.json when present.
"""

import argparse
import csv
import io
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS_CANDIDATES = [
    os.path.join(HERE, "..", "..", "instagram-reel-script-generator", "references", "hooks.json"),
    os.path.join(HERE, "..", "references", "hooks.json"),
]
WORD_RE = re.compile(r"[\w$%'’-]+", re.UNICODE)
SHORTCODE_RE = re.compile(r"instagram\.com/(?:[\w.]+/)?(?:reel|reels|p)/([\w-]+)")

try:
    sys.path.insert(0, os.path.join(HERE, "..", "..", "instagram-reel-script-generator", "scripts"))
    from hookscore import run as score_hook  # noqa: E402
except Exception:
    score_hook = None


def load_formulas(path=None):
    for p in ([path] if path else []) + HOOKS_CANDIDATES:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        by_id = {h["id"]: h for h in d["hooks"]}
        order = d.get("classify_order") or sorted(by_id)
        return [(by_id[i]["id"], by_id[i]["name"], re.compile(by_id[i]["match"], re.I))
                for i in order if i in by_id and by_id[i].get("match")]
    return None


def classify(hook, formulas):
    for fid, name, pattern in formulas or []:
        if pattern.search(hook or ""):
            return fid, name
    return None, "unclassified"


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([kmb]?)$", s)
    if not m:
        d = re.sub(r"[^\d]", "", s)
        return int(d) if d else None
    mult = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[m.group(2)]
    return int(float(m.group(1)) * mult)


def first_line(text, max_words=22):
    """The hook: first spoken sentence of a transcript, or first caption line."""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text.strip())
    m = re.match(r"(.+?[.!?।])(\s|$)", t)
    s = m.group(1) if m else t
    w = s.split()
    return " ".join(w[:max_words]) + (" ..." if len(w) > max_words else "")


def account_from_url(url):
    m = re.search(r"instagram\.com/([\w.]+)/(?:reel|reels|p)/", url or "")
    return m.group(1) if m else ""


def norm_row(account, views, transcript="", caption="", url="", median=None, followers=None, extra=None):
    hook = first_line(transcript) or first_line((caption or "").split("\n")[0])
    r = {"account": (account or account_from_url(url) or "?").lstrip("@"),
         "views": num(views) or 0, "hook": hook, "url": url or "",
         "hook_source": "transcript" if transcript else ("caption" if caption else "none"),
         "median": num(median), "followers": num(followers)}
    if extra:
        r.update(extra)
    return r


def read_csv(raw, default_account=""):
    rows = []
    rd = csv.DictReader(io.StringIO(raw))
    for d in rd:
        k = {re.sub(r"\s+", " ", (key or "").strip().lower()): v for key, v in d.items()}
        views = k.get("views") or k.get("plays") or k.get("view count")
        if views is None:
            continue
        url = k.get("url") or k.get("reel url") or ""
        rows.append(norm_row(k.get("account") or k.get("username") or account_from_url(url) or default_account,
                             views, k.get("transcript", ""), k.get("caption", ""),
                             k.get("url") or k.get("reel url") or "",
                             k.get("median"), k.get("followers"),
                             {"likes": num(k.get("likes")), "comments": num(k.get("comments")),
                              "shares": num(k.get("shares")), "saves": num(k.get("saves")),
                              "duration": k.get("duration"), "date": k.get("date")}))
    return rows


def read_tsv(raw):
    lines = [l for l in raw.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    head = [c.strip().lower() for c in lines[0].split("\t")]
    cols, body = (head, lines[1:]) if "views" in head else (["account", "followers", "views", "hook"], lines)
    rows = []
    for line in body:
        cells = line.split("\t") + [""] * len(cols)
        r = dict(zip(cols, [c.strip() for c in cells]))
        rr = norm_row(r.get("account"), r.get("views"), "", "", r.get("url", ""), r.get("median"), r.get("followers"))
        rr["hook"], rr["hook_source"] = r.get("hook", ""), "manual"
        rows.append(rr)
    return rows


def read_json(d):
    rows = []
    if isinstance(d, dict) and "rows" in d:                       # list/search_my_scripts
        for x in d["rows"]:
            rows.append(norm_row(x.get("account"), x.get("views"), x.get("transcript", ""),
                                 x.get("caption", ""), x.get("reelUrl", ""),
                                 extra={"likes": x.get("likes"), "comments": x.get("comments"),
                                        "engagement": x.get("engagementRate"), "duration": x.get("duration")}))
    elif isinstance(d, dict) and ("insights" in d or "stats" in d):  # get_competitor_report
        acct = d.get("handle") or d.get("competitorHandle") or d.get("username") or ""
        med = (d.get("stats") or {}).get("medianViews")
        ins = d.get("insights") or {}
        for x in (ins.get("bestReels") or []) + (ins.get("worstReels") or []):
            rows.append(norm_row(acct, x.get("views"), "", x.get("caption", ""), x.get("reelUrl", ""), med,
                                 extra={"likes": x.get("likes"), "comments": x.get("comments")}))
        for x in d.get("reels") or []:
            rows.append(norm_row(acct, x.get("views"), x.get("transcript", ""), x.get("caption", ""),
                                 x.get("reelUrl", ""), med))
    elif isinstance(d, list):
        for x in d:
            rows.append(norm_row(x.get("account"), x.get("views"), x.get("transcript", ""),
                                 x.get("caption", ""), x.get("reelUrl") or x.get("url", ""), x.get("median")))
    return rows


def read_any(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8-sig").read()
    s = raw.lstrip()
    if s.startswith("{") or s.startswith("["):
        return read_json(json.loads(s))
    first = s.splitlines()[0] if s else ""
    if "\t" in first and "," not in first:
        return read_tsv(s)
    # IShort exports are one profile per file, named reels_<account>_<timestamp>.csv
    base = os.path.basename(path)
    m = re.match(r"reels_(.+?)_\d{10,}\.csv$", base)
    default = m.group(1) if m else (re.sub(r"\.csv$", "", base) if path != "-" else "")
    return read_csv(s, default_account=default)


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        m = SHORTCODE_RE.search(r.get("url") or "")
        key = m.group(1) if m else (r["account"], r["views"], r["hook"][:40])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def tier(m):
    if m is None:
        return "?"
    return "BREAKOUT" if m >= 5 else "OUTLIER" if m >= 3 else "above par" if m >= 1.5 else "normal"


def analyse(rows, formulas, forced_median=None):
    by_acct = {}
    for r in rows:
        if r["views"] > 0:
            by_acct.setdefault(r["account"], []).append(r["views"])
    for r in rows:
        own = by_acct.get(r["account"], [])
        if forced_median:
            base, src = forced_median, "given"
        elif r.get("median"):
            base, src = r["median"], "report/column"
        elif len(own) >= 5:
            base, src = statistics.median(own), f"median of {len(own)} reels in file"
        elif r.get("followers"):
            base, src = r["followers"], "followers (weak baseline)"
        else:
            base, src = None, "unknown - need 5+ reels per account or --median"
        r["baseline"], r["baseline_source"] = base, src
        r["multiple"] = round(r["views"] / base, 2) if base else None
        r["tier"] = tier(r["multiple"])
        r["formula_id"], r["formula"] = classify(r["hook"], formulas)
        if score_hook and r["hook"]:
            _, overall, verdict, _ = score_hook(r["hook"])
            r["hook_score"], r["hook_verdict"] = round(overall, 1), verdict
        else:
            r["hook_score"], r["hook_verdict"] = None, None
    ranked = sorted(rows, key=lambda r: (-(r["multiple"] or 0), -r["views"]))
    counts = {}
    for r in ranked:
        if (r["multiple"] or 0) >= 3:
            counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    return {"n": len(ranked), "accounts": len(by_acct), "reels": ranked,
            "outliers": sum(1 for r in ranked if (r["multiple"] or 0) >= 3),
            "breakouts": sum(1 for r in ranked if (r["multiple"] or 0) >= 5),
            "formulas_in_outliers": sorted(counts.items(), key=lambda kv: -kv[1]),
            "no_transcript": sum(1 for r in ranked if (r["multiple"] or 0) >= 3 and r["hook_source"] != "transcript")}


def render(a, top, out=sys.stdout):
    head = f"OUTLIER REELS  ·  {a['n']} reels  ·  {a['accounts']} account(s)  ·  {a['outliers']} at 3x+, {a['breakouts']} at 5x+"
    print("\n" + head, file=out)
    print("=" * max(len(head), 78), file=out)
    for r in a["reels"][:top]:
        mult = f"{r['multiple']:.1f}x" if r["multiple"] else "  ?"
        sc = f"{r['hook_score']:.0f}" if r["hook_score"] is not None else " -"
        print(f"  {mult:>7}  {r['tier']:<9} @{r['account'][:18]:<18} {r['views']:>11,}  hook {sc:>3}  {r['formula'][:20]}", file=out)
        if r["hook"]:
            print(f"           \"{r['hook'][:92]}\"  [{r['hook_source']}]", file=out)
        if r["url"]:
            print(f"           {r['url']}", file=out)
    print("-" * max(len(head), 78), file=out)
    if a["formulas_in_outliers"]:
        print("  formulas in 3x+ reels: " + ", ".join(f"{n} x{c}" for n, c in a["formulas_in_outliers"][:5]), file=out)
    if a["no_transcript"]:
        print(f"  {a['no_transcript']} outlier(s) have no transcript, so the hook above is the CAPTION, not what was said.\n"
              "  Transcribe them (IShort MCP: transcribe_reel) before you copy anything.", file=out)
    srcs = sorted({r["baseline_source"] for r in a["reels"]})
    print("  baseline: " + "; ".join(srcs), file=out)
    print("", file=out)


def to_markdown(a, top):
    lines = ["# Swipe file", "", f"{a['n']} reels, {a['accounts']} account(s). Ranked by views / account median.", ""]
    for r in a["reels"][:top]:
        mult = f"{r['multiple']:.1f}x" if r["multiple"] else "?"
        lines += [f"## {mult} {r['tier']} · @{r['account']} · {r['formula']}",
                  f"- views: {r['views']:,} · baseline: {r['baseline'] and int(r['baseline']):,} ({r['baseline_source']})"
                  if r["baseline"] else f"- views: {r['views']:,} · baseline: unknown",
                  f"- hook ({r['hook_source']}): \"{r['hook']}\"",
                  f"- reel: {r['url']}" if r["url"] else "", ""]
    return "\n".join(l for l in lines if l is not None) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Rank Instagram Reels by outlier multiple (views / account median).")
    ap.add_argument("inputs", nargs="+", help="IShort CSV export, IShort MCP JSON, TSV, or - for stdin")
    ap.add_argument("--median", type=float, help="force one baseline (account median views)")
    ap.add_argument("--min", type=float, default=0, help="only show reels at or above this multiple")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--hooks", help="path to hooks.json")
    ap.add_argument("--out", help="write the swipe file as markdown")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = []
    for p in args.inputs:
        rows += read_any(p)
    rows = dedupe([r for r in rows if r["views"]])
    if not rows:
        sys.exit("no usable rows: need at least a views column (IShort export, MCP JSON or TSV)")
    a = analyse(rows, load_formulas(args.hooks), args.median)
    if args.min:
        a["reels"] = [r for r in a["reels"] if (r["multiple"] or 0) >= args.min]
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a, args.top)
    if args.out:
        path = os.path.expanduser(args.out)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, "w", encoding="utf-8").write(to_markdown(a, args.top))
        print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
