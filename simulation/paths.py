"""Where the simulation reads and writes, so every script works from any folder.

    from paths import DATA, FIGURES, CLASSIFIER, FEM

DATA        results/data        numbers and datasets (JSON, NPZ, CSV)
FIGURES     results/figures     every figure in the study (fig0-fig19)
CLASSIFIER  results/classifier  the trained SVM (svm_dual_shield.joblib)
FEM         simulation/fem      3D field-solver code and its own results
"""
from pathlib import Path

SIM = Path(__file__).resolve().parent
ROOT = SIM.parent
RESULTS = ROOT / "results"
DATA = RESULTS / "data"
FIGURES = RESULTS / "figures"
CLASSIFIER = RESULTS / "classifier"
FEM = SIM / "fem"

for _d in (DATA, FIGURES, CLASSIFIER):
    _d.mkdir(parents=True, exist_ok=True)
