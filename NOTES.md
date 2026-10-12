# SparshaGuard: project notes

SparshaGuard is a touch-sensing women's safety smartwatch (team: Bhajanth V, Sukruth A Chinnur, RV University).
Once Guard Mode is on, another person's sustained touch (~2 s) starts a 15 s PIN countdown; no PIN or a wrong PIN
sends SMS + GPS, calls 112 and records audio; a duress PIN fakes a cancel and alerts silently; strap removal alerts at once.
This repo is a simulation study (no hardware yet). The next stage, "Gate 1", is a battery-powered prototype that calibrates the model.

## Layout

- `sg_model.py` is the lumped electrical model (Touché-style swept-frequency sensing, 200 points from 1 kHz to 3.48 MHz, floating watch ground).
  Every parameter is tagged with its source: [S#] = paper, [G] = geometry, [E] = estimate, [E, settled] = estimate shown not to change any result.
- Pipeline: `make_figures.py` (fig0–4) → `make_dataset.py` → `train_classifier.py` (fig5–7) → `event_stream.py` (fig8–9, about 30 min).
  `whole_body.py` (fig10–12) and `fem/` (boundary-element 3D field solver) cover the whole-body touch study.
- `explorer/` is the interactive page; `explorer/model.js` must stay a faithful port of `sg_model.py` (rebuild with `build_explorer.py`).
- `docs/parameter_sources.md` lists every value and its source; `docs/SparshaGuard_paper_values.xlsx` is the paper-values workbook
  (built by `tools/build_paper_values_xlsx.py` from the lists in `tools/build_sources_xlsx.py`).
- `video/` holds the narrated explainer (its source code lives outside this repo).
- The big dataset CSVs are git-ignored; `python rebuild_csv.py` recreates `data/sparshaguard_synthetic_v0_3.csv` from the `.npz`.

## How the team wants this work done

- Use values from published papers rather than assumptions. When values are missing, find papers and report the findings first;
  integrate new findings into the model only when asked to.
- Log every value found in a paper in `docs/SparshaGuard_paper_values.xlsx` with its full reference. Keep that workbook simple
  (one sheet per purpose) and never add frozen panes.
- The remaining [E] estimates are on hold for a later discussion. The ring-electrode idea was dropped.
- The 3D hand-near-strap result (`fem/`, 0.05–1.4 pF at 1–10 cm) is not yet integrated into `sg_model.py` (forearm case still uses 0.5–3 pF). Integrate only when asked.
- Ideas proposed but not yet modelled: a passive body-potential channel for touches anywhere on the body (`docs/whole_body_detection.md`),
  an ADS1115 external ADC, a titanium back plate.
- Keep explanations plain and practical; the team presents this at hackathons.
