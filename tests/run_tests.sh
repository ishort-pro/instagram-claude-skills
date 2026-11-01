#!/usr/bin/env bash
# Runs every tool in the pack against tests/fixtures and asserts the results.
# Usage: bash tests/run_tests.sh      (exit 0 = all pass)
set -u
cd "$(dirname "$0")/.."
F=tests/fixtures
PY=${PYTHON:-python3}
pass=0; fail=0
check() {  # name, command, python-assert-on-stdout
  local name="$1" cmd="$2" assert="$3" out
  out=$(eval "$cmd" 2>&1)
  if OUT="$out" $PY -c "import os,json,sys; o=os.environ['OUT']; $assert" 2>/dev/null; then
    echo "PASS  $name"; pass=$((pass+1))
  else
    echo "FAIL  $name"; echo "$out" | head -20 | sed 's/^/      /'; fail=$((fail+1))
  fi
}

SEO=skills/instagram-seo-caption-generator/scripts/seo_caption.py
check "seo keywords: mines 'posting schedule' from the script" \
  "$PY $SEO --script $F/transcript_posting_schedule.txt --json" \
  "d=json.loads(o); assert d['suggested_primary']=='posting schedule'"
check "seo lint: weak caption scores < 50 and FIX" \
  "$PY $SEO --script $F/transcript_posting_schedule.txt --caption $F/caption_before.txt --primary 'instagram posting schedule' --secondary 'posting schedule for beginners,content creation,instagram account' --json" \
  "d=json.loads(o)['lint']; assert d['score']<50 and d['verdict']=='FIX'; assert any(c['check']=='NO STUFFING' and c['status']=='WARN' for c in d['checks'])"
check "seo lint: rewritten caption scores >= 85, no FAIL" \
  "$PY $SEO --script $F/transcript_posting_schedule.txt --caption $F/caption_after.txt --primary 'instagram posting schedule' --secondary 'posting schedule for beginners,content creation,instagram account' --json" \
  "d=json.loads(o)['lint']; assert d['score']>=85, d['score']; assert not any(c['status']=='FAIL' for c in d['checks'])"
check "seo lint: >5 hashtags fails" \
  "$PY $SEO --script $F/reel_script_outliers.txt --caption $F/caption_ai_draft.txt --primary 'outlier reels' --json" \
  "d=json.loads(o)['lint']; assert any(c['check']=='HASHTAGS' and c['status']=='FAIL' for c in d['checks'])"

check "caption_lint: shows the feed window, flags 7 hashtags" \
  "$PY skills/instagram-seo-caption-generator/scripts/caption_lint.py $F/caption_ai_draft.txt" \
  "assert 'WHAT THE FEED SHOWS' in o and 'over Instagram' in o"

OUT=skills/instagram-reels-research/scripts/outliers.py
check "outliers: IShort CSV export, breakout found at 19x, account from URL" \
  "$PY $OUT $F/ishort_export_sample.csv --json" \
  "d=json.loads(o); r=d['reels'][0]; assert r['multiple']>15 and r['tier']=='BREAKOUT' and r['account']=='example_creator'; assert d['outliers']==2"
check "outliers: hook formula named from hooks.json" \
  "$PY $OUT $F/ishort_export_sample.csv --json" \
  "d=json.loads(o); assert d['reels'][0]['formula']!='unclassified'"

printf '{"rows":[{"account":"a","views":5000,"transcript":"Five UI mistakes that are killing your designs."},{"account":"b","views":0,"transcript":"x"},{"account":"c","views":90000,"transcript":"Three Reels numbers that matter more than views."}]}' > /tmp/ics_rows.json
printf 'c\t20000\n' > /tmp/ics_medians.tsv
check "outliers: mixed library says NO BASELINE and counts 0-view rows" \
  "$PY $OUT /tmp/ics_rows.json" \
  "assert 'NO BASELINE' in o and '1 reel(s) had 0 views' in o"
check "outliers: --medians gives per-account multiples; formulas #7/#11 match" \
  "$PY $OUT /tmp/ics_rows.json --medians /tmp/ics_medians.tsv --json" \
  "d=json.loads(o); r=[x for x in d['reels'] if x['account']=='c'][0]; assert r['multiple']==4.5; assert all(x['formula']!='unclassified' for x in d['reels'])"

HS=skills/instagram-reel-script-generator/scripts/hookscore.py
check "hookscore: dealbreaker hook never ranks first" \
  "$PY $HS $F/hooks_mixed.txt --json" \
  "d=json.loads(o); rows=d if isinstance(d,list) else d.get('hooks', d.get('ranked', [])); top=rows[0]; t=top.get('hook') or top.get('text'); assert 'Stop scrolling' not in t and 'Hey guys' not in t"
check "hookscore: 'Stop scrolling ... emoji' capped at <= 45" \
  "$PY $HS --hook 'Stop scrolling if you want to go viral on Instagram in 2026 🔥' --json" \
  "d=json.loads(o); d=d[0] if isinstance(d,list) else d; assert d.get('overall', d.get('score', 100))<=45"
check "beats: flags a slow hook" \
  "$PY skills/instagram-reel-script-generator/scripts/beats.py $F/reel_script_outliers.txt --target 30" \
  "assert 'past the 3s mark' in o"

HZ=skills/instagram-humanizer/scripts
check "humanize: strips slop and leaves no '.!' artefact" \
  "$PY $HZ/humanize.py $F/caption_ai_draft.txt" \
  "assert 'delve' not in o.lower() and '—' not in o and '.!' not in o and 'Follow for more' not in o"
check "detect: AI draft is FLAGGED" \
  "$PY $HZ/detect.py $F/caption_ai_draft.txt" \
  "assert 'FLAGGED' in o"

check "every SKILL.md has name + description frontmatter, name matches folder" \
  "for f in SKILL.md skills/*/SKILL.md; do echo \"FILE \$f\"; head -3 \$f; done" \
  "
import re
blocks=o.split('FILE ')[1:]
assert len(blocks)==10, len(blocks)
for b in blocks:
    path=b.split()[0]; assert '---' in b and 'name:' in b, path
    name=re.search(r'name:\s*(\S+)', b).group(1)
    folder=path.split('/')[-2] if '/' in path else 'instagram-claude-skills'
    assert name==folder, (name, folder)
"
check "plugin manifests are valid JSON" \
  "cat .claude-plugin/plugin.json .claude-plugin/marketplace.json .mcp.json .codex-plugin/plugin.json" \
  "import json; [json.load(open(p)) for p in ['.claude-plugin/plugin.json','.claude-plugin/marketplace.json','.mcp.json','.codex-plugin/plugin.json']]"

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
