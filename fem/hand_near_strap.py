"""3D electrostatic calculation: extra coupling between the watch's outer electrode (watch ground)
and the wearer's arm when another person's hand grips her forearm d cm away from the strap.

Geometry (metres, z along the arm, wrist at z = 0, hand side z > 0, elbow side z < 0):
  arm      cylinder r = 2.7 cm (wrist), z = -30 .. +18 cm, closed ends          -> conductor 1
  strap    outer electrode band r = 3.1 cm (4 mm strap), width 2.2 cm, 360 deg  -> conductor 0
  case     watch-top plate 4 x 4 cm at 1.2 cm above the skin (part of conductor 0)
  hand     his grip: shell outer radius r_arm + 2 cm, 300 deg wrap, 9 cm long, near edge d cm
           from the strap edge on the forearm side. His palm touches her skin, so it is at her
           body's potential: modelled as part of conductor 1 (inner surface is internal).
Output: increase in watch-ground <-> body mutual capacitance caused by the hand, i.e. the
model's 'his hand near the strap' coupling.
"""
import json
import numpy as np
import bem_capacitance as b

R_ARM, R_STRAP, W_STRAP = 0.027, 0.031, 0.022


def graded_cyl(r, zlist, phi0=0, phi1=2 * np.pi):
    cs, as_ = [], []
    for (z0, z1, dz) in zlist:
        c, a = b.cyl_band(r, z0, z1, phi0, phi1, dz)
        cs.append(c); as_.append(a)
    return np.vstack(cs), np.concatenate(as_)


def end_cap(r, z, dz):
    return b.disc(r, z, dz)


def annulus(r0, r1, z, phi0, phi1, dz):
    nr = max(1, int(np.ceil((r1 - r0) / dz)))
    cs, as_ = [], []
    for k in range(nr):
        ra, rb = r0 + (r1 - r0) * k / nr, r0 + (r1 - r0) * (k + 1) / nr
        rm = 0.5 * (ra + rb)
        nphi = max(3, int(np.ceil(rm * (phi1 - phi0) / dz)))
        ps = phi0 + (np.arange(nphi) + 0.5) * (phi1 - phi0) / nphi
        cs.append(np.stack([rm * np.cos(ps), rm * np.sin(ps), np.full(nphi, z)], 1))
        as_.append(np.full(nphi, 0.5 * (rb ** 2 - ra ** 2) * (phi1 - phi0) / nphi))
    return np.vstack(cs), np.concatenate(as_)


def plate_x(x0, half, dz):
    n = int(np.ceil(2 * half / dz))
    u = -half + (np.arange(n) + 0.5) * 2 * half / n
    Y, Z = np.meshgrid(u, u, indexing="ij")
    c = np.stack([np.full(Y.size, x0), Y.ravel(), Z.ravel()], 1)
    return c, np.full(Y.size, (2 * half / n) ** 2)


def build(d_cm=None, design="dual"):
    fine, mid, coarse = 0.003, 0.008, 0.02
    arm = graded_cyl(R_ARM, [(-0.30, -0.15, coarse), (-0.15, -0.05, mid), (-0.05, 0.05, fine),
                             (0.05, 0.15, mid), (0.15, 0.18, coarse)])
    caps = [end_cap(R_ARM, -0.30, coarse), end_cap(R_ARM, 0.18, coarse)]
    body = [arm] + caps
    if design == "dual":
        watch = [b.cyl_band(R_STRAP, -W_STRAP / 2, W_STRAP / 2, 0, 2 * np.pi, fine),
                 plate_x(R_ARM + 0.012, 0.02, fine)]
    else:  # single electrode: only the PCB ground plane inside the case, 6 mm above the skin
        watch = [plate_x(R_ARM + 0.006, 0.0175, fine)]
    if d_cm is not None:
        z_near = -W_STRAP / 2 - d_cm / 100
        z_far = z_near - 0.09
        ro = R_ARM + 0.02
        gap = np.deg2rad(60)
        phi0, phi1 = np.pi + gap / 2, 3 * np.pi - gap / 2   # opening on the watch-top side
        dz = 0.005 if d_cm <= 2 else mid
        body += [b.cyl_band(ro, z_far, z_near, phi0, phi1, dz),
                 annulus(R_ARM, ro, z_near, phi0, phi1, dz),
                 annulus(R_ARM, ro, z_far, phi0, phi1, dz)]
    cond0 = (np.vstack([c for c, _ in watch]), np.concatenate([a for _, a in watch]))
    cond1 = (np.vstack([c for c, _ in body]), np.concatenate([a for _, a in body]))
    return [cond0, cond1]


def mutual(conds):
    C = b.cap_matrix(conds)
    return -C[0, 1], C


if __name__ == "__main__":
    out = {}
    for design in ("dual", "single"):
        base, Cb = mutual(build(None, design))
        res = {"no_hand_mutual_pF": base * 1e12, "watch_self_pF": Cb[0, 0] * 1e12}
        for d in (0.5, 1, 2, 3, 5, 10):
            mtl, _ = mutual(build(d, design))
            res[f"d={d}cm"] = (mtl - base) * 1e12
            print(design, d, "cm  extra coupling %.3f pF" % ((mtl - base) * 1e12), flush=True)
        out[design] = res
        print(design, res, flush=True)
    json.dump(out, open("hand_near_strap_results.json", "w"), indent=1)
