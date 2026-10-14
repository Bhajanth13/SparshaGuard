"""Time-domain simulation: a wearer goes about an hour of her day while the watch runs
the detection pipeline. Counts PIN prompts per hour (nuisance) and how often real
grabs get caught, for a range of thresholds.

Pipeline on the watch (5 frames/s, each frame = 16 averaged sweeps):
  1. score = RMS change of the current sweep vs the stored baseline
  2. baseline follows slow drift (EMA, 60 s) but FREEZES while score > enter threshold
     (re-baselines if frozen for more than 30 s without a prompt, e.g. wrist on a table)
  3. hysteresis: episode starts above T_enter, ends below 0.5 * T_enter
  4. optional classifier gate: frame must look like a hand at the watch (hers or his)
  5. prompt when the gate holds continuously for the sustain time

Run:  python event_stream.py   (about 30 minutes on 2 cores)
"""
import json

import joblib
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import lfilter

import plotstyle as ps
import sg_model as m

ps.apply()
FS = 5                      # frames per second
NOISE = 1e-3
DESIGN = "dual_shield"
CLF = joblib.load("models/svm_dual_shield.joblib")
HAND = ("self", "other_person")

# (kind, detail, events per hour, min s, max s); a duration given as LOGN(median, mean, cap) is log-normal
# Her hand on the watch: ~140 smartwatch sessions a day, about two thirds glances, so ~47 touch
# interactions a day = ~3 per hour over 16 waking hours [S38/E: waking hours]; half of sessions are
# under 5 s, the mean is ~9 s [S38]. Phone: ~85 uses a day (~5.3 per hour), more than half under
# 30 s, ~5 h a day in total (mean ~210 s) [S39].
LOGN = lambda median, mean, cap: ("logn", median, mean, cap)
SELF_D, PHONE_D = LOGN(5, 9, 60), LOGN(30, 212, 1800)
SCENARIOS = {
    # motion = strap-gap jitter on C_GB [E]; feet = C_BE change while walking: 160 pF on both
    # feet, 100 pF on one [S40] -> log-normal sigma ln(1.6)/2 = 0.235 (the sweep is insensitive to it)
    "Walking alone at night": dict(env="street_shoes", motion=0.015, feet=0.235, events=[
        ("self", None, 3, *SELF_D), ("object", "railing_hand", 4, 3, 10), ("no_contact", "bystander", 6, 2, 6),
        ("object", "phone", 5.3, *PHONE_D), ("object", "bag", 2, 60, 300)]),
    "Bus / metro commute": dict(env="street_shoes", motion=0.010, feet=0.03, events=[
        ("object", "railing_wrist", 6, 20, 120), ("object", "railing_hand", 6, 30, 300),
        ("no_contact", "bystander", 30, 5, 60), ("other_person", "shoulder", 10, 1, 3),
        ("other_person", "other_arm", 6, 1, 3), ("other_person", "forearm", 4, 0.5, 2.5),
        ("self", None, 3, *SELF_D), ("object", "phone", 5.3, *PHONE_D)]),
    "Desk / home": dict(env="barefoot_tile", motion=0.005, feet=0.01, events=[
        ("object", "wood_table", 10, 60, 600), ("self", None, 3, *SELF_D), ("object", "phone", 5.3, *PHONE_D),
        ("other_person", "wrist", 1, 2, 6)]),
}
EVENT_NAME = {("self", None): "her hand on watch", ("object", "railing_hand"): "hand on railing",
              ("object", "railing_wrist"): "strap on metal pole", ("no_contact", "bystander"): "bystander close",
              ("object", "phone"): "phone", ("object", "bag"): "bag", ("object", "wood_table"): "wrist on table",
              ("other_person", "shoulder"): "stranger brushes shoulder", ("other_person", "other_arm"): "stranger brushes arm",
              ("other_person", "forearm"): "stranger brushes forearm", ("other_person", "wrist"): "friend holds her wrist"}


def ou(T, tau_s, sigma, rng):
    a = np.exp(-1.0 / (FS * tau_s))
    return lfilter([sigma * np.sqrt(1 - a * a)], [1, -a], rng.normal(size=T))


def simulate_signal(env, events, T, rng, motion_sigma, feet_sigma=0.03):
    """Complex sense-node sweeps (T, F) for one wearer with the given events."""
    s1 = m.Sampler(rng, 1)
    p0 = m.sample_base(s1, DESIGN, env)
    p = {k: np.repeat(v, T) for k, v in p0.items()}
    p["hyd"] = np.clip(p["hyd"] + ou(T, 300, 0.15, rng), 0, 1)   # sweat, minutes [E]
    p["C_GB"] = p["C_GB"] * (1 + ou(T, 1.0, motion_sigma, rng))   # watch moving on wrist [E]
    p["C_BE"] = p["C_BE"] * np.exp(ou(T, 0.5, feet_sigma, rng))   # feet lifting while walking [S4/E]
    br = m.base_branches(p)
    for kind, detail, t0, t1 in events:
        p1 = {k: v[t0:t0 + 1] for k, v in p.items()}
        b0 = m.base_branches(p1)
        be = m.event_branches(p1, m.Sampler(rng, 1), DESIGN, kind, detail)
        for key in ("Y_B0", "Y_BE", "Y_0E", "Y_BA", "Y_A0"):
            br[key][t0:t1] += be[key] - b0[key]
    V = np.vstack([m.solve({k: v[i:i + 4000] for k, v in br.items()}) for i in range(0, T, 4000)])
    return m.add_noise(V, NOISE, rng)


def features(b, v):
    """Amplitude-only features, as the classifier was trained (Touché-style)."""
    return (np.abs(v) - np.abs(b))[None, :]


def run_pipeline(V, T_enter, sustain_s, use_clf=True, tau_base=60.0, max_freeze_s=30.0):
    T = len(V)
    alpha = 1.0 / (FS * tau_base)
    b = V[:FS * 5].mean(axis=0)                      # 5 s start-up baseline
    active, count, frozen, prompted = False, 0, 0, False
    prompts, scores = [], np.empty(T)
    need = int(round(sustain_s * FS))
    for t in range(T):
        sc = np.sqrt(np.mean((np.abs(V[t]) - np.abs(b)) ** 2))
        scores[t] = sc
        if not active and sc > T_enter:
            active, count, frozen, prompted = True, 0, 0, False
        elif active and sc < 0.5 * T_enter:
            active = False
        if active:
            frozen += 1
            hand = (CLF.predict(features(b, V[t]))[0] in HAND) if use_clf else True
            count = count + 1 if hand else 0
            if count >= need and not prompted:
                prompts.append(t)
                prompted = True
            if frozen > max_freeze_s * FS and not prompted:
                b = V[t].copy()                     # accept the new normal
                active = False
        else:
            b = (1 - alpha) * b + alpha * V[t]
    return np.array(prompts, dtype=int), scores


def duration(rng, a, b, c=None, d=None):
    """Uniform a..b s, or log-normal ('logn', median, mean, cap) with mean/median = exp(sigma^2 / 2)."""
    if a == "logn":
        sigma = np.sqrt(2 * np.log(c / b))
        return min(d, b * np.exp(sigma * rng.normal()))
    return rng.uniform(a, b)


def random_events(spec, T, rng):
    evs, labels = [], []
    for kind, detail, rate, *dur in spec:
        k = rng.poisson(rate * T / FS / 3600)
        for _ in range(k):
            d = int(duration(rng, *dur) * FS)
            t0 = int(rng.integers(FS * 10, T - d - 1))
            evs.append((kind, detail, t0, t0 + d))
            labels.append(EVENT_NAME[(kind, detail)])
    return evs, labels


def cause_of(t, evs, labels):
    hits = [lab for (k, d, t0, t1), lab in zip(evs, labels) if t0 <= t <= t1 + FS * 3]
    return hits[-1] if hits else "drift / no event"


# ----------------------------------------------------------------- experiment
GRID_T = [0.003, 0.004, 0.006, 0.01]      # enter threshold (RMS amplitude change, fraction of full scale)
GRID_S = [1.0, 2.0, 3.0]                     # sustain seconds
TIMELINE_T = 0.003                           # threshold shown in fig 8 (set from fig 9)
MIN_VALID_PCT = 0.25                         # thresholds below ~2x noise floor latch on (see fig 9)
HOURS_PER_SCENARIO = 2
N_ATTACK = 120


def nuisance_runs(rng):
    runs = []
    for name, sc in SCENARIOS.items():
        for h in range(HOURS_PER_SCENARIO):
            T = 3600 * FS
            evs, labels = random_events(sc["events"], T, rng)
            V = simulate_signal(sc["env"], evs, T, rng, sc["motion"], sc["feet"])
            runs.append((name, V, evs, labels))
    return runs


def attack_runs(rng):
    runs = []
    for loc in ["wrist", "forearm", "shoulder"]:
        for i in range(N_ATTACK):
            T = 40 * FS
            env = m.ENVS[i % len(m.ENVS)]
            evs = [("other_person", loc, 20 * FS, 30 * FS)]
            V = simulate_signal(env, evs, T, rng, 0.015, 0.05)
            runs.append((loc, V))
    return runs


def main():
    rng = np.random.default_rng(11)
    nuis = nuisance_runs(rng)
    atk = attack_runs(rng)
    table = []
    for use_clf in (True, False):
        for T_enter in GRID_T:
            for sus in GRID_S:
                row = {"classifier_gate": use_clf, "T_enter_pct": 100 * T_enter, "sustain_s": sus}
                per_scn, causes = {}, {}
                for name, V, evs, labels in nuis:
                    pr, _ = run_pipeline(V, T_enter, sus, use_clf)
                    per_scn.setdefault(name, []).append(len(pr))
                    for t in pr:
                        c = cause_of(t, evs, labels)
                        causes.setdefault(name, {}).setdefault(c, 0)
                        causes[name][c] += 1 / HOURS_PER_SCENARIO
                row["prompts_per_hour"] = {k: float(np.mean(v)) for k, v in per_scn.items()}
                row["prompt_causes_per_hour"] = causes
                det = {}
                for loc, V in atk:
                    pr, _ = run_pipeline(V, T_enter, sus, use_clf)
                    hit = np.any((pr >= 20 * FS) & (pr <= 30 * FS))
                    det.setdefault(loc, []).append(hit)
                row["detection_rate"] = {k: float(np.mean(v)) for k, v in det.items()}
                table.append(row)
                print(use_clf, T_enter, sus, {k: round(v, 1) for k, v in row["prompts_per_hour"].items()},
                      {k: round(v, 2) for k, v in row["detection_rate"].items()})
    with open("data/event_stream_results.json", "w") as fh:
        json.dump(table, fh, indent=1)
    fig_tradeoff(table)
    fig_timeline(np.random.default_rng(5))


def fig_tradeoff(table, sustain=2.0):
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    for gate, col, lab in [(False, ps.SERIES[0], "Threshold + 2 s sustain"),
                           (True, ps.SERIES[1], "Threshold + 2 s sustain + classifier gate")]:
        rows = [r for r in table if r["classifier_gate"] == gate and r["sustain_s"] == sustain
                and r["T_enter_pct"] >= MIN_VALID_PCT]
        x = [np.mean(list(r["prompts_per_hour"].values())) for r in rows]
        y = [100 * r["detection_rate"]["wrist"] for r in rows]
        ax.plot(x, y, "-o", color=col, ms=9, mec=ps.SURFACE, mew=1.5, label=lab)
        offs = [(14, 10), (-18, 10), (-26, -18), (26, -18)] if gate else [(30, -2), (30, -6), (14, -20), (-24, -20)]
        for xi, yi, r, o in zip(x, y, rows, offs):
            ax.annotate(f"{r['T_enter_pct']:g}%", (xi, yi), textcoords="offset points",
                        xytext=o, ha="center", fontsize=9, color=ps.INK2)
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50])
    ax.set_xticklabels(["1", "2", "5", "10", "20", "50"])
    ax.set_xlim(0.8, 60)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Nuisance PIN prompts per hour of Guard Mode (average of walking, commute, desk)")
    ax.set_ylabel("Wrist grabs caught (%)")
    ax.set_title("Sensitivity vs nuisance prompts: upper left is best", pad=22)
    sel = [r for r in table if not r["classifier_gate"] and r["sustain_s"] == sustain
           and r["T_enter_pct"] >= MIN_VALID_PCT]
    other = "; ".join(f"{loc} " + "/".join(f"{100 * r['detection_rate'][loc]:.0f}" for r in sel) + "%"
                      for loc in ("forearm", "shoulder"))
    ps.subtitle(ax, f"Point labels = enter threshold (% of full scale). Caught at those thresholds: {other}")
    ax.legend(loc="lower right")
    if any(r["T_enter_pct"] < MIN_VALID_PCT for r in table):
        fig.text(0.01, 0.005, f"Thresholds below {MIN_VALID_PCT:g}% (about twice the noise floor) are left out: "
                 "the exit level falls inside the noise, so the detector stays latched and the counts are meaningless.",
                 fontsize=8, color=ps.MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    ps.save(fig, "figures/fig9_tradeoff.png")


def fig_timeline(rng):
    """A scripted 3-minute walk with nuisances and two grabs."""
    T = 180 * FS
    script = [("object", "railing_hand", 10, 18, "hand on railing"),
              ("self", None, 35, 37, "adjusts her watch"),
              ("no_contact", "bystander", 50, 56, "bystander close"),
              ("object", "phone", 65, 95, "using phone"),
              ("other_person", "shoulder", 110, 120, "shoulder grab"),
              ("other_person", "wrist", 140, 152, "wrist grab")]
    evs = [(k, d, int(a * FS), int(b * FS)) for k, d, a, b, _ in script]
    V = simulate_signal("street_shoes", evs, T, rng, 0.015, 0.05)
    T_enter, sus = TIMELINE_T, 2.0
    pr, sc = run_pipeline(V, T_enter, sus, False)
    t = np.arange(T) / FS
    fig, ax = plt.subplots(figsize=(13, 4.8))
    for (k, d, a, b, lab), i in zip(script, range(len(script))):
        col = ps.SERIES[1] if k == "other_person" else ps.GRID
        ax.axvspan(a, b, color=col, alpha=0.35 if k == "other_person" else 0.8, lw=0)
        ax.text((a + b) / 2, 1.02, lab, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=8.5, color=ps.INK2, rotation=0)
    ax.plot(t, 100 * sc, color=ps.SERIES[0], lw=1.6, label="change score")
    ax.axhline(100 * T_enter, color=ps.INK2, ls="--", lw=1.2)
    ax.text(1, 100 * T_enter * 1.12, f"enter threshold {100 * T_enter:g}%", fontsize=8.5, color=ps.INK2)
    for p in pr:
        real = any(k == "other_person" and a <= p / FS <= b + 3 for k, d, a, b, _ in script)
        ax.axvline(p / FS, color=ps.CRITICAL, lw=2)
        ax.text(p / FS + 1, 0.98, "PIN prompt" if real else "PIN prompt\n(her own hand held 2 s)",
                transform=ax.get_xaxis_transform(), color=ps.CRITICAL, fontsize=9, fontweight="bold", va="top")
    ax.set_yscale("log")
    ax.set_xlim(0, 180)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Change vs baseline (% of full scale, RMS)")
    ax.set_title("A simulated 3-minute walk through the full pipeline", pad=28)
    fig.text(0.01, 0.01, f"Inner + outer electrode with driven shield; enter {100 * T_enter:g}%, sustain 2 s, threshold only. "
             "Orange bands = another person touching her.", fontsize=8.5, color=ps.MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    ps.save(fig, "figures/fig8_pipeline_timeline.png")
    np.savez_compressed("data/timeline_example.npz", t=t, score=sc, prompts=pr / FS)


if __name__ == "__main__":
    import sys
    if "--figs-only" in sys.argv:
        fig_tradeoff(json.load(open("data/event_stream_results.json")))
        fig_timeline(np.random.default_rng(5))
    else:
        main()
