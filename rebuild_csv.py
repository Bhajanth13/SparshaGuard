"""Write data/sparshaguard_synthetic_v0_3.csv from the .npz copy of the dataset.

The CSV (amplitude-change columns only) is byte-for-byte what make_dataset.py writes. Use this when you
have the .npz but not the CSV. Needs only numpy and pandas.

Run:  python rebuild_csv.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

data = Path(__file__).parent / "data"
D = np.load(data / "sparshaguard_synthetic_v0_3.npz", allow_pickle=True)
meta_cols = ["design", "environment", "label", "subtype", "near_watch", "score_pct"]
meta = pd.DataFrame({c: D[c] for c in meta_cols})
F = len(D["freqs_hz"])
df = pd.concat([meta, pd.DataFrame(D["X"], columns=[str(c) for c in D["cols"]])], axis=1)
df.to_csv(data / "sparshaguard_synthetic_v0_3.csv", index=False, float_format="%.5g")
print("wrote", data / "sparshaguard_synthetic_v0_3.csv", df.shape)
