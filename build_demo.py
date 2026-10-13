"""Build the digital-twin demo page from its sources.

demo/page_src.html  (layout, styles, UI script, with /*MODEL*/ /*SENSOR*/ /*FIRMWARE*/ placeholders)
explorer/model.js   (JavaScript port of sg_model.py, shared with the explorer)
demo/sensor.js      (sensor twin: drift, noise, per-event random draws)
demo/firmware.js    (watch logic: detection pipeline of event_stream.py + PIN state machine)
  -> demo/sparshaguard_demo.html  (one self-contained page; open it in a browser)

Run:  python build_demo.py        Check the logic headless with:  node demo/check_demo.js
"""
from pathlib import Path

root = Path(__file__).parent
strip = lambda p: (root / p).read_text(encoding="utf-8").replace(
    'if (typeof module !== "undefined") module.exports = SG;', "")
page = (root / "demo/page_src.html").read_text(encoding="utf-8")
page = (page.replace("/*MODEL*/", strip("explorer/model.js"))
            .replace("/*SENSOR*/", strip("demo/sensor.js"))
            .replace("/*FIRMWARE*/", strip("demo/firmware.js")))
out = '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n' + page + "\n</html>\n"
(root / "demo/sparshaguard_demo.html").write_text(out, encoding="utf-8")
print("wrote demo/sparshaguard_demo.html")
