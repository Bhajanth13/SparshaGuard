"""One source of truth for the headline numbers, and a check that no file quotes stale ones.

    python tools/check_consistency.py          # writes data/headline_numbers.json, then scans
    python tools/check_consistency.py --quiet  # only the scan result (exit 1 if anything is stale)

Every number the README, front page, decks and scripts quote should come from
data/headline_numbers.json, which this script builds from the result files:
  demo/demo_check.json             digital twin, rule F2, bodies at ~10 V (node demo/check_demo.js)
  data/passive_stream_results.json Python time-domain study, improved front end, 1-100 V
  data/event_stream_results.json   active sweep alone (first design)
  tools/build_sources_xlsx.py      the source list (count of S-numbers)
The scan then looks for claims that were true once and are not any more (added in the 6 Nov 2026
consistency pass, see docs/consistency_pass_2026-11-06.md). Files kept as history are skipped.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
pct = lambda x: round(100 * x)


def headline() -> dict:
    chk = json.loads((ROOT / "demo/demo_check.json").read_text())
    ps = json.loads((ROOT / "data/passive_stream_results.json").read_text())["improved"]
    es = json.loads((ROOT / "data/event_stream_results.json").read_text())
    hours = 3 * len(chk["daily_life"])
    held = chk["hold_without_pull_caught"]
    volts = [v for v in ps if 1.0 <= float(v) <= 100.0]
    ctx = list(ps[volts[0]]["coverage"])
    wrist = [sum(ps[v]["coverage"][c]["wrist"]["F2"] for c in ctx) / len(ctx) for v in volts]
    body = [ps[v]["body_avg"]["F2"] for v in volts]
    fp = [ps[v]["fp_avg_strangers_excl_friend"]["F2"] for v in volts]
    base = next(r for r in es if not r["classifier_gate"] and abs(r["T_enter_pct"] - 0.3) < 1e-9
                and abs(r["sustain_s"] - 2.0) < 1e-9)
    srcs = re.findall(r'"S(\d+)"', (ROOT / "tools/build_sources_xlsx.py").read_text())
    return {
        "note": "Built by tools/check_consistency.py; quote these, not older decks.",
        "sources_logged": max(map(int, srcs)),
        "demo_F2_10V": {
            "wrist_grabs_caught_pct": pct(chk["grabs_caught"]["wrist"]["fused2"]),
            "body_average_7_places_pct": pct(chk["body_average"]["fused2"]),
            "hold_without_pull_caught_pct": [pct(min(held[k]["fused2"] for k in held)), pct(max(held[k]["fused2"] for k in held))],
            "struggle_without_touch_caught_pct": pct(chk["struggle_without_touch_caught"]["fused2"]),
            "own_hand_prompted_pct": pct(chk["own_hand_prompted"]["fused2"]),
            "strap_removal_caught_pct": pct(chk["strap_removal_caught"]["fused2"]),
            "simulated_hours": hours,
            "unwanted_prompts_in_hours": round(chk["mean_unwanted_prompts_per_hour"]["fused2"] * hours),
            "unwanted_prompts_per_hour": round(chk["mean_unwanted_prompts_per_hour"]["fused2"], 2),
        },
        "demo_first_design": {
            "body_average_7_places_pct": pct(chk["body_average"]["active"]),
            "wrist_grabs_caught_pct": pct(chk["grabs_caught"]["wrist"]["active"]),
            "unwanted_prompts_in_hours": round(chk["mean_unwanted_prompts_per_hour"]["active"] * hours),
            "unwanted_prompts_per_hour": round(chk["mean_unwanted_prompts_per_hour"]["active"], 1),
        },
        "study_F2_1_to_100V": {
            "wrist_grabs_caught_pct": [pct(min(wrist)), pct(max(wrist))],
            "body_average_7_places_pct": [pct(min(body)), pct(max(body))],
            "unwanted_prompts_per_hour_strangers": [round(min(fp), 2), round(max(fp), 2)],
        },
        "study_sweep_only": {
            "wrist_grabs_caught_pct": pct(base["detection_rate"]["wrist"]),
            "prompts_per_hour": {k.split(" ")[0].lower(): v for k, v in base["prompts_per_hour"].items()},
        },
    }


# Claims that were true once (and the date they stopped being true). Each is (pattern, why).
STALE = [
    (r"99 ?%\W{0,3}(of )?(grabs|wrist|struggles)|99 ?%\s+\(goal", "99 % wrist/struggles is the 15 Oct twin; see demo_F2_10V"),
    (r"Catches 70 ?% of grabs|70 ?% of grabs caught|Grabs anywhere.{0,40}70 ?%", "70 % anywhere is rule F (14 Oct); F2 is current"),
    (r"0[–-]1 (unwanted|false)|at most one unwanted prompt", "0-1 prompts in 9 h is the 15 Oct twin"),
    (r"\b60 (published|sources|cited)|60 papers|\b15 published", "the source list has grown; use sources_logged"),
    (r"half the price of a cellular Apple Watch", "Rs 24,999 is ~60 % of Rs 41,999"),
    (r"good shield \(2 pF|2 pF left|C_GB 2 pF|cgb=2\.0", "the 2 pF shield residual has no source; best measured is 23 % [S14]"),
    (r"about 30 ?% with a bootstrapped|about 30 ?% with the bootstrapped|-> k ~ 30 %", "k is ~10 % with the sourced shield"),
    (r"~88[–-]93 ?%|~4[–-]5\.5 unwanted|about twenty-five for a sweep-only", "pre-3D event_stream numbers (12 Oct)"),
    (r"what would run on the ESP32", "the flagship runs Guard Mode on the nRF5340 safety core"),
    (r"Alerts over 4G LTE Cat-1", "a 112 voice call needs 4G VoLTE (flagship spec)"),
]
# History kept on purpose (each says so in its own README or header), and this file.
SKIP = ("archive/", "video/SparshaGuard_Explained", "video/narration_script.md", "video/demo_2min/",
        "docs/anvaya/SparshaGuard_ANVAYA_2k26.pptx", "docs/consistency_pass_", "tools/check_consistency.py",
        "tools/build_sources_xlsx.py", "docs/parameter_sources.md", "docs/findings_integrated_v0_3.md",
        "data/", ".git/")
TEXT = (".md", ".py", ".js", ".html", ".mmd", ".svg", ".txt")


def texts():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if not p.is_file() or rel.startswith(SKIP):
            continue
        if p.suffix in TEXT:
            yield rel, p.read_text(encoding="utf-8", errors="ignore")
        elif p.suffix == ".pptx":
            with zipfile.ZipFile(p) as z:
                xml = " ".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".xml"))
            yield rel, re.sub(r"<[^>]+>", "", xml)


def scan() -> list[str]:
    bad = []
    for rel, t in texts():
        for pat, why in STALE:
            for m in re.finditer(pat, t):
                line = t.count("\n", 0, m.start()) + 1
                bad.append(f"{rel}:{line}: '{m.group(0)}': {why}")
    return bad


if __name__ == "__main__":
    if "--quiet" not in sys.argv:
        h = headline()
        (ROOT / "data/headline_numbers.json").write_text(json.dumps(h, indent=1, ensure_ascii=False) + "\n")
        print(json.dumps(h, indent=1, ensure_ascii=False))
    problems = scan()
    print(f"\n{len(problems)} stale claim(s)" + (":" if problems else ""))
    for b in problems:
        print("  " + b)
    sys.exit(1 if problems else 0)
