"""Rebuild the interactive explorer page from its two sources.

explorer/page_src.html  (layout, styles, UI script, with a /*MODEL*/ placeholder)
explorer/model.js       (JavaScript port of sg_model.py)
data/passive_stream_results.json  (fused-watch results shown in the Whole-body tab)
demo/demo_check.json              (signs-of-assault results from the digital twin's headless check)
  -> explorer/sparshaguard_explorer.html  (one self-contained page; open it in a browser)

Run:  python build_explorer.py
"""
import json
from pathlib import Path

here = Path(__file__).parent / "explorer"
src = (here / "page_src.html").read_text(encoding="utf-8")
model = (here / "model.js").read_text(encoding="utf-8").replace(
    'if (typeof module !== "undefined") module.exports = SG;', "")
# fused-watch results from passive_stream.py (bootstrapped input + ADS1115)
res = json.loads((here.parent / "data/passive_stream_results.json").read_text())["improved"]
fz = {}
for v0 in ("1.0", "10.0", "100.0"):
    r = res[v0]
    locs = r["coverage"]["walking"].keys()
    fz[v0] = {"loc": {l: {k: round(sum(r["coverage"][c][l][k] for c in r["coverage"]) / 3, 3) for k in ("A", "F")} for l in locs},
              "body": {k: round(r["body_avg"][k], 3) for k in ("A", "F")},
              "fp": {k: round(r["fp_avg_strangers_excl_friend"][k], 3) for k in ("A", "F")}}
src = src.replace("/*FUSED*/", json.dumps(fz))
# signs of assault from her movement: digital-twin headless check (demo/check_demo.js)
chk = json.loads((here.parent / "demo/demo_check.json").read_text())
sig = {"struggle": chk["struggle_without_touch_caught"]["fused"], "runAlone": chk["running_alone_prompted"]["fused"],
       "touchRun": chk["touch_while_running_caught"]["fused"]}
src = src.replace("/*SIGNS*/", json.dumps(sig))
(here / "sparshaguard_explorer.html").write_text(src.replace("/*MODEL*/", model), encoding="utf-8")
print("wrote explorer/sparshaguard_explorer.html")
