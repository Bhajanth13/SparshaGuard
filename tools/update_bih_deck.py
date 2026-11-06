"""Bring docs/SparshaGuard_BIH2026.pptx up to date with data/headline_numbers.json.

    python tools/check_consistency.py    # first: refresh data/headline_numbers.json
    python tools/update_bih_deck.py

Edits text runs in place (formatting kept) and resizes the success-metric bars on slide 7.
Safe to re-run: every replacement is keyed on the deck's current wording or on the shape.
"""
import json
import re
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "docs/SparshaGuard_BIH2026.pptx"
H = json.loads((ROOT / "data/headline_numbers.json").read_text())
D = H["demo_F2_10V"]
N = H["sources_logged"]
BAR_FULL = 3200400                       # EMU width of the 100 % bar track on slide 7

# whole-run text replacements (regex on each run)
RUNS = [
    (r"Physics from \d+ sources", f"Physics from {N} sources"),
    (r"\(\d+ logged\)", f"({N} logged)"),
    (r"^\d+ published sources$", f"{N} published sources"),
    (r"^Catches \d+ % of grabs$", f"Catches {D['body_average_7_places_pct']} % of grabs"),
    (r"^Catches \d+ % of struggles$", f"Catches {D['struggle_without_touch_caught_pct']} % of struggles"),
    (r"^(?:0[–-]1|\d+) false prompts in \d+ hours$", f"{D['unwanted_prompts_in_hours']} false prompts in {D['simulated_hours']} hours"),
    (r"^\d+ % of grabs caught$", f"{D['body_average_7_places_pct']} % of grabs caught"),
    (r"^(?:0[–-]1|\d+) false alarms in \d+ h$", f"{D['unwanted_prompts_in_hours']} false alarms in {D['simulated_hours']} h"),
    (r"^\d+ cited sources$", f"{N} cited sources"),
    (r"^Alerts over 4G LTE Cat-1 \(2G is being shut down\)$", "Alerts over 4G VoLTE, own SIM (2G is being shut down)"),
    (r"^(?:0[–-]1|\d+) in \d+ h$", f"{D['unwanted_prompts_in_hours']} in {D['simulated_hours']} h"),
]
# slide 7 bars: (label of the value text box, shape id of the filled bar, value as a fraction)
BARS = [("(goal 90 %)", 39, D["wrist_grabs_caught_pct"] / 100),
        ("(goal 60 %)", 44, D["body_average_7_places_pct"] / 100)]


def main():
    prs = Presentation(DECK)
    changed = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    for pat, new in RUNS:
                        if re.search(pat, run.text):
                            out = re.sub(pat, new, run.text)
                            if out != run.text:
                                run.text = out
                                changed += 1
    s7 = prs.slides[6]
    byid = {sh.shape_id: sh for sh in s7.shapes}
    for goal, sid, frac in BARS:                # value run ("99 %") sits before the goal run
        for sh in s7.shapes:
            if sh.has_text_frame and goal in sh.text_frame.text:
                sh.text_frame.paragraphs[0].runs[0].text = f"{round(100 * frac)} %"
        byid[sid].width = int(BAR_FULL * min(1.0, frac))
    prs.save(DECK)
    print(f"{changed} text runs updated; bars set to {[round(f, 2) for _, _, f in BARS]}")


if __name__ == "__main__":
    main()
