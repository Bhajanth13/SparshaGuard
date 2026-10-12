"""Whole-body touch detection study (figures 10-12).

fig10  Why the current active method can't see far touches: shoulder grab vs an ordinary change in
       the watch's surroundings, as the front end is improved.
fig11  Passive body-potential channel: size of the voltage step at the wrist when another person
       touches her ANYWHERE, vs the voltage difference between the two bodies.
fig12  Hand-near-strap coupling from the 3D field calculation (fem/hand_near_strap.py).

Run:  python whole_body.py
"""
import json

import matplotlib.pyplot as plt
import numpy as np

import plotstyle as ps
import sg_model as m

ps.apply()
pF = 1e-12
S = m.Sampler(None, 1)


def typ():
    return m.sample_base(S, "dual_shield", "street_shoes")


def score(p, mod):
    vb = m.solve(m.base_branches(p))
    br = m.base_branches(p)
    mod(br, p)
    return 100 * m.change_score(vb, m.solve(br))[0]


def shoulder(br, p):
    br["Y_BA"] = 1 / m.z_cloth(S, np.array([60.0]))
    br["Y_A0"] = m.yc(p["C_GE_free"] * 0.11)


def surroundings(br, p):            # walking past a wall / car: return path +10 %
    br["Y_0E"] = m.yc(p["C_GE"] * 1.10)


def bystander(br, p):
    br["Y_BA"] = m.yc(np.array([30.5 * pF]))
    br["Y_A0"] = m.yc(p["C_GE_free"] * 0.055)


def fig10():
    steps = [("Current design", {}),
             ("Tank 10 pF\n(not 100 pF)", {"Ctank": np.array([14.5 * pF])}),
             ("+ near-ideal shield\n(5% left)", {"Ctank": np.array([14.5 * pF]), "C_GB": np.array([35.4 * pF * 0.05])}),
             ("+ 3x bigger return path\n(best imaginable)", {"Ctank": np.array([14.5 * pF]), "C_GB": np.array([35.4 * pF * 0.05]),
                                                             "C_GE": np.array([3 * pF]), "C_GE_free": np.array([3 * pF])})]
    rows = []
    for name, ov in steps:
        p = typ()
        p.update(ov)
        rows.append((name, score(p, shoulder), score(p, surroundings), score(p, bystander)))
    fig, ax = plt.subplots(figsize=(11, 5.2))
    x = np.arange(len(rows))
    w = 0.26
    series = [("Shoulder grab (real touch)", 1, ps.SERIES[1]),
              ("Walking past a wall: return path +10% (no touch)", 2, ps.MUTED),
              ("Bystander very close (no touch)", 3, ps.SERIES[4])]
    for k, (lab, idx, col) in enumerate(series):
        vals = [r[idx] for r in rows]
        ax.bar(x + (k - 1) * w, vals, w * 0.92, color=col, label=lab)
    ax.axhline(0.112, color=ps.INK2, ls="--", lw=1.2)
    ax.text(-0.45, 0.125, "noise floor (ESP32 ADC)", ha="left", fontsize=8.5, color=ps.INK2)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylabel("Change at the sense node (% of full scale)")
    ax.set_title("The active sweep can't tell a far touch from a change in the surroundings", pad=22)
    ps.subtitle(ax, "Improving the front end makes a shoulder grab visible, but an ordinary change near the watch grows just as fast")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    ps.save(fig, "figures/fig10_active_limit.png")
    return rows


def wrist_step(dv_bodies, c_ge, c_gb, c_in, c_her=140e-12, c_his=140e-12):
    """Voltage step seen between her skin electrode and the watch ground when two bodies at
    different potentials touch (charge sharing), for a floating watch.
    Her body jumps by dv * C_his / (C_her + C_his); the watch ground follows her body through
    C_GB and stays tied to the room through C_GE, so the electrode sees the fraction
    C_GE / (C_GE + C_GB + C_in) of the jump."""
    body_jump = dv_bodies * c_his / (c_her + c_his)
    return body_jump * c_ge / (c_ge + c_gb + c_in)


def fig11():
    dv = np.logspace(-2, 3, 200)
    designs = [("Current watch (shield leaves 35%, 5 pF amplifier input)", 1.1e-12, 12.4e-12, 5e-12, ps.SERIES[0]),
               ("Bootstrapped input + good shield (2 pF left, 0.5 pF input)", 1.1e-12, 2e-12, 0.5e-12, ps.SERIES[2])]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    for lab, cge, cgb, cin, col in designs:
        ax.plot(dv, 1e3 * wrist_step(dv, cge, cgb, cin), color=col, label=lab)
    ax.axhline(21.8, color=ps.CRITICAL, ls="--", lw=1.2)
    ax.text(0.011, 21.8 * 1.15, "ESP32 built-in ADC fluctuation (~21.8 mV)", fontsize=8.5, color=ps.CRITICAL)
    ax.axhline(2.0, color=ps.INK2, ls="--", lw=1.2)
    ax.text(0.011, 2.0 * 1.15, "ADS1115 fluctuation (~2 mV)", fontsize=8.5, color=ps.INK2)
    ax.axvspan(250, 1000, color=ps.GRID, alpha=0.7, lw=0)
    ax.text(480, 0.12, "walking on vinyl:\n250–12,000 V (Desco)", ha="center", fontsize=8.5, color=ps.INK2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.01, 1000)
    ax.set_ylim(0.05, 5e5)
    ax.set_xlabel("Voltage difference between the two bodies at the moment of contact (V)")
    ax.set_ylabel("Step seen at the wrist electrode (mV)")
    ax.set_title("A passive channel sees a touch anywhere on her body, if the two bodies differ by ~1 V", pad=22)
    ps.subtitle(ax, "Charge sharing between two ~140 pF bodies; the floating watch sees a fixed fraction of her body's voltage jump")
    ax.legend(loc="upper left")
    fig.tight_layout()
    ps.save(fig, "figures/fig11_passive_channel.png")
    out = {}
    for lab, cge, cgb, cin, _ in designs:
        out[lab] = {f"{v} V": round(1e3 * float(wrist_step(np.array(v), cge, cgb, cin)), 3) for v in (0.1, 0.5, 1, 10, 100)}
    return out


def fig12():
    r = json.load(open("fem/hand_near_strap_results.json"))
    d = [1, 2, 3, 5, 10]
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for key, lab, col in [("dual", "Outer electrode on strap + case", ps.SERIES[1]),
                          ("single", "Single electrode (case ground plane only)", ps.SERIES[0])]:
        y = [r[key][f"d={x}cm"] for x in d]
        ax.plot(d, y, "-o", color=col, ms=7, mec=ps.SURFACE, mew=1.3, label=lab)
    ax.axhspan(0.5, 3.0, color=ps.GRID, alpha=0.6, lw=0)
    ax.text(9.8, 2.2, "previous estimate (0.5–3 pF)", ha="right", fontsize=8.5, color=ps.INK2)
    ax.set_yscale("log")
    ax.set_xlabel("Gap between his hand and the strap edge (cm)")
    ax.set_ylabel("Extra coupling to the watch (pF)")
    ax.set_title("His hand near the strap: 3D field calculation", pad=22)
    ps.subtitle(ax, "Boundary-element solve: her forearm, the strap electrode and case, and his gripping hand (9 cm wide)")
    ax.legend(loc="lower left")
    fig.tight_layout()
    ps.save(fig, "figures/fig12_hand_near_strap_fem.png")


if __name__ == "__main__":
    rows = fig10()
    steps = fig11()
    fig12()
    json.dump({"active_limit": [{"design": a, "shoulder_pct": b, "surroundings_pct": c, "bystander_pct": d}
                                for a, b, c, d in rows], "passive_step_mV": steps},
              open("data/whole_body_results.json", "w"), indent=1)
    print(json.dumps(steps, indent=1))
    for r_ in rows:
        print(r_)
