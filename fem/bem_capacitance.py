"""Minimal 3D electrostatic boundary-element solver (method of moments, flat panels).

Each conductor surface is split into small rectangular panels with uniform charge.
P[i, j] = potential at panel i's centre from unit charge on panel j:
  far:  1 / (4*pi*eps0*r)
  self: 4*a*ln(1+sqrt(2)) / (4*pi*eps0*A)  for a square of side a (exact for a square)
Capacitance matrix C = solve(P, ...) summed per conductor (Maxwell form).
"""
import numpy as np

EPS0 = 8.854e-12
K = 1.0 / (4 * np.pi * EPS0)


def cyl_band(r, z0, z1, phi0, phi1, dz, closed_ends=False):
    """Panels on a cylinder surface (axis = z), returns centres (N,3) and areas (N,)."""
    nz = max(1, int(np.ceil((z1 - z0) / dz)))
    arc = r * (phi1 - phi0)
    nphi = max(3, int(np.ceil(arc / dz)))
    zs = z0 + (np.arange(nz) + 0.5) * (z1 - z0) / nz
    ps = phi0 + (np.arange(nphi) + 0.5) * (phi1 - phi0) / nphi
    Z, P = np.meshgrid(zs, ps, indexing="ij")
    c = np.stack([r * np.cos(P).ravel(), r * np.sin(P).ravel(), Z.ravel()], 1)
    a = np.full(len(c), (z1 - z0) / nz * arc / nphi)
    if closed_ends:
        for z in (z0, z1):
            cc, aa = disc(r, z, dz)
            c, a = np.vstack([c, cc]), np.concatenate([a, aa])
    return c, a


def disc(r, z, dz):
    nr = max(1, int(np.ceil(r / dz)))
    cs, as_ = [], []
    for k in range(nr):
        r0, r1 = r * k / nr, r * (k + 1) / nr
        rm = 0.5 * (r0 + r1)
        nphi = max(3, int(np.ceil(2 * np.pi * rm / dz)))
        ps = (np.arange(nphi) + 0.5) * 2 * np.pi / nphi
        cs.append(np.stack([rm * np.cos(ps), rm * np.sin(ps), np.full(nphi, z)], 1))
        as_.append(np.full(nphi, np.pi * (r1 ** 2 - r0 ** 2) / nphi))
    return np.vstack(cs), np.concatenate(as_)


def sphere(R, n):
    """Roughly equal-area panels on a sphere (for validation)."""
    cs, as_ = [], []
    nt = n
    for k in range(nt):
        t0, t1 = np.pi * k / nt, np.pi * (k + 1) / nt
        tm = 0.5 * (t0 + t1)
        band = 2 * np.pi * R * R * (np.cos(t0) - np.cos(t1))
        nphi = max(3, int(round(2 * nt * np.sin(tm))))
        ps = (np.arange(nphi) + 0.5) * 2 * np.pi / nphi
        cs.append(np.stack([R * np.sin(tm) * np.cos(ps), R * np.sin(tm) * np.sin(ps), np.full(nphi, R * np.cos(tm))], 1))
        as_.append(np.full(nphi, band / nphi))
    return np.vstack(cs), np.concatenate(as_)


def cap_matrix(conductors):
    """conductors: list of (centres, areas). Returns Maxwell capacitance matrix (F)."""
    cents = np.vstack([c for c, _ in conductors])
    areas = np.concatenate([a for _, a in conductors])
    owner = np.concatenate([np.full(len(a), k) for k, (_, a) in enumerate(conductors)])
    from scipy.spatial.distance import cdist
    P = cdist(cents, cents)
    np.fill_diagonal(P, 1.0)
    np.divide(K, P, out=P)                      # potential per unit total charge, far field
    side = np.sqrt(areas)
    # self term: uniformly charged square of side a, potential at its centre per unit charge
    P[np.diag_indices_from(P)] = K * 4 * side * np.log(1 + np.sqrt(2)) / areas
    n = len(conductors)
    V = np.stack([(owner == k).astype(float) for k in range(n)], 1)
    Q = np.linalg.solve(P, V)   # panel charges for each conductor held at 1 V, others at 0 V
    C = np.zeros((n, n))
    for k in range(n):
        for j in range(n):
            C[j, k] = Q[owner == j, k].sum()
    return C
