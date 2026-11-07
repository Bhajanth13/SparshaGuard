# SparshaGuard: project notes

SparshaGuard is a touch-sensing women's safety smartwatch (team: Bhajanth V, Sukruth A Chinnur, RV University).
Once Guard Mode is on, another person's sustained touch (~2 s) starts a 15 s PIN countdown; no PIN or a wrong PIN
sends SMS + GPS, calls 112 and records audio; a duress PIN fakes a cancel and alerts silently; strap removal alerts at once.
This repo is a simulation study (no hardware yet). The next stage, "Gate 1", is a battery-powered prototype that calibrates the model.

## Layout

Folders (since 7 Nov 2026): `simulation/` all Python, writing to `results/` (`data/`, `figures/`, `classifier/`) via
`simulation/paths.py`, so scripts run from any folder; `demo/` and `explorer/` the two web pages (their URLs must not move;
`index.html` and `.nojekyll` stay at the root for GitHub Pages); `docs/technical/`, `docs/sources/`, `docs/pitch/<event>/`;
`media/` videos and screenshots; `tools/` build and check scripts; `archive/` old versions. Each folder has a README.

- `simulation/sg_model.py` is the lumped electrical model (Touché-style swept-frequency sensing, 200 points from 1 kHz to 3.48 MHz, floating watch ground).
  Every parameter is tagged with its source: [S#] = paper, [G] = geometry, [E] = estimate, [E, settled] = estimate shown not to change any result.
- Pipeline: `simulation/make_figures.py` (fig0–4) → `simulation/make_dataset.py` → `simulation/train_classifier.py` (fig5–7) → `simulation/event_stream.py` (fig8–9, about 3 min).
  `simulation/whole_body.py` (fig10–12) and `simulation/fem/` (boundary-element 3D field solver) cover the whole-body touch study.
- `explorer/` is the interactive page; `explorer/model.js` must stay a faithful port of `simulation/sg_model.py` (rebuild with `tools/build_explorer.py`).
- `simulation/sg_passive.py` (passive static channel in time + firmware contact-step detector) and `simulation/passive_stream.py` (fused rule F:
  sweep + static + accelerometer, fig17–18); summary in `docs/technical/whole_body_fusion.md`.
- `simulation/sg_newch.py` (28 Oct 2026): her own hand on the glass (k change), skin-stretch noise, the 100 kHz transmit check (shunt mode
  rejected, fig19) and skin response (EDA). Rule F2 = F + own-hand veto + an EDA path for grabs that only hold; summary in
  `docs/technical/new_channels.md`. The demo and explorer use rule F2.
- `demo/` is the digital-twin demo for the hackathon: `sensor.js` (model + drift + noise), `firmware.js` (`simulation/event_stream.py` pipeline + PIN
  state machine; it is the logic of the flagship's nRF5340 safety core), built by `tools/build_demo.py`; `node demo/check_demo.js` checks it
  headless against the study's rates and `node demo/test_firmware.js` tests the Guard Mode rules.
- Architecture: the ANVAYA 2k26 flagship design (nRF5340 safety core + STM32U5 app processor, 4G VoLTE + GNSS) is the reference;
  the ESP32 remains only the Gate 1 bench controller and the "current front end" baseline. See `docs/technical/design_notes.md`.
- Numbers: `python tools/check_consistency.py` builds `results/data/headline_numbers.json` from the results and fails if any file quotes a
  stale number; `python tools/update_bih_deck.py` writes them into the BIH deck. Run both after any re-run. History of the
  6 Nov 2026 pass: `docs/technical/consistency_pass_2026-11-06.md`.
- `docs/sources/parameter_sources.md` lists every value and its source; `docs/sources/SparshaGuard_paper_values.xlsx` is the paper-values workbook
  (built by `tools/build_paper_values_xlsx.py` from the lists in `tools/build_sources_xlsx.py`).
- `media/videos/` holds the narrated explainer (its source code lives outside this repo) and the 2-minute video.
- The big dataset CSVs are git-ignored; `python simulation/rebuild_csv.py` recreates `results/data/sparshaguard_synthetic_v0_3.csv` from the `.npz`.

## How the team wants this work done

- Use values from published papers rather than assumptions. When values are missing, find papers and report the findings first;
  integrate new findings into the model only when asked to.
- Log every value found in a paper in `docs/sources/SparshaGuard_paper_values.xlsx` with its full reference. Keep that workbook simple
  (one sheet per purpose) and never add frozen panes.
- The remaining [E] estimates are on hold for a later discussion. The ring-electrode idea was dropped.
- The 3D hand-near-strap result (`simulation/fem/`, 0.05–1.4 pF at 1–10 cm, checked with FastCap) was integrated into `simulation/sg_model.py` on 12 Oct 2026
  at the team's request: forearm grabs now sit at the noise floor, so only wrist grabs are visible to the active sweep.
- Independent checks: `simulation/ltspice/spice_crosscheck.py` (circuit vs ngspice) and `simulation/fem/fastcap_crosscheck.py` (3D field vs FastCap).
- The passive body-potential channel is now modelled (14 Oct 2026, fusion-study branch); it needs the bootstrapped input + ADS1115.
  Since 6 Nov 2026 the improved input uses TI's best measured shield (23 % of 35.4 pF = 8.1 pF) instead of an unsourced 2 pF.
  Still not modelled: a titanium back plate, audio, heart rate. EDA and the transmit check were added on 28 Oct 2026.
- Keep explanations plain and practical; the team presents this at hackathons.
