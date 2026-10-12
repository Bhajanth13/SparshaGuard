"""Independent check of the hand-near-strap 3D result with FastCap (MIT, Nabors & White 1991).

FastCap is the standard reference capacitance solver used in chip and package design. Here it
solves the same geometry as fem/hand_near_strap.py, built again as real surface panels (flat
quadrilaterals and triangles) with FastCap's own panel integrals, multipole acceleration and
mesh. Agreement means our own boundary-element solver and its geometry are right.

Steps
  1. Validate FastCap here against an exact result: an isolated sphere, C = 4*pi*eps0*R.
  2. Watch + arm with and without his hand at 1, 2, 3, 5, 10 cm from the strap edge, for the
     outer-electrode and single-electrode designs; extra coupling = increase in the
     watch-ground <-> body mutual capacitance (same definition as hand_near_strap.py).
  3. Repeat on a mesh about 1.5x finer in each direction to show the answer has converged.

Build FastCap (C source, github.com/ediloren/FastCap2, branch WRCad):
    git clone -b WRCad https://github.com/ediloren/FastCap2 && cd FastCap2 && mkdir -p bin
    cd src && make fastcap CFLAGS="-O2 -fcommon -DFOUR"
Run:  FASTCAP=/path/to/FastCap2/bin/fastcap python fem/fastcap_crosscheck.py     (~5-10 min)
Writes fem/fastcap_results.json and figures/fig14_fastcap_crosscheck.png
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import plotstyle as ps  # noqa: E402

FASTCAP = os.environ.get("FASTCAP", "fastcap")
EPS0 = 8.854187817e-12
R_ARM, R_STRAP, W_STRAP = 0.027, 0.031, 0.022       # same as hand_near_strap.py
DISTANCES = [1, 2, 3, 5, 10]                        # cm (0.5 cm did not converge in fem/)


# ------------------------------------------------------------------ panel geometry
class Mesh:
    def __init__(self):
        self.lines = []

    def quad(self, name, p):
        self.lines.append("Q %s " % name + " ".join("%.7e" % v for v in np.ravel(p)))

    def tri(self, name, p):
        self.lines.append("T %s " % name + " ".join("%.7e" % v for v in np.ravel(p)))

    def cyl(self, name, r, z0, z1, phi0, phi1, h):
        nz = max(1, int(np.ceil((z1 - z0) / h)))
        nphi = max(3, int(np.ceil(r * (phi1 - phi0) / h)))
        zs = np.linspace(z0, z1, nz + 1)
        ps_ = np.linspace(phi0, phi1, nphi + 1)
        for i in range(nz):
            for j in range(nphi):
                pts = [(ps_[j], zs[i]), (ps_[j + 1], zs[i]), (ps_[j + 1], zs[i + 1]), (ps_[j], zs[i + 1])]
                self.quad(name, [[r * np.cos(p), r * np.sin(p), z] for p, z in pts])

    def ring(self, name, r0, r1, z, phi0, phi1, h):
        """Flat annular sector at height z (r0 = 0 gives a disc; the centre ring is triangles)."""
        nr = max(1, int(np.ceil((r1 - r0) / h)))
        rs = np.linspace(r0, r1, nr + 1)
        for k in range(nr):
            nphi = max(3, int(np.ceil(rs[k + 1] * (phi1 - phi0) / h)))
            ps_ = np.linspace(phi0, phi1, nphi + 1)
            for j in range(nphi):
                a, b = ps_[j], ps_[j + 1]
                if rs[k] == 0:
                    self.tri(name, [[0, 0, z], [rs[1] * np.cos(a), rs[1] * np.sin(a), z],
                                    [rs[1] * np.cos(b), rs[1] * np.sin(b), z]])
                else:
                    self.quad(name, [[rs[k] * np.cos(a), rs[k] * np.sin(a), z],
                                     [rs[k + 1] * np.cos(a), rs[k + 1] * np.sin(a), z],
                                     [rs[k + 1] * np.cos(b), rs[k + 1] * np.sin(b), z],
                                     [rs[k] * np.cos(b), rs[k] * np.sin(b), z]])

    def plate_x(self, name, x0, half, h):
        n = int(np.ceil(2 * half / h))
        u = np.linspace(-half, half, n + 1)
        for i in range(n):
            for j in range(n):
                self.quad(name, [[x0, u[i], u[j]], [x0, u[i + 1], u[j]],
                                 [x0, u[i + 1], u[j + 1]], [x0, u[i], u[j + 1]]])

    def sphere(self, name, R, n):
        th = np.linspace(0, np.pi, n + 1)
        for k in range(n):
            nphi = max(3, int(round(2 * n * np.sin(0.5 * (th[k] + th[k + 1])))))
            ps_ = np.linspace(0, 2 * np.pi, nphi + 1)
            for j in range(nphi):
                pt = lambda t, p: [R * np.sin(t) * np.cos(p), R * np.sin(t) * np.sin(p), R * np.cos(t)]
                if k == 0:
                    self.tri(name, [pt(th[0], 0), pt(th[1], ps_[j]), pt(th[1], ps_[j + 1])])
                elif k == n - 1:
                    self.tri(name, [pt(th[k], ps_[j]), pt(th[n], 0), pt(th[k], ps_[j + 1])])
                else:
                    self.quad(name, [pt(th[k], ps_[j]), pt(th[k + 1], ps_[j]),
                                     pt(th[k + 1], ps_[j + 1]), pt(th[k], ps_[j + 1])])

    def __len__(self):
        return len(self.lines)


def build(d_cm, design, s=1.0):
    """Same geometry as hand_near_strap.build(); s scales every panel size (s < 1 = finer)."""
    fine, mid, coarse = 0.003 * s, 0.008 * s, 0.02 * s
    m = Mesh()
    for z0, z1, h in [(-0.30, -0.15, coarse), (-0.15, -0.05, mid), (-0.05, 0.05, fine),
                      (0.05, 0.15, mid), (0.15, 0.18, coarse)]:
        m.cyl("body", R_ARM, z0, z1, 0, 2 * np.pi, h)
    m.ring("body", 0, R_ARM, -0.30, 0, 2 * np.pi, coarse)
    m.ring("body", 0, R_ARM, 0.18, 0, 2 * np.pi, coarse)
    if design == "dual":
        m.cyl("watch", R_STRAP, -W_STRAP / 2, W_STRAP / 2, 0, 2 * np.pi, fine)
        m.plate_x("watch", R_ARM + 0.012, 0.02, fine)
    else:
        m.plate_x("watch", R_ARM + 0.006, 0.0175, fine)
    if d_cm is not None:
        z_near = -W_STRAP / 2 - d_cm / 100
        z_far = z_near - 0.09
        ro = R_ARM + 0.02
        gap = np.deg2rad(60)
        phi0, phi1 = np.pi + gap / 2, 3 * np.pi - gap / 2
        h = (0.005 if d_cm <= 2 else 0.008) * s
        m.cyl("body", ro, z_far, z_near, phi0, phi1, h)
        m.ring("body", R_ARM, ro, z_near, phi0, phi1, h)
        m.ring("body", R_ARM, ro, z_far, phi0, phi1, h)
    return m


# ------------------------------------------------------------------------ FastCap
def run(mesh, tol=1e-5, order=3):
    with tempfile.TemporaryDirectory() as tmp:
        qui = os.path.join(tmp, "geom.qui")
        lst = os.path.join(tmp, "geom.lst")
        with open(qui, "w") as fh:
            fh.write("0 SparshaGuard geometry\n" + "\n".join(mesh.lines) + "\n")
        with open(lst, "w") as fh:
            fh.write(f"C {qui} 1.0 0.0 0.0 0.0\n")
        t = time.time()
        r = subprocess.run([FASTCAP, f"-l{lst}", f"-t{tol}", f"-o{order}"],
                           capture_output=True, text=True, cwd=tmp)
        dt = time.time() - t
    out = r.stdout
    if "CAPACITANCE MATRIX" not in out:
        raise RuntimeError(out[-3000:] + r.stderr)
    blk = out.split("CAPACITANCE MATRIX")[1]
    unit = blk.split("\n")[0]
    scale = {"picofarads": 1e-12, "femtofarads": 1e-15, "nanofarads": 1e-9, "microfarads": 1e-6,
             "farads": 1.0}[re.search(r"(\w+farads)", unit).group(1)]
    rows = {}
    for line in blk.split("\n")[2:]:
        mm = re.match(r"\s*(\S+)%\S+\s+\d+\s+(.*)", line)
        if not mm:
            if rows:
                break
            continue
        rows[mm.group(1)] = [float(v) * scale for v in mm.group(2).split()]
    return rows, dt


def mutual_pF(mesh):
    rows, dt = run(mesh)
    names = list(rows)
    iw, ib = names.index("watch"), names.index("body")
    c = -0.5 * (rows["watch"][ib] + rows["body"][iw])   # symmetrise
    return c * 1e12, dt


def main():
    res = {"solver": "FastCap 2.0wr (MIT, Nabors & White 1991), GMRES tol 1e-5, multipole order 3"}

    # 1. exact check: isolated sphere
    sph = []
    for n in (12, 24, 36):
        m = Mesh()
        m.sphere("sph", 0.05, n)
        rows, _ = run(m)
        c = rows["sph"][0]
        exact = 4 * np.pi * EPS0 * 0.05
        sph.append({"panels": len(m), "C_pF": c * 1e12, "exact_pF": exact * 1e12,
                    "error_pct": 100 * (c / exact - 1)})
        print("sphere", sph[-1], flush=True)
    res["sphere_R5cm"] = sph

    # 2-3. hand near strap, two mesh levels
    fem = json.load(open(os.path.join(HERE, "hand_near_strap_results.json")))
    for design in ("dual", "single"):
        out = {}
        for s, tag in ((1.0, "mesh_1"), (0.67, "mesh_fine")):
            base, dt = mutual_pF(build(None, design, s))
            row = {"no_hand_mutual_pF": base, "panels_no_hand": len(build(None, design, s))}
            for d in DISTANCES:
                mt, dt = mutual_pF(build(d, design, s))
                row[f"d={d}cm"] = mt - base
                print(f"{design:6s} {tag:9s} d={d:>2} cm  extra {mt - base:.4f} pF   "
                      f"(our BEM {fem[design][f'd={d}cm']:.4f} pF)  {dt:.0f}s", flush=True)
            out[tag] = row
        out["our_bem"] = {k: v for k, v in fem[design].items() if k != "d=0.5cm"}
        res[design] = out
    json.dump(res, open(os.path.join(HERE, "fastcap_results.json"), "w"), indent=1)
    figure(res)


def figure(res):
    ps.apply()
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axes[0]
    d = np.array(DISTANCES, float)
    for design, col in (("dual", ps.DESIGN_COLOR["dual"]), ("single", ps.DESIGN_COLOR["single"])):
        r = res[design]
        lab = "Outer electrode" if design == "dual" else "Single electrode"
        ax.plot(d, [r["our_bem"][f"d={x:g}cm"] for x in d], "-", color=col, lw=2.4,
                label=f"{lab}: our solver (fem/)")
        ax.plot(d, [r["mesh_1"][f"d={x:g}cm"] for x in d], "o", ms=7, mfc="none", mec=ps.INK, mew=1.4,
                label=f"{lab}: FastCap")
        ax.plot(d, [r["mesh_fine"][f"d={x:g}cm"] for x in d], "x", ms=7, color=ps.CRITICAL, mew=1.4,
                label=f"{lab}: FastCap, finer mesh")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(d)
    ax.set_xticklabels([f"{x:g}" for x in d])
    ax.minorticks_off()
    ax.set_yticks([0.02, 0.05, 0.1, 0.2, 0.5, 1, 2])
    ax.set_yticklabels(["0.02", "0.05", "0.1", "0.2", "0.5", "1", "2"])
    ax.set_xlabel("Gap between his hand and the strap edge (cm)")
    ax.set_ylabel("Extra watch-to-body coupling (pF)")
    ax.set_title("His hand near the strap: two independent 3D solvers", pad=20)
    ps.subtitle(ax, "Same geometry, separate meshes and panel integrals")
    ax.legend(fontsize=8, loc="lower left")

    ax = axes[1]
    s = res["sphere_R5cm"]
    ax.plot([x["panels"] for x in s], [abs(x["error_pct"]) for x in s], "o-", color=ps.SERIES[2])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks([200, 500, 1000, 2000])
    ax.set_xticklabels(["200", "500", "1000", "2000"])
    ax.set_yticks([0.1, 0.2, 0.5, 1, 2])
    ax.set_yticklabels(["0.1", "0.2", "0.5", "1", "2"])
    ax.minorticks_off()
    ax.set_xlabel("Panels")
    ax.set_ylabel("|error| vs exact (%)")
    ax.set_title("FastCap vs exact sphere", pad=20)
    ps.subtitle(ax, "C = 4πε₀R, R = 5 cm (5.563 pF)")
    ps.footnote(fig, "FastCap: MIT multipole-accelerated capacitance solver (Nabors & White, IEEE TCAD 1991). "
                     "Geometry as in fem/hand_near_strap.py.")
    fig.tight_layout()
    ps.save(fig, os.path.join(HERE, "..", "figures", "fig14_fastcap_crosscheck.png"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--figs-only":
        figure(json.load(open(os.path.join(HERE, "fastcap_results.json"))))
    else:
        main()
