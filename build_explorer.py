"""Rebuild the interactive explorer page from its two sources.

explorer/page_src.html  (layout, styles, UI script, with a /*MODEL*/ placeholder)
explorer/model.js       (JavaScript port of sg_model.py)
data/passive_stream_results.json  (fused-watch results shown in the Whole-body tab)
demo/demo_check.json              (signs-of-assault results from the digital twin's headless check)
tools/build_sources_xlsx.py       (the numbered References list; cite a source in page_src.html as {S4})
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
# references, IEEE style: [n] is source Sn in tools/build_sources_xlsx.py (and in the workbook)
import html
import importlib.util
import re
spec = importlib.util.spec_from_file_location("srcs", here.parent / "tools/build_sources_xlsx.py")
srcs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srcs)


def ieee_authors(a):
    a = a.strip()
    if a.startswith("(") and a.endswith(")"):
        inner = a[1:-1]
        # an unknown author is left out, as IEEE style does; an institution is kept
        return "" if any(w in inner for w in ("authors", "survey")) else inner
    if any(ch.isdigit() for ch in a):                # e.g. a patent number, not a list of names
        return a
    parts = [x.strip() for x in a.split(",") if x.strip()]
    if len(parts) <= 1 or any("et al" in x for x in parts):
        return ", ".join(parts)
    return ", ".join(parts[:-1]) + (", and " if len(parts) > 2 else " and ") + parts[-1]


def ieee(sid, auth, title, venue, year, url):
    e = html.escape
    link = (f'doi: <a href="{e(url)}" target="_blank" rel="noopener">{e(url.split("doi.org/")[1])}</a>' if "doi.org/" in url
            else f'[Online]. Available: <a href="{e(url)}" target="_blank" rel="noopener">{e(url)}</a>')
    who = ieee_authors(auth)
    return (f'<li id="ref-{sid}"><span class="n">[{sid[1:]}]</span><span>{e(who) + ", " if who else ""}'
            f'&ldquo;{e(title)},&rdquo; <i>{e(venue)}</i>, {year or "n.d"}. {link}</span></li>')


reflist = "\n      ".join(ieee(s[0], s[1], s[2], s[3], s[4], s[7]) for s in srcs.SOURCES)
src = src.replace("/*REFLIST*/", "\n      " + reflist + "\n    ")


def cite(m):
    out = []
    for part in m.group(1).split(","):
        nums = [int(x) for x in re.findall(r"S(\d+)", part)]
        if len(nums) == 2:                       # a range: S40–S46
            out.append(f'<a class="cite" href="#ref-S{nums[0]}">{nums[0]}</a>–<a class="cite" href="#ref-S{nums[1]}">{nums[1]}</a>')
        else:
            out.append(f'<a class="cite" href="#ref-S{nums[0]}">{nums[0]}</a>')
    return "[" + ", ".join(out) + "]"


src = re.sub(r"\{(S\d+(?:\s*[,–]\s*S\d+)*)\}", cite, src)
ids = {s[0] for s in srcs.SOURCES}
missing = sorted(set(re.findall(r'href="#ref-(S\d+)"', src)) - ids)
assert not missing, f"cited but not in the source list: {missing}"
(here / "sparshaguard_explorer.html").write_text(src.replace("/*MODEL*/", model), encoding="utf-8")
print("wrote explorer/sparshaguard_explorer.html")
