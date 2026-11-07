"""Second-ground study (figures 20-21): can a second, separately grounded node on her body see a
touch ANYWHERE, whatever the static charge on either person?

Idea (from the whole-body research, docs/technical/second_ground.md): the watch sends a small
200 kHz signal into her skin through E1, as it already does for the sweep. A second receiver with
its OWN battery and floating ground (in the strap clasp under the wrist, or a pendant / anklet)
measures her body against that ground. A second person touching her anywhere roughly doubles her
body's capacitance to the surroundings, which changes how her body moves against the earth, and so
what the second node sees. A receiver that shares the watch's ground cannot see this.

The published two-node body-channel models (Maity et al. 2018, Das et al. 2020) leave out one
thing that decides the answer here: the direct capacitance between the two grounds, C_K0. The
watch drives her body hard against its own ground, so even a small C_K0 adds a large, constant
signal that dilutes the touch change, and any wobble in C_K0 (the strap flexing, her arm moving
against a pendant) looks like a touch. This study adds node K (the second ground) and R (its skin
electrode) to the model's nodal network and sweeps C_K0.

Nodes (voltages against the watch ground "0"): S tank/E1, B her body, A the other person,
E the earth/surroundings, K the second node's ground, R the second node's skin electrode.

Run:  python simulation/second_ground.py
"""
import json

import matplotlib.pyplot as plt
import numpy as np

import plotstyle as ps
import sg_model as m
from paths import DATA, FIGURES

ps.apply()
pF = 1e-12
F_TX = 200e3                       # transmit tone, inside the MAX30009 / AD5940 range
m.FREQS = np.array([F_TX])          # every branch admittance below is at this one frequency
DESIGN = "dual_shield"
ENVS = ("street_shoes", "sandals", "barefoot_tile")

# Where the second node sits. C_KE: its own return path to the surroundings (free-space
# self-capacitance 8*eps0*a times the on-body factor, as the watch's [S11, G]; a ~1-1.5 cm module
# on the wrist underside -> ~0.15-0.8 pF; a pendant hangs further from the body; an anklet is close
# to the floor). C_K0: its direct coupling to the watch ground. [E] estimates, to be measured at Gate 1.
PLACES = {
    "clasp":     dict(label="Clasp, E2 kept 15 mm clear", cke=(0.15, 0.8), ck0=(0.05, 0.5), flex=0.03),
    "clasp_e2":  dict(label="Clasp, E2 runs up to it", cke=(0.15, 0.8), ck0=(0.5, 3.0), flex=0.05),
    "pendant":   dict(label="Pendant at the collarbone", cke=(0.3, 1.5), ck0=(0.005, 0.05), flex=0.5),
    "anklet":    dict(label="Anklet", cke=(1.0, 5.0), ck0=(0.001, 0.01), flex=0.5),
}
EVENTS = [  # (key, label, kind, detail)
    ("shoulder", "Stranger: shoulder", "other_person", "shoulder"),
    ("waist", "Stranger: waist", "other_person", "waist"),
    ("hair", "Stranger: face / hair", "other_person", "face_hair"),
    ("other_arm", "Stranger: other arm", "other_person", "other_arm"),
    ("wrist", "Stranger: wrist", "other_person", "wrist"),
    ("railing", "Holds an earthed railing", "object", "railing_hand"),
    ("sit", "Sits down", None, "sit"),
    ("phone", "Picks up a phone", "object", "phone"),
    ("bystander", "Person 30 cm away, no touch", "no_contact", "bystander"),
    ("wall", "Walks past a wall / car", None, "wall"),
    ("flex", "Strap flex / arm swing", None, "flex"),
]
TOUCH_KEYS = ("shoulder", "waist", "hair", "other_arm", "wrist")


def node_branches(p, s, place, cfg):
    """Second-node branches for each sample."""
    br = {}
    h, a = m._skin(s)
    br["Y_BR"] = 1.0 / m.z_electrode(s.u(1.0, 2.0), h, a, s.u(0.5, 0.6))       # 1-2 cm^2 steel pad
    br["Y_RK"] = 1.0 / 1e6 + m.yc(np.full(s.n, 10 * pF))                       # receiver input, 1 MOhm || 10 pF
    br["Y_BK"] = m.yc(m.plate(s.u(2.0, 3.0), s.u(2, 4) * m.CM2, s.u(1.5e-3, 3e-3)))  # its board over her skin [G]
    br["C_KE"] = s.lu(*cfg["cke"]) * pF
    br["Y_KE"] = m.yc(br["C_KE"])
    if place == "shared":                       # receiver on the watch's own ground
        br["Y_K0"] = np.full_like(br["Y_KE"], 1.0)
    else:
        br["Y_K0"] = m.yc(s.lu(*cfg["ck0"]) * pF)
    return br


def solve6(br):
    """Nodal analysis with the second node. Returns (V_R - V_K, V_S), each (n,)."""
    n = br["Y_SB"].shape[0]
    S, B, A, E, K, R = range(6)
    Y = np.zeros((n, 6, 6), dtype=complex)
    g = lambda k: br[k][:, 0]   # noqa: E731  (single frequency)

    def link(i, j, y):
        Y[:, i, i] += y
        Y[:, j, j] += y
        Y[:, i, j] -= y
        Y[:, j, i] -= y

    def to0(i, y):
        Y[:, i, i] += y

    to0(S, g("Ysrc") + g("Y_S0"))
    link(S, B, g("Y_SB"))
    to0(B, g("Y_B0"))
    link(B, E, g("Y_BE"))
    link(B, A, g("Y_BA"))
    link(A, E, g("Y_AE"))
    to0(A, g("Y_A0"))
    to0(E, g("Y_0E"))
    link(B, R, g("Y_BR"))
    link(R, K, g("Y_RK"))
    link(B, K, g("Y_BK"))
    link(K, E, g("Y_KE"))
    to0(K, g("Y_K0"))
    link(A, K, g("Y_KA"))
    I = np.zeros((n, 6), dtype=complex)
    I[:, S] = g("Ysrc")                         # 1 V at the source
    V = np.linalg.solve(Y, I[..., None])[..., 0]
    return V[:, R] - V[:, K], V[:, S]


def run(place, n=1500, seed=7):
    """Per event: % change of the second node's reading and of the watch's own reading."""
    cfg = PLACES.get(place, PLACES["clasp"])
    out = {}
    for key, _lab, kind, detail in EVENTS:
        rx, wa = [], []
        for ei, env in enumerate(ENVS):
            rng = np.random.default_rng(seed + 100 * ei + hash(key) % 97)
            s = m.Sampler(rng, n)
            p = m.sample_base(s, DESIGN, env)
            base = m.base_branches(p)
            nb = node_branches(p, s, place, cfg)
            base.update(nb)
            base["Y_KA"] = np.zeros_like(base["Y_KE"])
            if kind is None:
                evt = {k: v.copy() for k, v in base.items()}
                if detail == "sit":                      # chair / bench: more of her close to the floor [E]
                    evt["Y_BE"] = base["Y_BE"] * s.u(1.2, 1.8)[:, None]
                elif detail == "wall":                   # surroundings +10 % for every return path [E]
                    evt["Y_0E"] = base["Y_0E"] * 1.10
                    evt["Y_KE"] = base["Y_KE"] * 1.10
                    evt["Y_BE"] = base["Y_BE"] * 1.03
                elif detail == "flex":                   # second node moves against the watch [E]
                    f = cfg["flex"]
                    evt["Y_K0"] = base["Y_K0"] * (1 + s.u(-f, f))[:, None] if place != "shared" else base["Y_K0"]
                    evt["Y_BK"] = base["Y_BK"] * (1 + s.u(-0.10, 0.10))[:, None]
            else:
                s2 = m.Sampler(np.random.default_rng(seed + 7 + 100 * ei + hash(key) % 89), n)
                ev = m.event_branches(p, s2, DESIGN, kind, detail)
                evt = dict(base)
                for k in ("Y_BA", "Y_A0", "Y_BE", "Y_0E"):
                    evt[k] = ev[k]
                # the other person couples to the second node in proportion to its return path
                ratio = (nb["C_KE"] / p["C_GE_free"])[:, None]
                evt["Y_KA"] = ev["Y_A0"] * ratio
            r0, w0 = solve6(base)
            r1, w1 = solve6(evt)
            rx.append(100 * (np.abs(r1) - np.abs(r0)) / np.abs(r0))
            wa.append(100 * (np.abs(w1) - np.abs(w0)) / np.abs(w0))
        out[key] = (np.concatenate(rx), np.concatenate(wa))
    return out


def summary(vals):
    a = np.abs(vals)
    return {"median_pct": round(float(np.median(vals)), 3), "median_abs_pct": round(float(np.median(a)), 3), "p10_abs_pct": round(float(np.percentile(a, 10)), 3),
            "p90_abs_pct": round(float(np.percentile(a, 90)), 3)}


def fig20(results):
    places = ["shared", "clasp", "clasp_e2", "pendant"]
    labels = {"shared": "Receiver on the watch's own ground", **{k: v["label"] for k, v in PLACES.items()}}
    fig, axes = plt.subplots(1, len(places), figsize=(15, 6.2), sharey=True)
    ylab = [lab for _k, lab, _a, _b in EVENTS]
    for ax, pl in zip(axes, places):
        res = results[pl]
        for i, (key, _lab, _k, _d) in enumerate(EVENTS):
            v = np.abs(res[key][0])
            lo, md, hi = np.percentile(v, [10, 50, 90])
            col = ps.SERIES[2] if key in TOUCH_KEYS else (ps.SERIES[1] if key in ("railing", "sit", "phone") else ps.MUTED)
            ax.plot([max(lo, 1e-4), hi], [i, i], color=col, lw=5, alpha=0.45, solid_capstyle="round")
            ax.plot([max(md, 1e-4)], [i], "o", color=col, ms=6)
        ax.axvline(0.1, color=ps.CRITICAL, ls="--", lw=1)
        ax.set_xscale("log")
        ax.set_xlim(1e-4, 100)
        ax.set_title(labels[pl], fontsize=10)
        ax.set_yticks(range(len(EVENTS)))
        ax.set_yticklabels(ylab, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Change in the second node's reading (%)")
    axes[0].text(0.11, len(EVENTS) - 0.6, "0.1 %: sweep noise level", color=ps.CRITICAL, fontsize=8)
    fig.suptitle("A second, separate ground sees a touch anywhere, but railings, sitting and its own wobble do too", y=0.99)
    ps.footnote(fig, "Bars: 10–90 % of 4,500 simulated cases (street shoes, sandals, barefoot); dot: median. Green: another "
                "person touching her; orange: everyday look-alikes; grey: drift. 200 kHz tone from E1. C_K0 and C_KE are "
                "estimates [E] until Gate 1 measures them.")
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    ps.save(fig, FIGURES / "fig20_second_ground.png")


def fig21():
    """Typical person, shoulder touch vs everyday wobble, as the direct coupling C_K0 grows."""
    ck0 = np.logspace(-3.3, 0.6, 120)
    cfg = PLACES["clasp"]
    touch, flex3, flex50 = [], [], []
    for c in ck0:
        s = m.Sampler(None, 1)
        p = m.sample_base(s, DESIGN, "street_shoes")
        base = m.base_branches(p)
        nb = node_branches(p, s, "clasp", cfg)
        nb["Y_K0"] = m.yc(np.array([c * pF]))
        base.update(nb)
        base["Y_KA"] = np.zeros_like(base["Y_KE"])
        r0, _ = solve6(base)
        ev = m.event_branches(p, m.Sampler(None, 1), DESIGN, "other_person", "shoulder")
        e = dict(base)
        for k in ("Y_BA", "Y_A0"):
            e[k] = ev[k]
        e["Y_KA"] = ev["Y_A0"] * (nb["C_KE"] / p["C_GE_free"])[:, None]
        r1, _ = solve6(e)
        touch.append(abs(100 * (abs(r1[0]) - abs(r0[0])) / abs(r0[0])))
        for frac, lst in ((0.03, flex3), (0.5, flex50)):
            f = dict(base)
            f["Y_K0"] = base["Y_K0"] * (1 + frac)
            r2, _ = solve6(f)
            lst.append(abs(100 * (abs(r2[0]) - abs(r0[0])) / abs(r0[0])))
    touch, flex3, flex50 = map(np.array, (touch, flex3, flex50))
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.plot(ck0, touch, color=ps.SERIES[2], lw=2.4, label="Stranger touches her shoulder")
    ax.plot(ck0, flex3, color=ps.SERIES[1], lw=1.8, ls="--", label="Coupling wobbles 3 % (rigid clasp)")
    ax.plot(ck0, flex50, color=ps.MUTED, lw=1.8, ls=":", label="Coupling wobbles 50 % (pendant, arm swinging)")
    ax.axhline(0.1, color=ps.CRITICAL, lw=1, ls="--")
    ax.text(0.0006, 0.115, "0.1 %: sweep noise level", fontsize=8.5, color=ps.CRITICAL)
    for lo, hi, name in ((0.005, 0.05, "pendant"), (0.05, 0.5, "clasp, E2 clear"), (0.5, 3.0, "clasp, E2 close")):
        ax.axvspan(lo, hi, color=ps.GRID, alpha=0.55 if name != "clasp, E2 clear" else 0.9, lw=0)
        ax.text(np.sqrt(lo * hi), 55, name, ha="center", fontsize=8.5, color=ps.INK2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.01, 100)
    ax.set_xlabel("Direct coupling between the watch ground and the second node's ground, C_K0 (pF)")
    ax.set_ylabel("Change in the second node's reading (%)")
    ax.set_title("The two grounds must barely see each other, and must hold still", pad=22)
    ps.subtitle(ax, "Typical person in street shoes; the touch must stand well above the wobble of C_K0")
    ax.legend(loc="lower left")
    fig.tight_layout()
    ps.save(fig, FIGURES / "fig21_second_ground_coupling.png")
    # where the touch is 3x the 3 % wobble
    ok = ck0[touch > 3 * flex3]
    return {"ck0_pF": [round(float(x), 4) for x in ck0[::12]], "touch_pct": [round(float(x), 3) for x in touch[::12]],
            "flex3_pct": [round(float(x), 4) for x in flex3[::12]], "flex50_pct": [round(float(x), 4) for x in flex50[::12]],
            "max_ck0_touch_3x_rigid_wobble_pF": round(float(ok.max()), 3) if ok.size else None}


def separable(res):
    """Share of events whose change is more than twice the 95th percentile of the everyday drift,
    judged two ways: while she stands still (surroundings change, someone passes close) and while
    she moves (the second node wobbles against the watch as well)."""
    still = np.concatenate([np.abs(res[k][0]) for k in ("wall", "bystander")])
    moving = np.concatenate([still, np.abs(res["flex"][0])])
    out = {}
    for name, d in (("still", still), ("moving", moving)):
        thr = max(2 * np.percentile(d, 95), 0.2)
        out[name] = {"threshold_pct": round(float(thr), 3),
                     "share": {k: round(float(np.mean(np.abs(res[k][0]) > thr)), 3) for k in TOUCH_KEYS + ("railing", "sit", "phone")}}
    return out


def main():
    results = {pl: run(pl) for pl in ["shared", "clasp", "clasp_e2", "pendant", "anklet"]}
    fig20(results)
    curve = fig21()
    out = {"tone_Hz": F_TX, "places": {}, "coupling_curve": curve}
    for pl, res in results.items():
        out["places"][pl] = {"label": PLACES[pl]["label"] if pl in PLACES else "Receiver on the watch's own ground",
                             "events": {k: summary(res[k][0]) for k, *_ in EVENTS},
                             "watch_alone": {k: summary(res[k][1]) for k, *_ in EVENTS},
                             "detect": separable(res)}
    (DATA / "second_ground_results.json").write_text(json.dumps(out, indent=1))
    for pl, d in out["places"].items():
        st, mv = d["detect"]["still"], d["detect"]["moving"]
        print(f"\n{d['label']}  (threshold still {st['threshold_pct']} %, moving {mv['threshold_pct']} %)")
        for k, *_ in EVENTS:
            e = d["events"][k]
            print(f"  {k:<10} median {e['median_pct']:>8} %  |10-90| {e['p10_abs_pct']:>7} – {e['p90_abs_pct']:<7}"
                  f"  caught still {st['share'].get(k, ''):<6} moving {mv['share'].get(k, '')}")
    print("\nmax C_K0 for touch > 3x rigid wobble:", curve["max_ck0_touch_3x_rigid_wobble_pF"], "pF")
    print("watch alone, shoulder:", out["places"]["clasp"]["watch_alone"]["shoulder"])


if __name__ == "__main__":
    main()
