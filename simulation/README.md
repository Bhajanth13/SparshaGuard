# simulation/

All the Python. Install once with `pip install -r requirements.txt` (from the repo root), then run
any script from anywhere; everything it produces goes to `results/` (see `paths.py`).

| Kind | Files |
|---|---|
| The model | `sg_model.py` (electrical model, every parameter sourced), `sg_passive.py` (static channel + motion), `sg_newch.py` (own-hand check, transmit check, skin response) |
| Studies | `make_figures.py` → `make_dataset.py` → `train_classifier.py` → `event_stream.py`, then `whole_body.py`, `second_ground.py`, `fusion_study.py`, `passive_stream.py` |
| Helpers | `sg_features.py`, `plotstyle.py`, `paths.py`, `rebuild_csv.py` |
| Independent checks | `fem/` (3D field solver, and FastCap), `ltspice/` (SPICE netlists, and ngspice) |

Run times and the full order are in the main `README.md` under "How to run". After any re-run,
finish with `python tools/check_consistency.py` so every document quotes the new numbers.
