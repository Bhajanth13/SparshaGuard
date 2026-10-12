"""Train contact classifiers on the synthetic dataset and evaluate them.

Run:  python train_classifier.py
Writes figures/fig5..fig7, data/classifier_results.json, models/svm_dual_shield.joblib
"""
import json
import os

import joblib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from sg_features import compress
from sklearn.svm import SVC

import plotstyle as ps
import sg_model as m

ps.apply()
os.makedirs("models", exist_ok=True)
D = np.load("data/sparshaguard_synthetic_v0_3.npz", allow_pickle=True)
X_all = D["X"]
F = len(D["freqs_hz"])
FEAT = slice(0, F)                          # amplitude change only, as Touché measures
design, env, label, sub = D["design"], D["environment"], D["label"], D["subtype"]
CLASS_LABEL = {"no_contact": "No contact", "object": "Object", "self": "Her own hand",
               "other_person": "Other person\n(at the wrist)"}
results = {}
NEAR = ["wrist"]          # grabs the sensor can see; forearm grabs fell below the noise with the 3D coupling


def models():
    return {
        "SVM (RBF)": make_pipeline(FunctionTransformer(compress), StandardScaler(), SVC(C=10, gamma="scale")),
        "Random forest": RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=0),
    }


def per_subtype_rate(y_pred, subs):
    """Share of samples in each subtype that the model calls 'other_person' (= PIN prompt)."""
    return {s: float(np.mean(y_pred[subs == s] == "other_person")) for s in np.unique(subs)}


cms = {}
for d in m.DESIGNS:
    idx = np.where(design == d)[0]
    X, y, s, e = X_all[idx][:, FEAT], label[idx], sub[idx], env[idx]
    # Grabs away from the watch are physically (almost) invisible to the sensor, so they
    # are NOT used for training. They are only used to test how often they get caught.
    far = (y == "other_person") & ~np.isin(s, NEAR)
    pool = np.where(~far)[0]
    tr, te = train_test_split(pool, test_size=0.25, random_state=0, stratify=s[pool])
    te_all = np.concatenate([te, np.where(far)[0]])
    res = {}
    for name, mdl in models().items():
        mdl.fit(X[tr], y[tr])
        yp = mdl.predict(X[te])
        yp_all = mdl.predict(X[te_all])
        hand_true = np.isin(y[te], ["self", "other_person"])
        hand_pred = np.isin(yp, ["self", "other_person"])
        r = {"accuracy_4class": float(accuracy_score(y[te], yp)),
             "accuracy_hand_at_watch_vs_rest": float(np.mean(hand_true == hand_pred)),
             "prompt_rate_by_subtype": per_subtype_rate(yp_all, s[te_all]),
             "hand_rate_by_subtype": {sb: float(np.mean(np.isin(yp_all[s[te_all] == sb], ["self", "other_person"])))
                                      for sb in np.unique(s[te_all])}}
        # generalisation: train without the car, test only in the car
        car = e == "car_seat"
        mdl2 = models()[name]
        mdl2.fit(X[~car & ~far], y[~car & ~far])
        r["accuracy_unseen_car_env"] = float(accuracy_score(y[car & ~far], mdl2.predict(X[car & ~far])))
        res[name] = r
        if name == "SVM (RBF)":
            cms[d] = confusion_matrix(y[te], yp, labels=m.CLASSES, normalize="true")
            if d == "dual_shield":
                joblib.dump(mdl, "models/svm_dual_shield.joblib")
    results[d] = res
    print(d, {k: round(v["accuracy_4class"], 3) for k, v in res.items()},
          "car:", {k: round(v["accuracy_unseen_car_env"], 3) for k, v in res.items()})

with open("data/classifier_results.json", "w") as fh:
    json.dump(results, fh, indent=1)

# ------------------------------------------------ Fig 5: confusion matrices
fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
for ax, d in zip(axes, m.DESIGNS):
    cm = cms[d]
    ax.imshow(cm, cmap=plt.matplotlib.colors.LinearSegmentedColormap.from_list(
        "b", ["#fcfcfb", "#cde2fb", "#6da7ec", "#2a78d6", "#104281"]), vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{100 * cm[i, j]:.0f}%", ha="center", va="center", fontsize=10,
                    color="white" if cm[i, j] > 0.55 else ps.INK)
    ax.set_xticks(range(4))
    ax.set_xticklabels([CLASS_LABEL[c] for c in m.CLASSES], rotation=20, ha="right")
    ax.set_yticks(range(4))
    ax.set_yticklabels([CLASS_LABEL[c] for c in m.CLASSES])
    ax.grid(False)
    ax.set_xlabel("Predicted")
    acc = results[d]["SVM (RBF)"]["accuracy_4class"]
    ax.set_title(f"{ps.DESIGN_LABEL[d]}\nSVM accuracy {100 * acc:.0f}%", fontsize=11)
axes[0].set_ylabel("True class")
fig.suptitle("Contact classifier on synthetic data (rows sum to 100%)", x=0.01, ha="left",
             fontweight="bold", fontsize=13)
fig.text(0.01, 0.905, "Trained and tested on events the sensor can physically see (grabs at the wrist). "
         "Grabs elsewhere are tested separately in fig 6.", fontsize=9.5, color=ps.INK2)
fig.tight_layout(rect=(0, 0, 1, 0.9))
ps.save(fig, "figures/fig5_confusion_matrices.png")

# ------------------------------------- Fig 6: prompt rate by situation
rows_other = [("other_person", l, ps.LOC_LABEL[l]) for l in m.LOCATIONS]
rows_nuis = [("no_contact", "drift", "No touch: sweat drift"),
             ("no_contact", "arm_motion", "No touch: arm swinging"),
             ("no_contact", "bystander", "Bystander very close"),
             ("self", "hand_on_watch", "Her hand on the watch"),
             ("object", "railing_hand", "Hand on metal railing"),
             ("object", "railing_wrist", "Strap pressed on metal pole"),
             ("object", "phone", "Holding a phone"),
             ("object", "wood_table", "Wrist on wooden table"),
             ("object", "bag", "Holding a bag")]
rows = rows_other + rows_nuis
fig, ax = plt.subplots(figsize=(11, 7.4))
series6 = [("Classified 'other person'", "prompt_rate_by_subtype", ps.SERIES[1]),
           ("Classified as any hand at the watch (hers or his)", "hand_rate_by_subtype", ps.SERIES[0])]
for (lab, key, col), off in zip(series6, [-0.15, 0.15]):
    rates = results["dual_shield"]["SVM (RBF)"][key]
    ys = np.arange(len(rows)) + off
    vals = [100 * rates[sb] for _, sb, _ in rows]
    for y, v in zip(ys, vals):
        ax.plot([0, v], [y, y], color=col, lw=2, alpha=0.45)
    ax.plot(vals, ys, "o", ms=7.5, color=col, mec=ps.SURFACE, mew=1.3, label=lab)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[2] for r in rows])
ax.invert_yaxis()
ax.axhspan(len(rows_other) - 0.5, len(rows) - 0.5, color=ps.GRID, alpha=0.45, zorder=0)
ax.text(101, len(rows_other) - 0.3, "nuisance — want 0%", ha="right", va="top", fontsize=9, color=ps.INK2)
ax.text(101, -0.45, "real grabs — want 100%", ha="right", va="top", fontsize=9, color=ps.INK2)
ax.set_xlim(0, 102)
ax.set_xlabel("Share of events, %")
ax.grid(axis="y", visible=False)
ax.set_title("What the classifier says, situation by situation", pad=22)
ps.subtitle(ax, "Inner + outer electrode with driven shield. SVM, held-out data, one event, before the sustain rule and motion fusion.")
ax.legend(loc="lower right")
fig.tight_layout()
ps.save(fig, "figures/fig6_prompt_rate_by_situation.png")

# --------------------------------------------- Fig 7: dataset map (PCA)
idx = np.where(design == "dual_shield")[0]
Xd = StandardScaler().fit_transform(np.arcsinh(X_all[idx][:, FEAT] / 2e-3))  # compress the huge range
Z = PCA(n_components=2, random_state=0).fit_transform(Xd)
yd, sd = label[idx], sub[idx]
groups = [("No contact", (yd == "no_contact"), ps.MUTED, "o"),
          ("Object", (yd == "object"), ps.SERIES[6], "s"),
          ("Her own hand", (yd == "self"), ps.SERIES[2], "^"),
          ("Other person, at the wrist", (yd == "other_person") & np.isin(sd, NEAR), ps.SERIES[1], "D"),
          ("Other person, elsewhere", (yd == "other_person") & ~np.isin(sd, NEAR), ps.SERIES[0], "v")]
fig, ax = plt.subplots(figsize=(11.5, 6.4))
rng = np.random.default_rng(0)
for lab, mask, col, mk in groups:
    pts = np.where(mask)[0]
    pts = rng.choice(pts, min(400, len(pts)), replace=False)
    ax.scatter(Z[pts, 0], Z[pts, 1], s=16, color=col, marker=mk, alpha=0.75,
               edgecolors=ps.SURFACE, linewidths=0.4, label=lab)
ax.set_xlabel("Principal component 1")
ax.set_ylabel("Principal component 2")
ax.set_title("Map of the synthetic dataset", pad=22)
ps.subtitle(ax, "One point per simulated event (inner + outer + shield). Grabs away from the watch fall inside the no-contact cloud.")
ax.legend(loc="best", markerscale=1.6)
fig.tight_layout()
ps.save(fig, "figures/fig7_dataset_map.png")
print("done")
