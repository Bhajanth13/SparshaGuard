"""Physics figures for the SparshaGuard simulation study.

Run:  python make_figures.py      (writes figures/*.png and data/summary_stats.json)
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import schemdraw
import schemdraw.elements as elm

import plotstyle as ps
import sg_model as m

ps.apply()
RNG = np.random.default_rng(2026)
N_PER_ENV = 800
NOISE = 1e-3          # ESP32 ADC noise after ~16 averaged sweeps, fraction of full scale [S15]
NOISE_DA = float(np.hypot(NOISE, NOISE / 2))   # resulting per-point amplitude-change noise
OUT = "figures"
stats = {}


def pooled_scores(design, kind, detail=None, envs=m.ENVS, grounded=False, strong=False, noise=NOISE):
    sc = []
    for env in envs:
        vb, ve = m.simulate_pair(design, env, kind, detail, n=N_PER_ENV, rng=RNG,
                                 grounded_bench=grounded, strong_drift=strong)
        vb = m.add_noise(vb, noise / 2, RNG)   # baseline is averaged longer
        ve = m.add_noise(ve, noise, RNG)
        sc.append(m.change_score(vb, ve))
    return 100 * np.concatenate(sc)           # percent


def q(x):
    return np.percentile(x, [10, 50, 90])


# ------------------------------------------------------------- Fig 0: schematic
def fig_schematic():
    with schemdraw.Drawing(show=False) as d:
        d.config(fontsize=10.5, unit=2, color=ps.INK)
        elm.SourceSin().at((0, 0)).to((0, 3)).label("Vs\nsweep\n1 kHz–3.5 MHz", loc="left")
        elm.Resistor().at((0, 3)).to((2, 3)).label("Rs 10 kΩ")
        elm.Inductor2().at((2, 3)).to((4, 3)).label("L 10 mH")
        elm.Dot().at((4, 3)).label("S", loc="top")
        elm.Capacitor().at((4, 3)).to((4, 0)).label("C_tank 100 pF", loc="bottom", ofst=(0.15, 0))
        elm.RBox().at((4, 3)).to((6.6, 3)).label("electrode–\nskin (CPE)")
        elm.Resistor().at((6.6, 3)).to((8.6, 3)).label("R_body")
        elm.Dot().at((8.6, 3))
        elm.Label().at((9.75, 2.15)).label("B  her body")
        elm.Capacitor().at((8.6, 3)).to((8.6, 0)).label("C_GB", loc="bottom")
        elm.Capacitor().at((8.6, 3)).to((8.6, 6)).label("C_BE", loc="bottom")
        elm.RBox().at((8.6, 3)).to((12, 3)).label("Z_BA  touch /\ncloth / proximity").color(ps.SERIES[1])
        elm.Dot().at((12, 3))
        elm.Label().at((13.4, 3.45)).label("A  other person")
        elm.Capacitor().at((12, 3)).to((12, 6)).label("C_AE", loc="bottom")
        elm.RBox().at((12, 3)).to((12, 0)).label("Z_A0  his hand on\nouter electrode", loc="bottom").color(ps.SERIES[1])
        elm.Capacitor().at((16.6, 6)).to((16.6, 0)).label("C_GE", loc="bottom")
        elm.Line().at((0, 0)).to((16.6, 0)).color(ps.SERIES[0])
        elm.Line().at((8.6, 6)).to((16.6, 6)).color(ps.SERIES[2])
        elm.Ground().at((2, 0)).color(ps.SERIES[0])
        elm.Label().at((8.3, -0.75)).label("0 = watch ground (floats on battery)", color=ps.SERIES[0])
        elm.Label().at((12.6, 6.45)).label("E = surroundings / earth", color=ps.SERIES[2])
        elm.Label().at((4, 4.4)).label("measured: |V_S(f)|", color=ps.INK2)
        d.save(f"{OUT}/fig0_equivalent_circuit.png", dpi=200)


# ------------------------------------------------------- Fig 1: sweep curves
def fig_sweeps():
    m.set_sweep(400, 1e3, 3.5e6, "log")
    f = m.FREQS / 1e3
    design, env = "dual_shield", "street_shoes"
    vb, _ = m.simulate_pair(design, env, "no_contact")
    curves = [("No contact (baseline)", vb, ps.INK2, "-")]
    for lab, kind, det, col in [("Wrist grab by another person", "other_person", "wrist", ps.SERIES[1]),
                                ("Her own hand on the strap", "self", None, ps.SERIES[2]),
                                ("Strap pressed on a metal pole", "object", "railing_wrist", ps.SERIES[6])]:
        _, ve = m.simulate_pair(design, env, kind, det)
        curves.append((lab, ve, col, "-"))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    ax = axes[0]
    for lab, v, col, ls in curves:
        ax.plot(f, np.abs(v)[0], color=col, ls=ls, label=lab)
    ax.set_xscale("log")
    ax.set_xlabel("Sweep frequency (kHz)")
    ax.set_ylabel("Sense-node amplitude  |V_S / Vs|")
    ax.set_title("What the watch measures: the capacitive profile", pad=22)
    ps.subtitle(ax, "Typical wearer in street shoes, inner + outer electrode with driven shield")
    ax.legend(loc="upper left")

    ax = axes[1]
    for lab, kind, det, col in [("Wrist grab", "other_person", "wrist", ps.SERIES[1]),
                                ("Forearm grab", "other_person", "forearm", ps.SERIES[3]),
                                ("Shoulder grab", "other_person", "shoulder", ps.SERIES[0]),
                                ("Bystander very close, no touch", "no_contact", "bystander", ps.SERIES[4])]:
        b, e = m.simulate_pair(design, env, kind, det)
        ax.plot(f, 100 * np.abs(np.abs(e) - np.abs(b))[0], color=col, label=lab)
    ax.axhline(100 * NOISE_DA, color=ps.MUTED, ls="--", lw=1.4)
    ax.text(f[3], 100 * NOISE_DA * 1.15, "measurement noise (16 averaged sweeps)", color=ps.MUTED, fontsize=8.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 150)
    ax.set_xlabel("Sweep frequency (kHz)")
    ax.set_ylabel("Amplitude change (% of full scale)")
    ax.set_title("How big the change is, by where she is grabbed", pad=22)
    ps.subtitle(ax, "Same wearer; only the touch changes")
    ax.legend(loc="lower left")
    fig.tight_layout()
    ps.save(fig, f"{OUT}/fig1_sweep_profiles.png")
    m.set_sweep()


# ------------------------------------------- Fig 2: signal vs grab location
def dotplot(ax, rows, series, xlabel):
    """rows: list of row labels; series: list of (label, color, {row: samples})."""
    k = len(series)
    offs = np.linspace(-0.22, 0.22, k) if k > 1 else [0]
    for (lab, col, data), off in zip(series, offs):
        for i, r in enumerate(rows):
            if r not in data:
                continue
            p10, p50, p90 = q(data[r])
            y = i + off
            ax.plot([p10, p90], [y, y], color=col, lw=2.2, alpha=0.55, solid_capstyle="round")
            ax.plot(p50, y, "o", ms=8, color=col, mec=ps.SURFACE, mew=1.5,
                    label=lab if i == 0 else None)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", visible=False)


def fig_location():
    rows = ["No touch: sweat + strap drift", "Bystander very close, no touch"] + \
           [ps.LOC_LABEL[l] for l in m.LOCATIONS]
    series = []
    stats["location"] = {}
    for d in m.DESIGNS:
        data = {rows[0]: pooled_scores(d, "no_contact"),
                rows[1]: pooled_scores(d, "no_contact", "bystander")}
        for l in m.LOCATIONS:
            data[ps.LOC_LABEL[l]] = pooled_scores(d, "other_person", l)
        series.append((ps.DESIGN_LABEL[d], ps.DESIGN_COLOR[d], data))
        stats["location"][d] = {r: [round(float(v), 4) for v in q(x)] for r, x in data.items()}

    fig, ax = plt.subplots(figsize=(11, 6.2))
    dotplot(ax, rows, series, "Amplitude change across the sweep (% of full scale, RMS, log scale)")
    ax.axhspan(-0.5, 1.5, color=ps.GRID, alpha=0.45, zorder=0)
    ax.text(0.995, 0.5, "nuisance\n(must NOT trigger)", transform=ax.get_yaxis_transform(),
            ha="right", va="center", fontsize=8.5, color=ps.INK2)
    ax.set_title("Grabs at the wrist stand out; grabs elsewhere, even on the forearm, are lost in the noise", pad=22)
    ps.subtitle(ax, "Dot = median, bar = 10th–90th percentile over 3,200 simulated wearers per row "
                    "(4 footwear/seating conditions). Further right = easier to detect.")
    ax.legend(loc="lower right", title="Watch design", title_fontsize=9.5)
    ps.footnote(fig, "SparshaGuard simulation v0.3 — parameters from published measurements where available (docs/parameter_sources.md); calibrate with Gate 1.")
    fig.tight_layout()
    ps.save(fig, f"{OUT}/fig2_signal_by_location.png")


# --------------------------------------------- Fig 3: footwear / environment
def fig_environment():
    d = "dual_shield"
    rows = [ps.ENV_LABEL[e] for e in m.ENVS]
    series = []
    stats["environment"] = {}
    for lab, kind, det, col in [("Wrist grab", "other_person", "wrist", ps.SERIES[1]),
                                ("Shoulder grab", "other_person", "shoulder", ps.SERIES[0]),
                                ("No touch (drift only)", "no_contact", None, ps.MUTED)]:
        data = {ps.ENV_LABEL[e]: pooled_scores(d, kind, det, envs=[e]) for e in m.ENVS}
        series.append((lab, col, data))
        stats["environment"][lab] = {r: [round(float(v), 4) for v in q(x)] for r, x in data.items()}
    fig, ax = plt.subplots(figsize=(10, 4.2))
    dotplot(ax, rows, series, "Amplitude change across the sweep (% of full scale, RMS, log scale)")
    ax.set_title("Shoes don't break it: the wrist-grab signal barely moves with footwear", pad=22)
    ps.subtitle(ax, "Inner + outer electrode with driven shield; 800 simulated wearers per row")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    ps.save(fig, f"{OUT}/fig3_footwear_environment.png")


# ---------------------------------------------- Fig 4: bench vs battery
def fig_bench():
    rows = [ps.DESIGN_LABEL[d] for d in m.DESIGNS]
    series = []
    stats["bench_vs_battery_shoulder"] = {}
    for lab, grounded, col in [("Battery-powered (real use)", False, ps.SERIES[0]),
                               ("USB to a charging laptop (bench test)", True, ps.SERIES[7])]:
        data = {ps.DESIGN_LABEL[d]: pooled_scores(d, "other_person", "shoulder", grounded=grounded)
                for d in m.DESIGNS}
        series.append((lab, col, data))
        stats["bench_vs_battery_shoulder"][lab] = {r: [round(float(v), 4) for v in q(x)] for r, x in data.items()}
    fig, ax = plt.subplots(figsize=(10, 3.6))
    dotplot(ax, rows, series, "Shoulder-grab amplitude change (% of full scale, RMS, log scale)")
    ax.set_title("Why bench demos mislead: an earthed circuit sees a shoulder grab easily", pad=22)
    ps.subtitle(ax, "Same shoulder grab. Earthing the watch ground (laptop on charger) makes it look detectable.")
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    ps.save(fig, f"{OUT}/fig4_bench_vs_battery.png")


if __name__ == "__main__":
    fig_schematic()
    fig_sweeps()
    fig_location()
    fig_environment()
    fig_bench()
    with open("data/summary_stats.json", "w") as fh:
        json.dump({"units": "percent RMS change, [p10, p50, p90]", **stats}, fh, indent=1)
    print("figures written")
