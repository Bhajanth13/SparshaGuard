"""
SparshaGuard - lumped-element electrical model of a battery-powered wrist sensor,
the wearer, a second person, and the environment.

The watch drives a swept sine through a series R-L into a sense node S that has a
tank capacitor to the watch's own ground (node 0). S connects to the wearer's skin
through the inner electrode. Everything else couples capacitively:

    nodes:  S  sense node (what the ADC / envelope or lock-in detector reads)
            B  wearer's body
            A  second person's body (attacker, bystander, or nobody)
            E  environment / earth (floor, walls, car body ...)
            0  watch circuit ground (reference; it FLOATS - not tied to earth)

    branches:
      source  -> S       : Vs through Rs + jwL
      S - 0              : C_tank
      S - B              : inner electrode-skin interface (Cole model) + body tissue R
      B - 0              : watch-ground-to-wrist parasitic C_GB (+ self-touch path)
      B - E              : wearer to surroundings (air + feet/seat) (+ objects touched)
      0 - E              : watch ground to surroundings C_GE (+ objects against strap)
      B - A              : skin-skin contact, contact through clothing, or proximity
      A - E              : second person to surroundings
      A - 0              : second person's hand on the outer electrode, or proximity

Designs:
      "single"        one skin electrode, no outer electrode, no shield
      "dual"          + outer electrode (coated mesh on case and strap) tied to 0
      "dual_shield"   + driven shield that cancels most of C_GB

Every number here is an engineering assumption from typical ranges for body
capacitance, dry-electrode skin impedance and small-device self-capacitance.
They are meant to be replaced by measured values after the Gate 1 experiment.
"""
from __future__ import annotations

import numpy as np

EPS0 = 8.854e-12
pF = 1e-12
FREQS = np.logspace(np.log10(1e5), np.log10(2e6), 64)  # 100 kHz .. 2 MHz sweep

def set_sweep(n_points=64, f_lo=1e5, f_hi=2e6):
    """Change the sweep (use m.FREQS afterwards, not a copied name)."""
    global FREQS
    FREQS = np.logspace(np.log10(f_lo), np.log10(f_hi), n_points)


DESIGNS = ["single", "dual", "dual_shield"]
ENVS = ["street_shoes", "sandals", "barefoot_tile", "car_seat"]
LOCATIONS = ["wrist", "forearm", "upper_arm", "other_arm", "shoulder", "waist", "face_hair"]
OBJECTS = ["railing_hand", "railing_wrist", "phone", "wood_table", "bag"]
CLASSES = ["no_contact", "object", "self", "other_person"]

# probability that a grab at this location is on bare skin (otherwise through clothing)
BARE_PROB = {"wrist": 0.9, "forearm": 0.6, "upper_arm": 0.3, "other_arm": 0.5,
             "shoulder": 0.1, "waist": 0.05, "face_hair": 0.8}


class Sampler:
    """Random draws, or deterministic 'typical' values for clean figures."""

    def __init__(self, rng: np.random.Generator | None, n: int):
        self.rng, self.n = rng, n
        self.typical = rng is None

    def u(self, a, b):
        if self.typical:
            return np.full(self.n, 0.5 * (a + b))
        return self.rng.uniform(a, b, self.n)

    def lu(self, a, b):
        if self.typical:
            return np.full(self.n, np.sqrt(a * b))
        return np.exp(self.rng.uniform(np.log(a), np.log(b), self.n))

    def p(self, prob):
        if self.typical:
            return np.full(self.n, prob >= 0.5)
        return self.rng.random(self.n) < prob

    def lognorm(self, sigma):
        if self.typical:
            return np.ones(self.n)
        return np.exp(self.rng.normal(0, sigma, self.n))

    def norm(self, sigma):
        if self.typical:
            return np.zeros(self.n)
        return self.rng.normal(0, sigma, self.n)


def _w():
    return 2 * np.pi * FREQS[None, :]


def cole(R0, Rinf, fc, alpha):
    """Cole impedance of a skin interface, shape (n, F)."""
    w = _w()
    tau = 1.0 / (2 * np.pi * fc[:, None])
    return Rinf[:, None] + (R0 - Rinf)[:, None] / (1 + (1j * w * tau) ** alpha[:, None])


def yc(C):
    """Admittance of a capacitor (array of C in farads) -> (n, F)."""
    return 1j * _w() * np.asarray(C)[:, None]


def y_series(*Z):
    return 1.0 / sum(Z)


# --------------------------------------------------------------------------- base
def sample_base(s: Sampler, design: str, env: str, grounded_bench: bool = False) -> dict:
    """Device, wearer and environment parameters (per sample)."""
    n = s.n
    p = {}
    p["L"] = np.full(n, 1e-3)                       # 1 mH sweep inductor
    p["Rs"] = np.full(n, 1e3)                       # 1 kOhm source resistor
    p["Ctank"] = 47 * pF * (1 + 0.005 * s.norm(1))  # 47 pF tank capacitor
    # inner electrode on dry skin (sweat lowers R0)
    p["es_R0"] = s.lu(1e5, 2e6)
    p["es_Rinf"] = s.u(100, 300)
    p["es_fc"] = s.lu(1e3, 1e4)
    p["es_a"] = s.u(0.7, 0.9)
    p["Rbody"] = s.u(300, 700)                      # wrist -> trunk tissue
    # watch ground <-> wrist parasitic (PCB, battery under the case back)
    cgb = s.u(10, 30) * pF
    if design == "dual_shield":
        cgb = cgb * s.u(0.1, 0.3)                   # driven shield removes 70-90 %
    p["C_GB"] = cgb
    # wearer to surroundings
    air = s.u(60, 110) * pF
    feet = {"street_shoes": s.u(15, 40), "sandals": s.u(30, 80),
            "barefoot_tile": s.u(150, 600), "car_seat": s.u(15, 40)}[env] * pF
    seat = s.u(100, 300) * pF if env == "car_seat" else 0.0
    p["C_BE"] = air + feet + seat
    # watch ground to surroundings: a small floating object
    cge = (s.u(1.5, 3.5) if design == "single" else s.u(3, 7)) * pF
    if env == "car_seat":
        cge = cge * s.u(1.3, 2.0)
    if grounded_bench:
        cge = np.full(n, 10e-9)                     # USB to a mains-earthed laptop
    p["C_GE"] = cge
    # second person (only matters when they are near or touching)
    p["C_AE"] = s.u(60, 110) * pF + s.u(15, 40) * pF + (s.u(100, 300) * pF if env == "car_seat" else 0.0)
    return p


def base_branches(p: dict) -> dict:
    """Admittances (n, F) for the always-present branches."""
    w = _w()
    br = {}
    br["Ysrc"] = 1.0 / (p["Rs"][:, None] + 1j * w * p["L"][:, None])
    br["Y_S0"] = yc(p["Ctank"])
    Zes = cole(p["es_R0"], p["es_Rinf"], p["es_fc"], p["es_a"])
    br["Y_SB"] = 1.0 / (Zes + p["Rbody"][:, None])
    br["Y_B0"] = yc(p["C_GB"])
    br["Y_BE"] = yc(p["C_BE"])
    br["Y_0E"] = yc(p["C_GE"])
    br["Y_AE"] = yc(p["C_AE"])
    zero = np.zeros_like(br["Y_B0"])
    br["Y_BA"] = zero.copy()
    br["Y_A0"] = zero.copy()
    return br


# ------------------------------------------------------------------- contact parts
def z_skin_skin(s):
    return cole(s.lu(2e4, 5e5), s.u(200, 600), s.lu(5e3, 3e4), s.u(0.75, 0.9))


def z_cloth(s):
    C = EPS0 * s.u(1.5, 3.0) * s.u(20e-4, 100e-4) / s.lu(0.3e-3, 3e-3)
    return 1.0 / yc(C) + 1e3


def y_outer_contact(s, design):
    """A hand resting on the outer electrode (or on the case if there is none)."""
    if design == "single":
        return yc(s.u(1, 4) * pF)                   # hand over a plastic case
    zskin = cole(s.lu(1e5, 1e6), s.u(200, 500), s.lu(2e3, 2e4), s.u(0.75, 0.9))
    zcoat = 1.0 / yc(s.u(300, 2000) * pF)          # thin insulating coating
    return 1.0 / (zskin + zcoat)


# ------------------------------------------------------------------------- events
def apply_drift(p: dict, s: Sampler, strong: bool) -> dict:
    """Changes between the stored baseline and 'now' that are NOT a touch:
    sweat (electrode R0) and the watch shifting on the wrist (C_GB)."""
    q = dict(p)
    q["es_R0"] = p["es_R0"] * s.lognorm(0.30 if strong else 0.08)
    q["C_GB"] = p["C_GB"] * (1 + s.norm(0.03 if strong else 0.008))
    return q


def event_branches(p_now: dict, s: Sampler, design: str, kind: str, detail: str | None):
    br = base_branches(p_now)
    if kind == "no_contact":
        if detail == "bystander":                   # someone standing very close
            br["Y_BA"] = yc(s.u(0.3, 3) * pF)
            br["Y_A0"] = yc(s.lu(0.02, 0.3) * pF)
    elif kind == "other_person":
        loc = detail
        bare = s.p(BARE_PROB[loc])
        zc = np.where(bare[:, None], z_skin_skin(s), z_cloth(s))
        br["Y_BA"] = 1.0 / zc
        if loc == "wrist":
            on_electrode = s.p(0.85)
            prox = yc((s.u(1, 5) if design != "single" else s.u(0.5, 3)) * pF)
            br["Y_A0"] = np.where(on_electrode[:, None], y_outer_contact(s, design), prox)
        elif loc == "forearm":
            br["Y_A0"] = yc((s.u(1, 6) if design != "single" else s.u(0.5, 3)) * pF)
        else:                                       # his body somewhere near the watch
            br["Y_A0"] = yc(s.lu(0.03, 0.6) * pF)
    elif kind == "self":                            # her other hand on watch / strap
        r_arm = s.u(600, 1200)[:, None]
        br["Y_B0"] = br["Y_B0"] + 1.0 / (1.0 / y_outer_contact(s, design) + r_arm)
    elif kind == "object":
        if detail in ("railing_hand", "railing_wrist"):  # earthed metal
            zc = cole(s.lu(5e4, 1e6), s.u(100, 300), s.lu(2e3, 2e4), s.u(0.75, 0.9))
            br["Y_BE"] = br["Y_BE"] + 1.0 / zc
            if detail == "railing_wrist":           # strap pressed against the metal
                c = (s.u(5, 20) if design == "single" else s.u(100, 1500)) * pF
                br["Y_0E"] = br["Y_0E"] + yc(c)
        elif detail == "phone":                     # floating object in the hand
            zc = cole(s.lu(5e4, 1e6), s.u(100, 300), s.lu(2e3, 2e4), s.u(0.75, 0.9))
            br["Y_BE"] = br["Y_BE"] + y_series(zc, 1.0 / yc(s.u(8, 25) * pF))
        elif detail == "wood_table":
            br["Y_0E"] = br["Y_0E"] + yc(s.u(1, 5) * pF)
            br["Y_BE"] = br["Y_BE"] + yc(s.u(5, 20) * pF)
        elif detail == "bag":
            br["Y_BE"] = br["Y_BE"] + yc(s.u(2, 10) * pF)
    else:
        raise ValueError(kind)
    return br


# ------------------------------------------------------------------------- solver
def solve(br: dict) -> np.ndarray:
    """Nodal analysis. Returns complex V_S / Vs, shape (n, F)."""
    n, F = br["Y_SB"].shape
    Y = np.zeros((n, F, 4, 4), dtype=complex)
    S, B, A, E = 0, 1, 2, 3
    Y[..., S, S] = br["Ysrc"] + br["Y_S0"] + br["Y_SB"]
    Y[..., S, B] = Y[..., B, S] = -br["Y_SB"]
    Y[..., B, B] = br["Y_SB"] + br["Y_B0"] + br["Y_BE"] + br["Y_BA"]
    Y[..., B, A] = Y[..., A, B] = -br["Y_BA"]
    Y[..., B, E] = Y[..., E, B] = -br["Y_BE"]
    Y[..., A, A] = br["Y_BA"] + br["Y_AE"] + br["Y_A0"]
    Y[..., A, E] = Y[..., E, A] = -br["Y_AE"]
    Y[..., E, E] = br["Y_BE"] + br["Y_AE"] + br["Y_0E"]
    I = np.zeros((n, F, 4, 1), dtype=complex)
    I[..., S, 0] = br["Ysrc"]                       # Vs = 1 V
    V = np.linalg.solve(Y, I)
    return V[..., S, 0]


# ---------------------------------------------------------------- convenience API
def simulate_pair(design, env, kind, detail=None, n=1, rng=None, grounded_bench=False,
                  strong_drift=False):
    """Baseline response and event response for the same person/environment."""
    s = Sampler(rng, n)
    p = sample_base(s, design, env, grounded_bench)
    v_base = solve(base_branches(p))
    p_now = apply_drift(p, s, strong_drift)
    v_evt = solve(event_branches(p_now, s, design, kind, detail))
    return v_base, v_evt


def rel_change(v_base, v_evt):
    """Per-frequency relative amplitude change and phase change (rad)."""
    da = (np.abs(v_evt) - np.abs(v_base)) / np.abs(v_base)
    dph = np.angle(v_evt / v_base)
    return da, dph


def change_score(v_base, v_evt):
    """Single number: RMS of relative complex change across the sweep."""
    return np.sqrt(np.mean(np.abs(v_evt / v_base - 1) ** 2, axis=-1))


def peak_freq(v):
    a = np.abs(v)
    return FREQS[np.argmax(a, axis=-1)]


def add_noise(v, sigma, rng):
    """Complex measurement noise relative to signal level (lock-in I/Q noise)."""
    if sigma <= 0:
        return v
    nz = rng.normal(0, sigma, v.shape) + 1j * rng.normal(0, sigma, v.shape)
    return v * (1 + nz)
