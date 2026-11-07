# tools/

Run from anywhere.

| Script | What it does |
|---|---|
| `build_demo.py` | Rebuilds `demo/sparshaguard_demo.html` from its sources and `demo/demo_check.json` |
| `build_explorer.py` | Rebuilds `explorer/sparshaguard_explorer.html` from its sources and `results/data/` |
| `check_consistency.py` | Writes `results/data/headline_numbers.json` and fails if any file quotes a stale number. Run it last, after any re-run |
| `update_bih_deck.py` | Writes the headline numbers into `docs/pitch/bih2026/SparshaGuard_BIH2026.pptx` |
| `build_sources_xlsx.py`, `build_paper_values_xlsx.py` | Build the source workbooks in `docs/sources/` |
