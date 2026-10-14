"""Independent check of the Python circuit solver against SPICE (ngspice).

For every design and scenario, this script writes a SPICE netlist of the same circuit,
element by element, using the 'typical' (midpoint) values of sg_model.py, runs ngspice on the
same 200-point Touché sweep, and compares the sense-node voltage with sg_model.solve().

The netlists are built here from the circuit description, not from the Python admittances,
so a wiring or formula mistake on either side shows up as a disagreement.

Skin is a constant-phase element (CPE) in the model (Goyal et al. 2022). SPICE has no CPE, so
each one is replaced by a standard R-C ladder fitted to the exact CPE over 10 Hz - 350 MHz
(Valsa, Dvorak, Friedl, "Network model of the CPE", Int. J. Circuit Theory Appl. 2011).
The ladder's own error is reported separately.

Run:  python ltspice/spice_crosscheck.py      (needs ngspice on the PATH, ~10 s)
Writes ltspice/netlists/*.cir, data/spice_crosscheck.json, figures/fig13_spice_crosscheck.png
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import nnls

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import plotstyle as ps  # noqa: E402
import sg_model as m  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
NET_DIR = os.path.join(os.path.dirname(__file__), "netlists")
EPS0, pF, CM2 = m.EPS0, 1e-12, 1e-4
F = m.FREQS
NOISE_PCT = 0.1                       # ADC noise, % of full scale (as in the model)

# ------------------------------------------------------------- CPE -> R-C ladder
# Admittance of a CPE with Q = 1:  Y = (jw)^a.  Approximated by a parallel conductance plus
# N series R-C branches with time constants spread 6 per decade; branch capacitances fitted by
# non-negative least squares on the relative error. Scaling Q scales every C (R = tau / C).
TAUS = 1 / (2 * np.pi * np.logspace(-1, 10, 67))
_FIT_F = np.logspace(1, np.log10(3.5e8), 600)
_ladders = {}


def ladder(alpha):
    if alpha not in _ladders:
        jw = 1j * 2 * np.pi * _FIT_F
        target = jw ** alpha
        cols = [np.ones_like(jw)] + [jw / (1 + jw * t) for t in TAUS]   # G0, then branches
        A = np.array(cols).T / np.abs(target)[:, None]
        b = target / np.abs(target)
        x, _ = nnls(np.vstack([A.real, A.imag]), np.concatenate([b.real, b.imag]))
        _ladders[alpha] = x
    return _ladders[alpha]


def ladder_admittance(alpha, Q, f):
    x = ladder(alpha)
    jw = 1j * 2 * np.pi * np.asarray(f)
    y = x[0] * np.ones_like(jw)
    for c, t in zip(x[1:], TAUS):
        y = y + jw * c / (1 + jw * t)
    return Q * y


# ------------------------------------------------------------------ netlist writer
class Net:
    def __init__(self, title):
        self.lines = [f"* {title}"]
        self.k = 0

    def _id(self):
        self.k += 1
        return self.k

    def node(self):
        return f"x{self._id()}"

    def R(self, a, b, r, note=""):
        self.lines.append(f"R{self._id()} {a} {b} {r:.6e}" + (f" ; {note}" if note else ""))

    def C(self, a, b, c, note=""):
        self.lines.append(f"C{self._id()} {a} {b} {c:.6e}" + (f" ; {note}" if note else ""))

    def L(self, a, b, l, note=""):
        self.lines.append(f"L{self._id()} {a} {b} {l:.6e}" + (f" ; {note}" if note else ""))

    def cpe(self, a, b, Q, alpha, note=""):
        """CPE  Y = Q (jw)^alpha  between a and b, as a fitted R-C ladder."""
        self.lines.append(f"* CPE Q={Q:.4e} alpha={alpha:.3f} {note}")
        x = ladder(alpha)
        if x[0] > 0:
            self.R(a, b, 1 / (Q * x[0]))
        for c, t in zip(x[1:], TAUS):
            if c * Q > 1e-30:
                mid = self.node()
                self.R(a, mid, t / (Q * c))
                self.C(mid, b, Q * c)

    def sc(self, a, b, area, hyd=0.5, alpha=0.9, note="stratum corneum"):
        """Stratum corneum (Goyal 2022): Rsc || CPE(Csc), per cm^2 values scaled by area."""
        rsc = m._lerp_log(6.4e6, 3.0e6, hyd) / area
        qsc = m._lerp_log(41e-9, 190e-9, hyd) * area
        self.R(a, b, rsc, f"{note}, {area:g} cm^2")
        self.cpe(a, b, qsc, alpha, note)

    def metal(self, a, b, area, hyd=0.5, beta=0.55):
        """Stainless-steel contact CPE (Goyal 2022)."""
        self.cpe(a, b, m._lerp_log(114e-9, 114e-9 * 420 / 267, hyd) * area, beta, "metal contact")

    def text(self):
        return "\n".join(self.lines + [".options rshunt=1e18", ".end", ""])


def plate(er, area_m2, gap_m):
    return EPS0 * er * area_m2 / gap_m


def mid(a, b):
    return 0.5 * (a + b)


def gmean(a, b):
    return np.sqrt(a * b)


# ------------------------------------------------------ the circuit, element by element
def build(design, env, kind, detail, bench=False):
    """Netlist with the midpoint ('typical') values of every range in sg_model.py."""
    n = Net(f"SparshaGuard v0.3 | {design} | {env} | {kind} {detail or ''} | bench={bench}")
    n.lines.append("* nodes: S sense, B her body, A other person, E surroundings, 0 watch ground")
    # drive + Arduino Touché tank [S3] and sense-node parasitics
    n.lines.append("V1 drv 0 AC 1")
    n.R("drv", "n1", 10e3, "Rs")
    n.L("n1", "S", 10e-3, "tank inductor")
    n.C("S", "0", (100 + mid(2.1, 9) + mid(0.6, 0.8) * mid(1, 3)) * pF, "tank C + buffer/trace parasitics")
    # inner electrode: metal contact + stratum corneum + body tissue
    a1, a2 = n.node(), n.node()
    n.metal("S", a1, 3.0)
    n.sc(a1, a2, 3.0)
    n.R(a2, "B", mid(100, 400) + 100, "wrist-to-trunk tissue")
    # watch ground to wrist
    cgb = plate(2.0, 10 * CM2, 3e-3)
    if design != "single":
        cgb += plate(3.0, 25 * CM2, 2.25e-3)
    if design == "dual_shield":
        cgb *= 0.35
    n.C("B", "0", cgb, "watch ground + strap to wrist")
    cbe = {"street_shoes": 140, "sandals": 170, "barefoot_tile": 217.5, "car_seat": 225}[env] * pF
    n.C("B", "E", cbe, "her body to surroundings")
    cge = gmean(0.4, 1.5) * pF if design == "single" else gmean(0.6, 2.0) * pF
    if env == "car_seat":
        cge *= 1.65
    cge_free = cge
    n.C("0", "E", 10e-9 if bench else cge, "watch return path" + (" (USB earthed)" if bench else ""))
    n.C("A", "E", (140 + (85 if env == "car_seat" else 0)) * pF, "his body to surroundings")

    def outer_contact(a, b):          # his/her palm on the outer electrode (or over the case)
        if design == "single":
            n.C(a, b, plate(2.0, 4 * CM2, 4.5e-3), "hand over the case")
        else:
            x = n.node()
            n.sc(a, x, 15.0, note="palm skin")
            n.C(x, b, plate(mid(2.65, 3.15), 15 * CM2, 62.5e-6), "strap coating")

    if kind == "no_contact" and detail == "bystander":
        n.C("B", "A", 30.5 * pF, "body-to-body, bystander")
        n.C("A", "0", cge_free * 0.055, "his body to the watch")
    elif kind == "other_person":
        bare = m.BARE_PROB[detail] >= 0.5
        x = n.node()
        if bare:
            n.sc("B", x, 60.0, note="her skin")
            n.sc(x, "A", 60.0, note="his skin")
        else:
            y = n.node()
            n.sc("B", x, 60.0, note="her skin")
            n.C(x, y, plate(3.15, 60 * CM2, 0.37e-3 * 1.5), "fabric")
            n.sc(y, "A", 60.0, note="his skin")
        if detail == "wrist":
            outer_contact("A", "0")
        elif detail == "forearm":
            n.C("A", "0", m.hand_near_strap_pF(3.0, design) * pF, "his hand 3 cm from the strap (3D solve)")
        else:
            n.C("A", "0", cge_free * 0.11, "his body to the watch")
    elif kind == "self":
        x = n.node()
        outer_contact("0", x)
        n.R(x, "B", 2 * 250, "her two arm segments")
    elif kind == "object":
        if detail in ("railing_hand", "railing_wrist"):
            x = n.node()
            n.sc("B", x, 30.0, note="palm on railing")
            n.metal(x, "E", 30.0)
            if detail == "railing_wrist":
                c = plate(3.0, 2 * CM2, 2.25e-3) if design == "single" else plate(mid(2.65, 3.15), 6 * CM2, 62.5e-6)
                n.C("0", "E", c, "strap on the metal pole")
        elif detail == "phone":
            x = n.node()
            n.sc("B", x, 30.0, note="hand on phone")
            n.C(x, "E", 8 * pF, "phone self-capacitance")
        elif detail == "wood_table":
            n.C("0", "E", 3 * pF, "watch to table")
            n.C("B", "E", 12.5 * pF, "arm to table")
        elif detail == "bag":
            n.C("B", "E", 6 * pF, "bag")
    return n.text()


# ------------------------------------------------------------------------ run SPICE
def run_ngspice(netlist, name):
    os.makedirs(NET_DIR, exist_ok=True)
    path = os.path.join(NET_DIR, name + ".cir")
    with open(path, "w") as fh:
        fh.write(netlist)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.txt")
        ctl = os.path.join(tmp, "run.cir")
        body = netlist.replace(".end\n", "")
        f_lo, f_hi = F[0], F[-1]
        with open(ctl, "w") as fh:
            fh.write(body + f".control\nac lin {len(F)} {f_lo:.6e} {f_hi:.6e}\n"
                     f"wrdata {out} v(S)\n.endc\n.end\n")
        r = subprocess.run(["ngspice", "-b", ctl], capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError(r.stdout + r.stderr)
        d = np.loadtxt(out)
    assert np.allclose(d[:, 0], F, rtol=1e-6), "frequency grid mismatch"
    return d[:, 1] + 1j * d[:, 2]


def python_pair(design, env, kind, detail, bench=False):
    vb, ve = m.simulate_pair(design, env, kind, detail, n=1, rng=None, grounded_bench=bench)
    return vb[0], ve[0]


CASES = [("no_contact", "bystander", "Bystander close"),
         ("other_person", "wrist", "Wrist grab"),
         ("other_person", "forearm", "Forearm grab"),
         ("other_person", "upper_arm", "Upper-arm grab (cloth)"),
         ("other_person", "other_arm", "Other-arm grab"),
         ("other_person", "shoulder", "Shoulder grab (cloth)"),
         ("other_person", "waist", "Waist grab (cloth)"),
         ("other_person", "face_hair", "Face / hair"),
         ("self", None, "Her own hand on watch"),
         ("object", "railing_hand", "Hand on railing"),
         ("object", "railing_wrist", "Strap on metal pole"),
         ("object", "phone", "Holding phone"),
         ("object", "wood_table", "Wrist on table"),
         ("object", "bag", "Bag")]


def main():
    if shutil.which("ngspice") is None:
        sys.exit("ngspice not found: install it (apt install ngspice / brew install ngspice)")
    if os.path.isdir(NET_DIR):
        shutil.rmtree(NET_DIR)

    # 1. the ladder against the exact CPE
    ladder_err = {}
    for alpha in (0.55, 0.9):
        exact = (1j * 2 * np.pi * F) ** alpha
        ladder_err[f"alpha={alpha}"] = float(np.max(np.abs(ladder_admittance(alpha, 1, F) / exact - 1)))

    # 2. every design x scenario (street shoes), plus environments and the USB bench case
    runs = [(d, "street_shoes", k, det, lab, False) for d in m.DESIGNS for k, det, lab in CASES]
    runs += [("dual_shield", env, "other_person", loc, f"{loc.title()} grab, {env}", False)
             for env in m.ENVS[1:] for loc in ("wrist", "shoulder")]
    runs += [("dual_shield", "street_shoes", "other_person", "shoulder", "Shoulder grab, USB bench", True)]

    results, curves, base_cache = [], {}, {}
    for design, env, kind, detail, label, bench in runs:
        key = (design, env, bench)
        tag = f"{design}_{env}" + ("_bench" if bench else "")
        if key not in base_cache:
            sb = run_ngspice(build(design, env, "no_contact", None, bench), f"{tag}__baseline")
            base_cache[key] = sb
        sb = base_cache[key]
        se = run_ngspice(build(design, env, kind, detail, bench), f"{tag}__{kind}_{detail or 'none'}")
        pb, pe = python_pair(design, env, kind, detail, bench)
        sc_py = 100 * float(np.sqrt(np.mean((np.abs(pe) - np.abs(pb)) ** 2)))
        sc_sp = 100 * float(np.sqrt(np.mean((np.abs(se) - np.abs(sb)) ** 2)))
        results.append(dict(
            design=design, environment=env, scenario=label, usb_bench=bench,
            score_python_pct=round(sc_py, 5), score_spice_pct=round(sc_sp, 5),
            score_diff_pct_of_fs=round(abs(sc_py - sc_sp), 6),
            max_curve_diff_pct_of_fs=round(100 * float(max(np.max(np.abs(np.abs(pb) - np.abs(sb))),
                                                         np.max(np.abs(np.abs(pe) - np.abs(se))))), 6),
            peak_khz_python=round(float(F[np.argmax(np.abs(pe))]) / 1e3, 2),
            peak_khz_spice=round(float(F[np.argmax(np.abs(se))]) / 1e3, 2)))
        curves[(design, env, label, bench)] = (pb, pe, sb, se)

    worst_curve = max(r["max_curve_diff_pct_of_fs"] for r in results)
    worst_score = max(r["score_diff_pct_of_fs"] for r in results)
    summary = dict(
        what="Python nodal solver (sg_model.solve) vs ngspice AC analysis, same 200-point sweep, "
             "typical (midpoint) values; skin CPEs as fitted R-C ladders in SPICE",
        ngspice=subprocess.run(["ngspice", "-v"], capture_output=True, text=True).stdout.split("\n")[1].strip("* "),
        ladder_max_rel_error_1kHz_3_5MHz=ladder_err,
        n_cases=len(results),
        worst_curve_diff_pct_of_full_scale=worst_curve,
        worst_score_diff_pct_of_full_scale=worst_score,
        adc_noise_pct_of_full_scale=NOISE_PCT,
        cases=results)
    with open(os.path.join(ROOT, "data", "spice_crosscheck.json"), "w") as fh:
        json.dump(summary, fh, indent=1)

    print(f"ladder max relative error (1 kHz - 3.5 MHz): {ladder_err}")
    print(f"{'design':12s} {'env':14s} {'scenario':28s} {'python %':>9s} {'spice %':>9s} {'max diff %FS':>12s}")
    for r in results:
        print(f"{r['design']:12s} {r['environment']:14s} {r['scenario'][:28]:28s} "
              f"{r['score_python_pct']:9.4f} {r['score_spice_pct']:9.4f} {r['max_curve_diff_pct_of_fs']:12.2e}")
    print(f"\n{len(results)} cases. Worst sweep-curve difference: {worst_curve:.2e} % of full scale; "
          f"worst change-score difference: {worst_score:.2e} % (ADC noise is {NOISE_PCT} %).")
    figure(curves, results)


def figure(curves, results):
    ps.apply()
    fig = plt.figure(figsize=(14, 9.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.15], hspace=0.5, wspace=0.3)
    show = [("single", "Wrist grab"), ("dual_shield", "Wrist grab"), ("dual_shield", "Her own hand on watch")]
    fk = F / 1e3
    for i, (design, label) in enumerate(show):
        ax = fig.add_subplot(gs[0, i])
        pb, pe, sb, se = curves[(design, "street_shoes", label, False)]
        ax.plot(fk, np.abs(pb), color=ps.SERIES[0], lw=2.6, label="No touch: Python")
        ax.plot(fk[::3], np.abs(sb)[::3], "o", ms=4.5, mfc="none", mec=ps.INK, mew=1.1, label="No touch: SPICE")
        ax.plot(fk, np.abs(pe), color=ps.SERIES[1], lw=2.6, label=f"{label}: Python")
        ax.plot(fk[::3], np.abs(se)[::3], "s", ms=4.0, mfc="none", mec=ps.CRITICAL, mew=1.1,
                label=f"{label}: SPICE")
        ax.set_xlim(0, 800)
        ax.set_xlabel("Sweep frequency (kHz)")
        if i == 0:
            ax.set_ylabel("Sense-node amplitude (× drive)")
        ax.set_title(f"{label}", pad=20)
        ps.subtitle(ax, ps.DESIGN_LABEL[design])
        ax.legend(loc="upper right", fontsize=8)

    ax = fig.add_subplot(gs[1, :2])
    sel = [r for r in results if r["environment"] == "street_shoes" and not r["usb_bench"]]
    labels = [c[2] for c in CASES]
    y = np.arange(len(labels))
    for j, d in enumerate(m.DESIGNS):
        rows = {r["scenario"]: r for r in sel if r["design"] == d}
        py = [rows[l]["score_python_pct"] for l in labels]
        sp = [rows[l]["score_spice_pct"] for l in labels]
        off = (j - 1) * 0.26
        ax.barh(y + off, py, height=0.24, color=ps.DESIGN_COLOR[d], label=ps.DESIGN_LABEL[d] + " (Python)")
        ax.plot(sp, y + off, "|", color=ps.INK, ms=9, mew=1.6, label="SPICE" if j == 0 else None)
    ax.axvline(NOISE_PCT, color=ps.MUTED, ls="--", lw=1.2)
    ax.text(NOISE_PCT * 1.08, len(labels) - 0.4, "ADC noise", color=ps.INK2, fontsize=8.5)
    ax.set_xscale("log")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Change from no touch (RMS over the sweep, % of full scale)")
    ax.set_title("Change score, every scenario: bars = Python, black ticks = SPICE", pad=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, fontsize=8)
    ax.grid(axis="y", visible=False)

    ax = fig.add_subplot(gs[1, 2])
    diffs = np.array([max(r["max_curve_diff_pct_of_fs"], 1e-12) for r in results])
    ax.hist(np.log10(diffs), bins=20, color=ps.SERIES[2])
    ax.axvline(np.log10(NOISE_PCT), color=ps.CRITICAL, lw=1.6)
    ax.text(np.log10(NOISE_PCT) - 0.15, ax.get_ylim()[1] * 0.92, "ADC noise\n0.1 %", color=ps.CRITICAL,
            fontsize=8.5, ha="right", va="top")
    ax.set_xlabel("log10 (largest difference, % of full scale)")
    ax.set_ylabel("Cases")
    ax.set_title("Python vs SPICE: largest difference", pad=20)
    ps.subtitle(ax, f"{len(results)} cases, all 200 sweep points")
    fig.suptitle("Circuit model cross-checked with SPICE (ngspice)", x=0.01, ha="left",
                 fontsize=15, fontweight="bold", color=ps.INK)
    ps.footnote(fig, "Same circuit and typical values, solved independently. Skin constant-phase elements "
                     "realised in SPICE as fitted R-C ladders (Valsa et al. 2011).")
    ps.save(fig, os.path.join(ROOT, "figures", "fig13_spice_crosscheck.png"))


if __name__ == "__main__":
    main()
