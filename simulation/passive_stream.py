"""Time-domain study of the fused alarm logic: active sweep + passive static channel + accelerometer.

Since 28 Oct 2026 the signals include her own hand on the watch changing k, skin-stretch motion
artefacts, the 100 kHz transmit check and EDA (sg_newch.py). Rules compared (the PIN prompt is what
a rule fires):
  A   today: active sweep held 2 s (event_stream.py, 0.3 %, no classifier gate)
  F   fused (14 Oct design), on the new, more realistic signals:
        wrist path    active sweep held 2 s AND a 'person' contact step within 4 s before it
        anywhere path 'person' contact step AND agitation (>= 2 jerks over 1.25 g) within 3 s
        earthed metal (pulled to 0 V, or hum gone indoors) never counts as a person
  F2  fused with the new channels (default since 28 Oct 2026):
        a contact step that coincides with a transmit-current jump and matches the k change it
        predicts is her own hand on the watch, never a person
        wrist path    as F
        anywhere path 'person' step AND (agitation within 3 s OR a skin conductance response of at
                      least EDA_TH starting 0.8-4.5 s after it, for a grab that holds her still)
  F2-tx  F2 without the EDA path (to show what each new channel adds)
A transmit-based "rescue" (a hand landing on the watch whose static change exceeds its k change =
another person) was tried on 28 Oct 2026: +6 points of wrist grabs at 10 V for ~0.5 more unwanted
prompts per hour while walking, so it is not used.
Active-sweep outcomes come from event_stream.py (results/data/event_stream_results.json): a wrist grab
starts a 2 s hold 92.5 % of the time, and each harmless cause starts one at the rates found there.
The passive channel and accelerometer are simulated sample by sample (sg_passive.py).

Run:  python simulation/passive_stream.py   (~3 min)   -> results/figures/fig17, fig18, results/data/passive_stream_results.json
"""
import json
import zlib

import matplotlib.pyplot as plt
import numpy as np

import plotstyle as ps
import sg_newch as NC
import sg_passive as P
from paths import DATA, FIGURES

ps.apply()
LOCS = ["wrist", "forearm", "upper_arm", "other_arm", "shoulder", "waist", "face_hair"]
LOC_LABEL = {"wrist": "Wrist", "forearm": "Forearm", "upper_arm": "Upper arm", "other_arm": "Other arm",
             "shoulder": "Shoulder", "waist": "Waist", "face_hair": "Face / hair"}
CTX = {"walking": "Walking alone at night", "bus": "Bus / metro commute", "desk": "Desk / home"}
V0S = [0.3, 1.0, 3.0, 10.0, 30.0, 100.0]
HOURS = 6                        # simulated hours per place and voltage
PULL = 0.7                       # share of grabs that pull or shake her arm [E]; 70 % of women report
                                 # significant freezing during sexual assault [S68], so many grabs only hold
SELF_RATE = 3.0                  # touch sessions on the watch per hour [S38]
SELF_D = ("logn", 5, 9, 60)      # session length [S38]
# harmless events per hour [E, as event_stream.py where it has them]; phone use 5.3 per hour,
# log-normal duration, median 30 s, mean 212 s [S39] (PHONE_D from event_stream.py)
PHONE_D = ("logn", 30, 212, 1800)
BACKGROUND = {
    "walking": [("earthed", None, 4, 3, 10), ("approach", None, 6, 2, 6), ("gesture", None, 15, 0.3, 0.3),
                ("phone", None, 5.3, *PHONE_D)],
    "bus": [("earthed", None, 12, 20, 120), ("approach", None, 30, 5, 60), ("brush", "shoulder", 10, 1, 3),
            ("brush", "other_arm", 6, 1, 3), ("brush", "forearm", 4, 0.5, 2.5), ("gesture", None, 15, 0.3, 0.3),
            ("jolt", None, 12, 0.3, 0.3), ("phone", None, 5.3, *PHONE_D)],
    "desk": [("brush", "wrist", 1, 2, 6), ("gesture", None, 15, 0.3, 0.3), ("phone", None, 5.3, *PHONE_D)],
}
# harmless causes of an active-sweep 2 s hold, per hour, read from event_stream.py (rule A at 0.3 %,
# 2 s, no classifier gate), with what the passive channel sees at that moment and how long it lasts
CAUSE_MAP = {"her hand on watch": ("none", SELF_D), "phone": ("phone", PHONE_D),
             "bystander close": ("approach", (5, 60)), "strap on metal pole": ("earthed", (20, 120)),
             "hand on railing": ("earthed", (30, 300)), "wrist on table": ("none", (60, 600)),
             "bag": ("none", (60, 300)), "friend holds her wrist": ("person", (2, 6)),
             "stranger brushes shoulder": ("person", (1, 3)), "stranger brushes arm": ("person", (1, 3)),
             "stranger brushes forearm": ("person", (0.5, 2.5))}
_ES = [r for r in json.load(open(DATA / "event_stream_results.json"))
       if not r["classifier_gate"] and abs(r["T_enter_pct"] - 0.3) < 1e-9 and r["sustain_s"] == 2.0][0]
P_ACTIVE_WRIST = _ES["detection_rate"]["wrist"]
_CTX_ES = {"walking": "Walking alone at night", "bus": "Bus / metro commute", "desk": "Desk / home"}
ACTIVE_CAUSES = {c: [(name, CAUSE_MAP[name][0], rate, *CAUSE_MAP[name][1])
                     for name, rate in _ES["prompt_causes_per_hour"][_CTX_ES[c]].items() if name in CAUSE_MAP]
                 for c in _CTX_ES}
# a friend holding her wrist is a real touch: keep it at its event rate (1 per hour at a desk) times
# the sweep's wrist detection, even when the short event_stream run happened to draw none
if not any(n == "friend holds her wrist" for n, *_ in ACTIVE_CAUSES["desk"]):
    ACTIVE_CAUSES["desk"].append(("friend holds her wrist", "person", 1.0 * P_ACTIVE_WRIST, 2, 6))


def duration(rng, a, b, c=None, d=None):
    """Uniform a..b s, or log-normal ('logn', median, mean, cap), as event_stream.duration."""
    if a == "logn":
        return min(d, b * np.exp(np.sqrt(2 * np.log(c / b)) * rng.normal()))
    return rng.uniform(a, b)


def stranger_voltage(v0, rng):
    return v0 * np.exp(rng.normal(0, 0.7)) * rng.choice([-1.0, 1.0])     # [E]


def add_event(sc, kind, detail, t0, t1, v0, rng, attack=False):
    if kind in ("person", "brush"):
        loc = detail or "wrist"
        sc.add(kind="person", t0=t0, t1=t1, loc=loc, attack=attack, pull=attack and rng.random() < PULL,
               v_a=stranger_voltage(v0, rng), face=loc == "wrist" and rng.random() < NC.P_STRANGER_FACE)
    elif kind == "self":                                # her hand on the watch: taps or the palm over the face
        sc.add(kind="self", t0=t0, t1=t1, cover=rng.random() < NC.P_COVER)
    elif kind == "earthed":
        sc.add(kind="earthed", t0=t0, t1=t1)
    elif kind == "approach":
        sc.add(kind="approach", t0=t0, t1=t1, dmin=rng.uniform(0.2, 0.6), v_a=stranger_voltage(v0, rng))
    elif kind == "phone":                               # a small floating object: 4-12 pF at ~0 V [G/E]
        sc.add(kind="person", t0=t0, t1=t1, loc="wrist", attack=False, pull=False, v_a=0.0, small=True)
    elif kind in ("gesture", "jolt"):
        sc.add(kind=kind, t0=t0, t1=t1)


def scene_steps(sc):
    """Static steps seen by the 14 Oct firmware (st) and by the firmware with the transmit check
    (st2), the accelerometer, and the EDA trace."""
    ti, acc = sc.accel()                                # first: it records the arm jerks
    t, v, hum = sc.body_voltage()
    u = sc.watch_signal(v)
    rms = P.FRONT[sc.front]["adc"] / 4
    st = P.contact_steps(u, rms, sc.heel, hum, sc.indoor)
    st2 = P.contact_steps(u, rms, sc.heel, hum, sc.indoor, tx=sc.tx, gain=sc.tx_gain()) if sc.new else st
    eda = NC.EDA(sc.rng, sc.ctx, sc.T)
    for ev in sc.events:
        if ev["kind"] == "person" and not ev.get("small"):
            eda.respond(ev["t0"], "attack" if ev.get("attack") else ("friend" if ev.get("loc") == "wrist" else "brush"))
    jt = [tj for tj, _ in sc.jerks]
    for tj in jt:
        eda.jerk(tj)
    te, sce = eda.signal()
    return st, st2, ti, acc, (te, sce, jt)


def scr(e, t0, th=None):
    te, sce, jt = e
    return NC.scr_after(te, sce, t0, jt, NC.EDA_TH if th is None else th)


# ------------------------------------------------------------------------------ grab trials
def grab_trials(ctx, loc, v0, front, n, seed):
    rng = np.random.default_rng(seed)
    hit = {"A": 0, "F": 0, "F2": 0, "F2-tx": 0}
    for _ in range(n):
        sc = P.Scene(ctx, 16, v0, front, rng, new=True)
        va = stranger_voltage(v0, rng)
        sc.add(kind="approach", t0=6.5, t1=8.0, dmin=0.25, v_a=va, stay=True)   # he walks up
        sc.add(kind="person", t0=8.0, t1=14.0, loc=loc, attack=True, pull=rng.random() < PULL, v_a=va,
               face=loc == "wrist" and rng.random() < NC.P_STRANGER_FACE)
        st, st2, ti, acc, e = scene_steps(sc)
        active = loc == "wrist" and rng.random() < P_ACTIVE_WRIST          # starts its hold at 8 s, fires at 10 s
        person = [s for s in st if s[2] == "person" and 7.9 <= s[0] <= 8.2]
        person2 = [s for s in st2 if s[2] == "person" and 7.9 <= s[0] <= 8.2]
        agit = any(P.agitation(ti, acc, s[0], sc.heel) for s in person)
        agit2 = any(P.agitation(ti, acc, s[0], sc.heel) for s in person2)
        eda2 = any(scr(e, s[0]) for s in person2)
        hit["A"] += active
        hit["F"] += (active and bool(person)) or agit
        hit["F2-tx"] += (active and bool(person2)) or agit2
        hit["F2"] += (active and bool(person2)) or agit2 or eda2
    return {k: v / n for k, v in hit.items()}


# ------------------------------------------------------------------------------ daily life
def daily_life(ctx, v0, front, hours, seed):
    rng = np.random.default_rng(seed)
    T = 3600
    fp = {"A": 0.0, "F": 0.0, "F2": 0.0, "F2-tx": 0.0}
    causes = {"F": {}, "F2": {}, "F2-tx": {}}

    def count(rule, name):
        fp[rule] += 1
        causes[rule][name] = causes[rule].get(name, 0) + 1
    self_holds = sum(r for n, _, r, *_ in ACTIVE_CAUSES[ctx] if n == "her hand on watch")
    for _ in range(hours):
        sc = P.Scene(ctx, T, v0, front, rng, new=True)
        # her hand on the watch: ~3 touch sessions per hour [S38]; the ones that start a 2 s hold come below
        for _ in range(rng.poisson(max(0.0, SELF_RATE - self_holds))):
            d = duration(rng, *SELF_D)
            t0 = rng.uniform(10, T - d - 5)
            add_event(sc, "self", None, t0, t0 + d, v0, rng)
        for kind, detail, rate, *dur in BACKGROUND[ctx]:
            for _ in range(rng.poisson(rate)):
                d = duration(rng, *dur)
                t0 = rng.uniform(10, T - d - 5)
                add_event(sc, kind, detail, t0, t0 + d, v0, rng)
                if kind == "brush":
                    sc.events[-1]["label"] = "stranger brushes her " + detail
        # harmless active-sweep holds and what the passive channel sees then
        holds = []
        for name, pas, rate, *dur in ACTIVE_CAUSES[ctx]:
            for _ in range(rng.poisson(rate)):
                d = duration(rng, *dur)
                t0 = rng.uniform(10, T - d - 5)
                holds.append((t0, d, name))
                if pas in ("earthed", "approach", "phone", "person"):
                    add_event(sc, pas, "wrist", t0, t0 + d, v0, rng)
                if name == "her hand on watch":
                    add_event(sc, "self", None, t0, t0 + d, v0, rng)
        st, st2, ti, acc, e = scene_steps(sc)
        fp["A"] += len(holds)
        for rule, steps in (("F", st), ("F2-tx", st2), ("F2", st2)):
            person = [s for s in steps if s[2] == "person"]
            for t0, d, name in holds:
                if any(t0 - 4 <= s[0] <= t0 + 2 for s in person):
                    count(rule, name)
            for s in person:
                if P.agitation(ti, acc, s[0], sc.heel):
                    count(rule, "contact + agitation")
                elif rule == "F2" and scr(e, s[0]):
                    count(rule, "contact + skin response (EDA)")
    return {k: v / hours for k, v in fp.items()}, {r: {k: v / hours for k, v in c.items()} for r, c in causes.items()}


def seed(*parts):
    return zlib.crc32(repr(parts).encode())


def one_setting(args):
    front, v0 = args
    cov = {ctx: {loc: grab_trials(ctx, loc, v0, front, 40, seed(ctx, loc, v0, front)) for loc in LOCS} for ctx in CTX}
    fps = {ctx: daily_life(ctx, v0, front, HOURS, seed(ctx, v0, front)) for ctx in CTX}
    return front, v0, cov, fps


def main():
    from multiprocessing import Pool
    res = {"improved": {}, "current": {}}
    with Pool() as pool:                                # each setting has its own seeds: same results in any order
        done = pool.map(one_setting, [(f, v) for f in ("improved", "current") for v in V0S])
    for front, v0, cov, fps in done:
        row = {"coverage": cov, "prompts_per_hour": {c: fps[c][0] for c in CTX}, "causes": {c: fps[c][1] for c in CTX}}
        R = ("A", "F", "F2", "F2-tx")
        row["body_avg"] = {r: float(np.mean([cov[c][l][r] for c in CTX for l in LOCS])) for r in R}
        row["fp_avg"] = {r: float(np.mean([row["prompts_per_hour"][c][r] for c in CTX])) for r in R}
        # a friend holding her wrist is a real touch by another person: the PIN is the right answer there
        fr = {r: float(np.mean([row["causes"][c].get(r, {}).get("friend holds her wrist", 0) for c in CTX])) for r in R[1:]}
        fr["A"] = sum(r for n, _, r, *_ in ACTIVE_CAUSES["desk"] if n == "friend holds her wrist") / 3
        row["fp_avg_strangers_excl_friend"] = {r: row["fp_avg"][r] - fr[r] for r in R}
        res[front][str(v0)] = row
        print(front, v0, {k: round(100 * x, 1) for k, x in row["body_avg"].items()}, {k: round(x, 2) for k, x in row["fp_avg"].items()}, {k: round(x, 2) for k, x in row["fp_avg_strangers_excl_friend"].items()}, flush=True)
    json.dump(res, open(DATA / "passive_stream_results.json", "w"), indent=1)
    figures(res)


def figures(res):
    rules = [("A", "A · active sweep only", ps.SERIES[0]),
             ("F", "F · fused (14 Oct): static step + motion", ps.SERIES[3]),
             ("F2", "F2 · fused + transmit check + EDA", ps.SERIES[2])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 6.4))
    for front, ls in (("improved", "-"), ("current", ":")):
        xs = [float(v) for v in res[front]]
        for r, lab, col in rules:
            if r == "A" and front == "current":
                continue
            a1.plot(xs, [100 * res[front][v]["body_avg"][r] for v in res[front]], ls, marker="o", color=col, ms=5,
                    label=f"{lab}" + ("" if r == "A" else f" ({P.FRONT[front]['label']})"))
            a2.plot(xs, [res[front][v]["fp_avg_strangers_excl_friend"][r] for v in res[front]], ls, marker="o", color=col, ms=5)
    for ax in (a1, a2):
        ax.set_xscale("log")
        ax.set_xlabel("Typical body voltage of each person (V)  ·  not yet measured on Indian floors")
        ax.axvspan(250, 300, color=ps.GRID)
    a1.set_ylim(0, 100)
    a1.set_ylabel("Grabs caught, averaged over 7 body locations and 3 places (%)")
    a1.set_title("Coverage of her whole body", pad=22)
    ps.subtitle(a1, "Solid: bootstrapped input + ADS1115; dotted: current input + ESP32 ADC")
    h, l = a1.get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=8.5, bbox_to_anchor=(0.5, 0.0))
    a2.set_ylim(0, None)
    a2.axhline(1 / 16, color=ps.MUTED, ls="--", lw=1.1)
    a2.text(0.32, 1 / 16 + 0.12, "≈ 1 per 16-hour day", fontsize=8.5, color=ps.INK2)
    a2.set_ylabel("Unwanted PIN prompts per hour (walking, bus, desk average)")
    a2.set_title("Unwanted PIN prompts", pad=22)
    ps.subtitle(a2, "Not counted: a friend holding her wrist (a real touch by another person; her PIN handles it)")
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    ps.save(fig, FIGURES / "fig17_fused_tradeoff.png")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    y = np.arange(len(LOCS))
    for ax, v0 in zip(axes, ("1.0", "10.0", "100.0")):
        cov = res["improved"][v0]["coverage"]
        for j, (r, lab, col) in enumerate(rules):
            ax.barh(y + (j - 1) * 0.27, [100 * np.mean([cov[c][l][r] for c in CTX]) for l in LOCS], height=0.25, color=col, label=lab)
        ax.set_yticks(y)
        ax.set_yticklabels([LOC_LABEL[l] for l in LOCS])
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("Grabs caught (%)")
        ax.set_title(f"Bodies at ~{float(v0):g} V", pad=8)
        ax.grid(axis="y", visible=False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=1, fontsize=9, bbox_to_anchor=(0.99, 0.995))
    fig.suptitle("Where on her body a grab is caught\n(time-domain simulation, bootstrapped input + ADS1115)",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=ps.INK)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    ps.save(fig, FIGURES / "fig18_fused_locations.png")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--figures"]:
        figures(json.load(open(DATA / "passive_stream_results.json")))
    else:
        main()
