"""Monte Carlo synthetic dataset of labelled sweep profiles.

Each row = one simulated event for one random wearer in one environment:
  baseline sweep (stored before the event) and event sweep, both with measurement
  noise, on the Touché grid: 200 frequencies, 1 kHz to 3.48 MHz in 17.5 kHz steps.

CSV (amplitude only, what a Touché-style envelope detector measures):
    da_XXX  amplitude change  |V_evt| - |V_base|, as a fraction of full scale (drive amplitude)
NPZ: sparshaguard_synthetic_v0_3.npz       X = da (same as CSV) and metadata
     sparshaguard_synthetic_v0_3_phase.npz    dp = phase change in radians (needs a lock-in detector)
     sparshaguard_synthetic_v0_3_baseline.npz base = baseline amplitude |V_base|   (same row order)

Run:  python make_dataset.py [rows_per_design]
Writes data/sparshaguard_synthetic_v0_3.csv, .npz, _phase.npz and _baseline.npz.
"""
import sys

import numpy as np
import pandas as pd

import sg_model as m

SEED = 7
NOISE = 1e-3                     # matches make_figures.py
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 6000

# (class, subtype, share of rows, strong drift?)
MIX = [("no_contact", "drift", 0.14, False),
       ("no_contact", "arm_motion", 0.105, True),
       ("no_contact", "bystander", 0.105, False)] + \
      [("object", o, 0.20 / len(m.OBJECTS), False) for o in m.OBJECTS] + \
      [("self", "hand_on_watch", 0.15, False)] + \
      [("other_person", l, 0.30 / len(m.LOCATIONS), False) for l in m.LOCATIONS]


def generate(rows_per_design=ROWS, seed=SEED):
    rng = np.random.default_rng(seed)
    frames, feats, bases = [], [], []
    for design in m.DESIGNS:
        for cls, sub, share, strong in MIX:
            n_total = int(round(share * rows_per_design))
            for env, n in zip(m.ENVS, np.diff(np.linspace(0, n_total, len(m.ENVS) + 1).astype(int))):
                if n == 0:
                    continue
                detail = None if sub in ("drift", "arm_motion", "hand_on_watch") else sub
                vb, ve = m.simulate_pair(design, env, cls, detail, n=n, rng=rng, strong_drift=strong)
                vb = m.add_noise(vb, NOISE / 2, rng)
                ve = m.add_noise(ve, NOISE, rng)
                da, dp = m.rel_change(vb, ve)
                feats.append(np.hstack([da, dp]))
                bases.append(np.abs(vb))
                frames.append(pd.DataFrame({
                    "design": design, "environment": env, "label": cls, "subtype": sub,
                    "near_watch": cls == "other_person" and sub in ("wrist", "forearm"),
                    "score_pct": 100 * m.change_score(vb, ve)}, index=range(n)))
    meta = pd.concat(frames, ignore_index=True)
    X = np.vstack(feats).astype(np.float32)
    base = np.vstack(bases).astype(np.float32)
    F = len(m.FREQS)
    cols = [f"da_{i:03d}" for i in range(F)] + [f"dp_{i:03d}" for i in range(F)]
    return meta, X, base, cols


if __name__ == "__main__":
    meta, X, base, cols = generate()
    F = len(m.FREQS)
    df = pd.concat([meta, pd.DataFrame(X[:, :F], columns=cols[:F])], axis=1)
    df.to_csv("data/sparshaguard_synthetic_v0_3.csv", index=False, float_format="%.5g")
    # split in two files so each stays small enough to move around easily
    np.savez_compressed("data/sparshaguard_synthetic_v0_3.npz", X=X[:, :F],
                        cols=np.array(cols[:F]), freqs_hz=m.FREQS,
                        **{c: meta[c].to_numpy() for c in meta.columns})
    # phase and baseline in their own files so each stays under ~15 MB
    np.savez_compressed("data/sparshaguard_synthetic_v0_3_phase.npz", dp=X[:, F:],
                        cols=np.array(cols[F:]), freqs_hz=m.FREQS)
    np.savez_compressed("data/sparshaguard_synthetic_v0_3_baseline.npz", base=base, freqs_hz=m.FREQS)
    pd.DataFrame({"index": range(len(m.FREQS)), "freq_hz": m.FREQS}).to_csv(
        "data/sweep_frequencies.csv", index=False)
    print(df.shape)
    print(df.groupby(["design", "label"]).size().unstack())
