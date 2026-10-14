"""Fusion study: how much of her body can SparshaGuard cover, and at what cost in unwanted prompts?

Adds a passive static-charge channel (charge sharing between two bodies at the moment of contact,
anywhere on her body) to the active capacitive sweep, and compares three alarm rules:

  A  active sweep only (the current design; numbers from event_stream.py)
  B  active sweep OR a passive contact step (earthed objects rejected indoors by the 50 Hz hum)
  C  active sweep OR (a passive contact step AND motion agitation within 3 s)

Physics of the passive step (tags as in sg_model.py):
  two bodies C_A, C_B to ground (110-250 pF each [S4]) at voltages V_A, V_B touch, either skin to
  skin or through fabric acting as a series capacitor C_c (er 1.2-5.1, 0.16-0.58 mm per layer [S7],
  40-80 cm^2 of hand [S13]):
      her jump  dV_B = (V_A - V_B) / (C_B (1/C_A + 1/C_B + 1/C_c))        (charge conservation)
  the floating watch sees  k = C_GE / (C_GE + C_GB + C_in)  of it (whole_body.py, fig 11):
      current front end  C_GE 0.6-2 pF [S5/S11], C_GB 12.4 pF (model), C_in 5 pF   -> k ~ 6 %
      improved front end C_GB 2 pF, C_in 0.5 pF (bootstrapped input, good shield)   -> k ~ 30 %
  body voltage from walking scales with humidity: on vinyl ~250 V at 65-90 % RH and ~12 kV at
  10-20 % RH [S17]; log-interpolated in between [E]. Other floors (road, bus, tiles) 0.1-1 x vinyl
  [E]. At the moment of contact each body sits at a random point of its charging cycle, 0.1-1 x
  that level, with random polarity (different soles) [E]. Charge leaks away with tau = R C,
  R ~ 2e10 ohm [S18] -> ~3 s, so a person who has stood still for > 10 s is nearly discharged.
  Bengaluru humidity: 37 % (Mar-Apr afternoons), 50 % (annual afternoon), 89 % (mornings) [S23].
  ADC noise: ADS1115 ~2 mV, ESP32 built-in ~21.8 mV [S15]; a step must exceed 3x that [E].

Rejection of passive false steps:
  her own footsteps: steps inside a +-50 ms window round each heel strike (accelerometer) are
  ignored, losing 2 x 0.05 s x 1.5 steps/s = 15 % of real touches while walking [E];
  a person only approaching changes her voltage over > 0.3 s (walking speed), a touch in < 10 ms,
  so approaches are rejected by rise time [physics; assumed perfect here, E];
  earthed objects (railing, pole, tap) pull her to 0 V and kill the 50 Hz hum indoors [S22];
  rejected 90 % of the time indoors, never outdoors or on a bus [E].
Motion confirmation (rule C): agitation within 3 s follows 50-90 % of grabs [E, no source found];
  it also follows a harmless contact 5 % (desk), 10 % (walking), 20 % (bus) of the time [E].
Event rates per hour are the ones event_stream.py uses [E].

Run:  python fusion_study.py     (~10 s)    -> figures/fig15, fig16, data/fusion_results.json
"""
import json

import matplotlib.pyplot as plt
import numpy as np

import plotstyle as ps

ps.apply()
RNG = np.random.default_rng(2026)
N = 20000
pF, EPS0, CM2 = 1e-12, 8.854e-12, 1e-4

LOCS = ["wrist", "forearm", "upper_arm", "other_arm", "shoulder", "waist", "face_hair"]
LOC_LABEL = {"wrist": "Wrist", "forearm": "Forearm", "upper_arm": "Upper arm", "other_arm": "Other arm",
             "shoulder": "Shoulder", "waist": "Waist", "face_hair": "Face / hair"}
BARE = {"wrist": 0.9, "forearm": 0.6, "upper_arm": 0.3, "other_arm": 0.5,      # as sg_model.py [E]
        "shoulder": 0.1, "waist": 0.05, "face_hair": 0.8}
ACTIVE_CATCH = {"wrist": 0.925, "forearm": 0.0, "upper_arm": 0.0, "other_arm": 0.0,   # event_stream.py
                "shoulder": 0.0, "waist": 0.0, "face_hair": 0.0}
RH_CASES = [("Dry: 37 % RH", 37), ("Typical: 50 % RH", 50), ("Humid: 89 % RH", 89)]
FRONT = {"current": dict(cgb=12.4 * pF, cin=5 * pF, noise=21.8e-3, label="Current front end, ESP32 ADC"),
         "improved": dict(cgb=2.0 * pF, cin=0.5 * pF, noise=2e-3, label="Improved input + ADS1115")}
CONTEXTS = {   # floor factor range vs vinyl [E], walking?, indoors?, motion false-confirm rate [E]
    "walking": dict(label="Walking alone at night", floor=(0.1, 0.5), walking=True, indoor=False, imu_fp=0.10),
    "bus": dict(label="Bus / metro commute", floor=(0.3, 1.0), walking=False, indoor=False, imu_fp=0.20),
    "desk": dict(label="Desk / home", floor=(0.3, 1.0), walking=False, indoor=True, imu_fp=0.05),
}
# harmless events per hour that cause a passive step (rates from event_stream.py) [E]
PERSON_CONTACTS = {"walking": 0.0, "bus": 10 + 6 + 4, "desk": 1.0}       # brushes, friend's hand
OBJECT_CONTACTS = {"walking": 4.0, "bus": 6 + 6, "desk": 0.0}            # railing, pole (earthed metal)
ACTIVE_PROMPTS = {"walking": 1.5, "bus": 7.5, "desk": 7.5}                # rule A, event_stream.py


def walk_voltage(rh):
    """Typical body voltage from walking on vinyl at this RH: log-interpolation of the Desco table
    (12 kV at 15 % RH, 250 V at 77.5 % RH) [S17]; held flat outside that range [E]."""
    t = np.clip((rh - 15) / (77.5 - 15), 0, 1)
    return np.exp(np.log(12000) + (np.log(250) - np.log(12000)) * t)


def body_voltage(rh, floor, n, rng, v0=None):
    """Body voltage at the moment of contact. With v0 given, the typical magnitude is v0 (the
    unknown this study sweeps) with a factor-of-e spread; otherwise it follows the vinyl table."""
    if v0 is not None:
        mag = v0 * np.exp(rng.normal(0, 1.0, n))
    else:
        lo, hi = floor
        mag = walk_voltage(rh) * rng.uniform(lo, hi, n) * rng.uniform(0.1, 1.0, n)
    return mag * rng.choice([-1.0, 1.0], n)


def watch_fraction(front, n, rng):
    cge = np.exp(rng.uniform(np.log(0.6), np.log(2.0), n)) * pF      # [S5/S11]
    f = FRONT[front]
    return cge / (cge + f["cgb"] + f["cin"])


def her_jump(va, vb, ca, cb, cc):
    return (va - vb) / (cb * (1 / ca + 1 / cb + 1 / cc))


def passive_detect_person(loc, rh, ctx, front, rng, n=N, v0=None):
    """Probability that a person touching her at loc gives a usable passive contact step."""
    c = CONTEXTS[ctx]
    ca, cb = rng.uniform(110, 250, n) * pF, rng.uniform(110, 250, n) * pF       # [S4]
    va, vb = body_voltage(rh, c["floor"], n, rng, v0), body_voltage(rh, c["floor"], n, rng, v0)
    bare = rng.random(n) < BARE[loc]
    area = rng.uniform(40, 80, n) * CM2                                            # [S13]
    cloth = EPS0 * rng.uniform(1.2, 5.1, n) * area / (rng.uniform(0.16e-3, 0.58e-3, n) * rng.uniform(1, 2, n))  # [S7]
    cc = np.where(bare, 1e-6, cloth)                     # bare skin: effectively a short
    step = np.abs(watch_fraction(front, n, rng) * her_jump(va, vb, ca, cb, cc))
    ok = step > 3 * FRONT[front]["noise"]
    if c["walking"]:
        ok &= rng.random(n) > 0.15                       # lost inside the heel-strike window [E]
    return float(ok.mean()), step


def passive_detect_object(rh, ctx, front, rng, n=N, v0=None):
    """Probability that touching an earthed object gives a step that is NOT rejected."""
    c = CONTEXTS[ctx]
    vb = body_voltage(rh, c["floor"], n, rng, v0)
    step = np.abs(watch_fraction(front, n, rng) * vb)    # she is pulled to 0 V
    ok = step > 3 * FRONT[front]["noise"]
    if c["indoor"]:
        ok &= rng.random(n) > 0.90                       # hum test rejects 90 % indoors [E]
    return float(ok.mean())


def run(front="improved", imu_attack=0.7, v0=None, cases=None):
    rng = np.random.default_rng(7)
    out = {}
    for rh_name, rh in (cases or RH_CASES):
        cov, fp = {}, {}
        for ctx in CONTEXTS:
            p_pas = {loc: passive_detect_person(loc, rh, ctx, front, rng, v0=v0)[0] for loc in LOCS}
            cov[ctx] = {}
            for loc in LOCS:
                a = ACTIVE_CATCH[loc]
                cov[ctx][loc] = {"A": a, "B": 1 - (1 - a) * (1 - p_pas[loc]),
                                 "C": 1 - (1 - a) * (1 - p_pas[loc] * imu_attack)}
            # mean passive step probability for harmless person contacts (mix of locations)
            p_person = float(np.mean([p_pas[l] for l in ("shoulder", "other_arm", "forearm")]))
            p_obj = passive_detect_object(rh, ctx, front, rng, v0=v0)
            extra = PERSON_CONTACTS[ctx] * p_person + OBJECT_CONTACTS[ctx] * p_obj
            fp[ctx] = {"A": ACTIVE_PROMPTS[ctx], "B": ACTIVE_PROMPTS[ctx] + extra,
                       "C": ACTIVE_PROMPTS[ctx] + extra * CONTEXTS[ctx]["imu_fp"],
                       "passive_person": PERSON_CONTACTS[ctx] * p_person, "passive_object": OBJECT_CONTACTS[ctx] * p_obj}
        out[rh_name] = {"coverage": cov, "prompts_per_hour": fp}
    return out


def body_avg(cov, rule):
    """Mean over the three contexts and the seven locations: share of grabs caught."""
    return float(np.mean([cov[c][l][rule] for c in cov for l in LOCS]))


V0_GRID = np.logspace(-1, 4, 26)        # typical body voltage magnitude at contact, V


def sweep_v0(front, imu_attack=0.7):
    rows = []
    for v0 in V0_GRID:
        r = run(front, imu_attack, v0=float(v0), cases=[("v0", 50)])["v0"]
        rows.append({"v0": float(v0),
                     **{f"cov_{k}": 100 * body_avg(r["coverage"], k) for k in "ABC"},
                     **{f"fp_{k}": float(np.mean([r["prompts_per_hour"][c][k] for c in CONTEXTS])) for k in "ABC"},
                     "passive_shoulder": 100 * float(np.mean([r["coverage"][c]["shoulder"]["B"] for c in CONTEXTS]))})
    return rows


def figures(sw_imp, sw_cur):
    v = [r["v0"] for r in sw_imp]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.4))
    # left: coverage vs typical body voltage
    for rows, ls, lab in ((sw_imp, "-", "improved input + ADS1115"), (sw_cur, ":", "current front end, ESP32 ADC")):
        a1.plot(v, [r["cov_B"] for r in rows], ls, color=ps.SERIES[1], label=f"B · + passive step ({lab})")
        a1.plot(v, [r["cov_C"] for r in rows], ls, color=ps.SERIES[2], label=f"C · + passive step and motion ({lab})")
    a1.plot(v, [r["cov_A"] for r in sw_imp], "-", color=ps.SERIES[0], label="A · active sweep only (today)")
    a1.axvspan(250, 12000, color=ps.GRID, alpha=0.8, lw=0)
    a1.text(1700, 6, "walking on vinyl,\ninsulating shoes:\n250 V – 12 kV\n(Desco table)", ha="center", fontsize=8.5, color=ps.INK2)
    a1.text(20, 30, "roads, tiles, bus floors:\nno published value", fontsize=8.5, color=ps.CRITICAL, ha="center", va="top")
    a1.set_xscale("log")
    a1.set_xlim(0.1, 1e4)
    a1.set_ylim(0, 100)
    a1.set_xlabel("Typical body voltage of each person at the moment of contact (V)")
    a1.set_ylabel("Grabs caught, averaged over 7 body locations (%)")
    a1.set_title("Coverage depends on one unmeasured number", pad=22)
    ps.subtitle(a1, "Charge sharing at contact; watch sees 6 % (current) or 30 % (improved) of her jump")
    a1.legend(loc="center left", fontsize=8)
    # right: unwanted prompts vs body voltage
    for rows, ls in ((sw_imp, "-"), (sw_cur, ":")):
        a2.plot(v, [r["fp_B"] for r in rows], ls, color=ps.SERIES[1])
        a2.plot(v, [r["fp_C"] for r in rows], ls, color=ps.SERIES[2])
    a2.plot(v, [r["fp_A"] for r in sw_imp], "-", color=ps.SERIES[0])
    a2.axhline(1 / 24 * 16, color=ps.MUTED, ls="--", lw=1.1)
    a2.text(0.13, 1 / 24 * 16 + 0.3, "≈ 1 false alarm per 16-hour day (stated budget for wrist detectors)", fontsize=8.5, color=ps.INK2)
    a2.axvspan(250, 12000, color=ps.GRID, alpha=0.8, lw=0)
    a2.set_xscale("log")
    a2.set_xlim(0.1, 1e4)
    a2.set_ylim(0, None)
    a2.set_xlabel("Typical body voltage of each person at the moment of contact (V)")
    a2.set_ylabel("Unwanted PIN prompts per hour (walking, bus, desk average)")
    a2.set_title("…and so does the false-prompt cost", pad=22)
    ps.subtitle(a2, "B prompts on every harmless brush and railing; C needs motion to confirm")
    fig.tight_layout()
    ps.save(fig, "figures/fig15_fusion_voltage.png")

    # fig 16: where on the body, at a modest 10 V and at the vinyl-humid 250 V
    rules = [("A", "A · active only", ps.SERIES[0]), ("B", "B · + passive step", ps.SERIES[1]),
             ("C", "C · + passive step and motion", ps.SERIES[2])]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.0), sharey=True)
    y = np.arange(len(LOCS))
    for ax, (title, v0) in zip(axes, (("Bodies at ~1 V", 1.0), ("Bodies at ~10 V", 10.0), ("Bodies at ~250 V (humid vinyl)", 250.0))):
        cov = run("improved", v0=v0, cases=[("v0", 50)])["v0"]["coverage"]
        for j, (r, lab, col) in enumerate(rules):
            ax.barh(y + (j - 1) * 0.27, [100 * np.mean([cov[c][l][r] for c in cov]) for l in LOCS], height=0.25, color=col, label=lab)
        ax.set_yticks(y)
        ax.set_yticklabels([LOC_LABEL[l] for l in LOCS])
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("Grabs caught (%)")
        ax.set_title(title, pad=8)
        ax.grid(axis="y", visible=False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", ncol=3, fontsize=9, bbox_to_anchor=(0.99, 0.995))
    fig.suptitle("Where on her body a grab is caught\n(improved input + ADS1115; motion confirms 70 % of grabs [E])",
                 x=0.01, ha="left", fontsize=12.5, fontweight="bold", color=ps.INK)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    ps.save(fig, "figures/fig16_fusion_locations.png")


def breakeven(rows, key, target):
    for r in rows:
        if r[key] >= target:
            return round(r["v0"], 2)
    return None


def main():
    sw_imp, sw_cur = sweep_v0("improved"), sweep_v0("current")
    vinyl = {name: run("improved")[name] for name, _ in RH_CASES}
    out = {
        "breakeven_v0_for_half_of_shoulder_grabs_V": {"improved": breakeven(sw_imp, "passive_shoulder", 50),
                                                       "current": breakeven(sw_cur, "passive_shoulder", 50)},
        "breakeven_v0_for_90pct_of_shoulder_grabs_V": {"improved": breakeven(sw_imp, "passive_shoulder", 90),
                                                        "current": breakeven(sw_cur, "passive_shoulder", 90)},
        "at_selected_v0_improved": {f"{r['v0']:.3g} V": {k: round(r[k], 1) for k in r if k != "v0"}
                                    for r in sw_imp if round(np.log10(r["v0"]) * 5) % 5 == 0},
        "vinyl_upper_case_improved": {rh: {k: {"coverage_pct": round(100 * body_avg(vinyl[rh]["coverage"], k), 1),
                                               "prompts_per_hour": round(float(np.mean([vinyl[rh]["prompts_per_hour"][c][k] for c in CONTEXTS])), 2)}
                                           for k in "ABC"} for rh, _ in RH_CASES},
        "rule_C_coverage_vs_motion_confirm_at_10V": {f"{p:.0%}": round(100 * body_avg(run("improved", p, v0=10.0, cases=[("v0", 50)])["v0"]["coverage"], "C"), 1)
                                                     for p in (0.5, 0.7, 0.9)},
        "sweep_improved": sw_imp, "sweep_current": sw_cur,
    }
    json.dump(out, open("data/fusion_results.json", "w"), indent=1)
    figures(sw_imp, sw_cur)
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("sweep")}, indent=1))


if __name__ == "__main__":
    main()
