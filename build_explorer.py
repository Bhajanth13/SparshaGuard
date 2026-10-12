"""Rebuild the interactive explorer page from its two sources.

explorer/page_src.html  (layout, styles, UI script, with a /*MODEL*/ placeholder)
explorer/model.js       (JavaScript port of sg_model.py)
  -> explorer/sparshaguard_explorer.html  (one self-contained page; open it in a browser)

Run:  python build_explorer.py
"""
from pathlib import Path

here = Path(__file__).parent / "explorer"
src = (here / "page_src.html").read_text(encoding="utf-8")
model = (here / "model.js").read_text(encoding="utf-8").replace(
    'if (typeof module !== "undefined") module.exports = SG;', "")
(here / "sparshaguard_explorer.html").write_text(src.replace("/*MODEL*/", model), encoding="utf-8")
print("wrote explorer/sparshaguard_explorer.html")
