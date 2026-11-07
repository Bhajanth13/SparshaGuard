# results/

Everything the simulation produces. Do not edit by hand: re-run the script named below.

| Folder | What | Made by |
|---|---|---|
| `data/headline_numbers.json` | The numbers every README, deck and script should quote | `tools/check_consistency.py` |
| `data/*.json`, `data/*.txt` | The results behind each figure | the matching script in `simulation/` |
| `data/*.npz`, `data/sweep_frequencies.csv` | The synthetic dataset (18,000 events, 200 sweep points) | `simulation/make_dataset.py` |
| `figures/fig0`–`fig19` | Every figure in the study | `simulation/` scripts (fig13: `ltspice/`, fig14: `fem/`) |
| `classifier/svm_dual_shield.joblib` | Trained SVM (needs scikit-learn 1.9.1) | `simulation/train_classifier.py` |

The digital twin's own results are kept with it in `demo/demo_check.json`.
