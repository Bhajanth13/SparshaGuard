# demo/ (the digital twin web page)

Live at https://bhajanth13.github.io/SparshaGuard/demo/. Open `sparshaguard_demo.html` to use it
offline. That file is generated: edit the sources, then run `python tools/build_demo.py`.

| File | What it is |
|---|---|
| `page_src.html` | Page layout, watch screens, guided story |
| `sensor.js` | Simulated sensor: the physics model plus drift and noise |
| `firmware.js` | Guard Mode logic of the safety core: detection rules and the PIN state machine |
| `check_demo.js` → `demo_check.json` | Headless check of the twin against the study (`node demo/check_demo.js`, ~4 min) |
| `test_firmware.js` | Tests of the Guard Mode rules (`node demo/test_firmware.js`, ~1 s) |
| `index.html` | Redirect so the short `/demo/` link works |
