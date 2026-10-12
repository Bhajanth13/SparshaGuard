"""
SparshaGuard - lumped-element electrical model of a battery-powered wrist sensor,
the wearer, a second person, and the environment.  Version 0.3 (sourced values; forearm coupling from the 3D solve since 12 Oct 2026).

Every parameter carries a tag in the comment next to it:
    [S#]  value taken from a published source (list in docs/parameter_sources.md)
    [G]   computed from geometry (parallel-plate or self-capacitance formulas)
    [D]   a design choice for our watch (we decide it; change it to explore designs)
    [E]   still an engineering estimate - no published value found; measure in Gate 1
    [E, settled]  an estimate whose full range changes no result (sensitivity check, 11 Oct 2026)

Sources used here:
    S1  Sato, Poupyrev, Harrison, "Touché", CHI 2012                     (proposal ref 5)
    S2  Harrison, Sato, Poupyrev, "Capacitive Fingerprinting", UIST 2012 (proposal ref 6)
    S3  Honigman et al., "Techniques in Swept Frequency Capacitive Sensing:
        an open source approach", NIME 2014 (Arduino Touché circuit values)
    S4  Jonassen, "Human body capacitance: static or dynamic concept?", EOS/ESD 1998
    S5  Maity et al., "Bio-physical modeling, characterization and optimization of
        electro-quasistatic human body communication", IEEE TBME 2019
    S6  Martinsen, Grimnes, Sveen, "Dielectric properties of some keratinised tissues.
        Part 1: stratum corneum and nail in situ", Med. Biol. Eng. Comput. 1997
    S7  Ng, Reaz, "Characterization of textile-insulated capacitive biosensors",
        Sensors 2017
    S8  Avlani, Nath, Maity, Sen, DATE 2020 (buffer input capacitance 2.1 pF;
        return-path capacitance ~ device self-capacitance)
    S10 Goyal, Borkholder, Day, "Dependence of skin-electrode contact impedance on
        material and skin hydration", Sensors 2022 (dry metal electrodes on skin)
    S11 Datta, Nath, Yang, Sen, "Advanced biophysical model to capture channel variability
        for EQS capacitive HBC", arXiv 2020 (return-path factor by body location)
    S12 Nath et al., "Inter-body coupling in EQS human body communication", Sci. Rep. 2021
    S13 Agarwal, Sahu, "Determination of hand and palm area as a ratio of body surface
        area in Indian population", Indian J. Plast. Surg. 2010
    S14 Texas Instruments SNOA926, "Capacitive sensing: ins and outs of active shielding"
    S15 Hackaday.io ADC comparison (ESP32 built-in ADC noise) - weak source

Circuit (unchanged topology, same as the open-source Arduino Touché [S3]):

    nodes:  S  sense node (what the envelope detector / ADC reads)
            B  wearer's body
            A  second person's body (attacker, bystander, or nobody)
            E  environment / earth (floor, walls, car body ...)
            0  watch circuit ground (reference; it FLOATS - not tied to earth)

    source -> S : Vs through Rs + jwL         S - 0 : C_tank + node parasitics
    S - B : electrode-skin (stratum corneum + metal contact, Goyal 2022) + tissue R
    B - 0 : watch ground / outer electrode to wrist      B - E : wearer to surroundings
    0 - E : watch return path                            B - A : contact / cloth / proximity
    A - E : second person to surroundings                A - 0 : his hand on/near the watch

Measurement: amplitude only, like Touché [S1, S2] (no phase).
"""
from __future__ import annotations

import numpy as np

EPS0 = 8.854e-12
pF = 1e-12
CM2 = 1e-4

# Touché sweep [S1]: 1 kHz to 3.5 MHz, 17.5 kHz steps, 200 steps per sweep
FREQS = 1e3 + 17.5e3 * np.arange(200)


def set_sweep(n_points=200, f_lo=1e3, f_hi=3.4835e6, kind="linear"):
    """Change the sweep (use m.FREQS afterwards, not a copied name)."""
    global FREQS
    if kind == "linear":
        FREQS = np.linspace(f_lo, f_hi, n_points)
    else:
        FREQS = np.logspace(np.log10(f_lo), np.log10(f_hi), n_points)


DESIGNS = ["single", "dual", "dual_shield"]
ENVS = ["street_shoes", "sandals", "barefoot_tile", "car_seat"]
LOCATIONS = ["wrist", "forearm", "upper_arm", "other_arm", "shoulder", "waist", "face_hair"]
OBJECTS = ["railing_hand", "railing_wrist", "phone", "wood_table", "bag"]
CLASSES = ["no_contact", "object", "self", "other_person"]

# probability that a grab at this location is on bare skin (otherwise through clothing) [E]
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


def _f():
    return FREQS[None, :]


def _w():
    return 2 * np.pi * _f()


def yc(C):
    """Admittance of a capacitor (array of C in farads) -> (n, F)."""
    return 1j * _w() * np.asarray(C)[:, None]


def plate(er, area_m2, gap_m):
    """Parallel-plate capacitance [G]."""
    return EPS0 * er * area_m2 / gap_m


# ------------------------------------------------------------------ skin model
# Goyal et al. 2022 [S10], dry metal electrodes on skin, fitted per cm^2:
#   stratum corneum: Rsc 6.4 MOhm.cm^2 (dry) -> 3.0 MOhm.cm^2 (hydrated),
#                    CPE Csc 41 nF/cm^2 (dry) -> 190 nF/cm^2 (hydrated), exponent ~0.9
#   metal contact:   CPE Cc 114 nF/cm^2 for stainless steel (dry), exponent 0.5-0.6;
#                    hydrated value scaled by the titanium dry->hydrated ratio 267->420 [S10]
# 'hyd' runs from 0 (dry) to 1 (hydrated); values are interpolated on a log scale.
# (Martinsen et al. [S6] palm values agree in size and are kept as a cross-check.)
def _lerp_log(a, b, h):
    return np.exp(np.log(a) + (np.log(b) - np.log(a)) * h)


def z_sc(area_cm2, hyd, alpha):
    """Stratum corneum layer: Rsc || CPE(Csc, alpha), for the given area [S10]."""
    w = _w()
    A = np.asarray(area_cm2)[:, None]
    h = np.asarray(hyd)[:, None]
    rsc = _lerp_log(6.4e6, 3.0e6, h) / A
    qsc = _lerp_log(41e-9, 190e-9, h) * A
    return 1.0 / (1.0 / rsc + qsc * (1j * w) ** np.asarray(alpha)[:, None])


def z_metal(area_cm2, hyd, beta):
    """Metal-to-skin contact CPE (stainless steel) [S10]."""
    w = _w()
    A = np.asarray(area_cm2)[:, None]
    qc = _lerp_log(114e-9, 114e-9 * 420 / 267, np.asarray(hyd)[:, None]) * A
    return 1.0 / (qc * (1j * w) ** np.asarray(beta)[:, None])


def z_electrode(area_cm2, hyd, alpha, beta):
    """Dry stainless-steel electrode on skin = contact + stratum corneum [S10]."""
    return z_metal(area_cm2, hyd, beta) + z_sc(area_cm2, hyd, alpha)


# --------------------------------------------------------------------------- base
def sample_base(s: Sampler, design: str, env: str, grounded_bench: bool = False) -> dict:
    """Device, wearer and environment parameters (per sample)."""
    n = s.n
    p = {}
    # Arduino Touché tank [S3]: R 10 kOhm, L 10 mH, C 100 pF (5 % parts [D])
    p["Rs"] = np.full(n, 10e3)
    p["L"] = np.full(n, 10e-3) * (1 + 0.05 * s.norm(0.5))
    # + sense-node parasitics: buffer input 2.1 pF [S8] to 5 pF op-amp input, + traces [E]
    p["Ctank"] = (100 * (1 + 0.05 * s.norm(0.5)) + s.u(2, 7)) * pF
    # inner electrode: 2-4 cm^2 stainless steel on the case back [D]; skin per [S10]
    p["el_area"] = s.u(2, 4)
    p["hyd"] = s.u(0.0, 1.0)                        # 0 dry .. 1 hydrated [S10]
    p["alpha"] = s.u(0.88, 0.92)                    # stratum corneum CPE exponent ~0.9 [S10]
    p["beta"] = s.u(0.50, 0.60)                     # metal contact CPE exponent 0.5-0.6 [S10]
    # wrist -> trunk tissue: 100-400 Ohm subcutaneous/limb [S5] + ~100 Ohm trunk [S1]
    p["Rbody"] = s.u(100, 400) + 100
    # watch ground to wrist [G]: PCB ground plane 8-12 cm^2, 2-4 mm through case back,
    # effective er 1.5-2.5 (plastic + air)  -> ~3-13 pF
    cgb = plate(s.u(1.5, 2.5), s.u(8, 12) * CM2, s.u(2e-3, 4e-3))
    if design in ("dual", "dual_shield"):
        # outer electrode on the strap, 20-30 cm^2, through 1.5-3 mm strap of er 2.5-3.5 [G]
        cgb = cgb + plate(s.u(2.5, 3.5), s.u(20, 30) * CM2, s.u(1.5e-3, 3e-3))
    if design == "dual_shield":
        # driven shield leaves 20-50 % of the coupling: TI measured 23-66 % residual for flat
        # shields, ~23 % for a ring + underside shield larger than the electrode [S14]
        cgb = cgb * s.u(0.20, 0.50)
    p["C_GB"] = cgb
    # wearer to surroundings, AC-bridge values [S4]: shoes on asphalt 110-115 pF, shoes on
    # linoleum 160-170 pF, barefoot asphalt 185 pF, barefoot linoleum 250 pF; ~150 pF [S5]
    p["C_BE"] = {"street_shoes": s.u(110, 170), "sandals": s.u(130, 210),     # sandals [E, settled]
                 "barefoot_tile": s.u(185, 250), "car_seat": s.u(150, 300)}[env] * pF  # car [E, settled]
    # watch return path: free-space self-capacitance 8*eps0*a [S11, G] times the on-body
    # factor at the wrist, x = 0.364 [S11] -> ~0.4-0.5 pF for a 3-4 cm board; Maity et al.
    # measured ~1.5 pF for a wearable [S5]. Range spans both.
    # With the outer electrode the conductor is a ~5-6 cm ring round the wrist: 8*eps0*a x 0.364
    # ~ 0.65-0.75 pF [G/S11], up to ~2 pF [E].
    cge = (s.lu(0.4, 1.5) if design == "single" else s.lu(0.6, 2.0)) * pF
    if env == "car_seat":
        cge = cge * s.u(1.3, 2.0)                   # metal car body nearby [E, settled]
    p["C_GE_free"] = cge                            # return path when not earthed
    if grounded_bench:
        cge = np.full(n, 10e-9)                     # USB to a mains-earthed laptop
    p["C_GE"] = cge
    # second person to surroundings: same footwear data [S4]
    p["C_AE"] = (s.u(110, 170) + (s.u(40, 130) if env == "car_seat" else 0.0)) * pF
    return p


def base_branches(p: dict) -> dict:
    """Admittances (n, F) for the always-present branches."""
    w = _w()
    br = {}
    br["Ysrc"] = 1.0 / (p["Rs"][:, None] + 1j * w * p["L"][:, None])
    br["Y_S0"] = yc(p["Ctank"])
    br["Y_SB"] = 1.0 / (z_electrode(p["el_area"], p["hyd"], p["alpha"], p["beta"]) + p["Rbody"][:, None])
    br["Y_B0"] = yc(p["C_GB"])
    br["Y_BE"] = yc(p["C_BE"])
    br["Y_0E"] = yc(p["C_GE"])
    br["Y_AE"] = yc(p["C_AE"])
    zero = np.zeros_like(br["Y_B0"])
    br["Y_BA"] = zero.copy()
    br["Y_A0"] = zero.copy()
    return br


# ------------------------------------------------------------------- contact parts
def _skin(s):
    """A random person's skin state: hydration 0..1 and CPE exponent [S10]."""
    return s.u(0.0, 1.0), s.u(0.88, 0.92)


def z_skin_skin(s, area):
    """Two stratum corneum layers in series (hers and his) [S10]."""
    h1, a1 = _skin(s)
    h2, a2 = _skin(s)
    return z_sc(area, h1, a1) + z_sc(area, h2, a2)


def z_cloth(s, area):
    """Fabric between the skins: er 1.2-5.1, 0.16-0.58 mm per layer [S7]; 1-2 layers [E]."""
    C = plate(s.u(1.2, 5.1), area * CM2, s.u(0.16e-3, 0.58e-3) * s.u(1, 2))
    h1, a1 = _skin(s)
    h2, a2 = _skin(s)
    return 1.0 / yc(C) + z_sc(area, h1, a1) + z_sc(area, h2, a2)


def y_outer_contact(s, design):
    """A hand resting on the outer electrode (or on the case if there is none)."""
    if design == "single":
        # hand over the case: 2-6 cm^2 above the ground plane, 3-6 mm away, er ~2 [G]
        return yc(plate(2.0, s.u(2, 6) * CM2, s.u(3e-3, 6e-3)))
    area = s.u(10, 20)                               # palm on strap electrode [E, settled]
    h, a = _skin(s)
    coat = plate(3.0, area * CM2, s.u(25e-6, 100e-6))  # 25-100 um coating, er 3 [D]
    return 1.0 / (z_sc(area, h, a) + 1.0 / yc(coat))


# --------------------------------------------------- his hand near the strap (3D)
# Extra watch-ground <-> body coupling when his hand grips her forearm a given gap (cm) from the
# strap edge: boundary-element solve in fem/hand_near_strap.py, checked with FastCap
# (fem/fastcap_crosscheck.py, within 1 %). His palm is on her skin, so the hand is at her body's
# potential in the 3D solve; in the circuit it is the A-0 branch, with A tied to B by the skin
# contact. The driven shield sits under the case, so the strap edge facing his hand is the same
# with and without it: both outer-electrode designs use the 'dual' curve.
FEM_GAP_CM = np.array([1.0, 2.0, 3.0, 5.0, 10.0])
FEM_HAND_PF = {"dual": np.array([1.4364, 0.4363, 0.2395, 0.1180, 0.0487]),
               "single": np.array([0.3494, 0.1106, 0.0612, 0.0312, 0.0134])}


def hand_near_strap_pF(gap_cm, design):
    """Log-log interpolation of the 3D result, gap 1-10 cm."""
    curve = FEM_HAND_PF["single" if design == "single" else "dual"]
    g = np.clip(np.asarray(gap_cm, float), FEM_GAP_CM[0], FEM_GAP_CM[-1])
    return np.exp(np.interp(np.log(g), np.log(FEM_GAP_CM), np.log(curve)))


# ------------------------------------------------------------------------- events
def apply_drift(p: dict, s: Sampler, strong: bool) -> dict:
    """Changes between the stored baseline and 'now' that are NOT a touch [E]:
    sweat (skin hydration), strap gap changes (C_GB), feet lifting while walking (C_BE;
    feet dominate body-capacitance variation per Jonassen [S4])."""
    q = dict(p)
    q["hyd"] = np.clip(p["hyd"] + s.norm(0.15 if strong else 0.04), 0.0, 1.0)
    q["C_GB"] = p["C_GB"] * (1 + s.norm(0.05 if strong else 0.015))
    q["C_BE"] = p["C_BE"] * s.lognorm(0.10 if strong else 0.03)
    return q


def event_branches(p_now: dict, s: Sampler, design: str, kind: str, detail: str | None):
    br = base_branches(p_now)
    if kind == "no_contact":
        if detail == "bystander":
            # body-to-body: 21 pF at 1 m by FEM [S12]; closer than 1 m it is higher [E upper]
            br["Y_BA"] = yc(s.u(21, 40) * pF)
            br["Y_A0"] = yc(p_now["C_GE_free"] * s.u(0.01, 0.10))   # his body to the watch [E]
    elif kind == "other_person":
        loc = detail
        # hand contact 40-80 cm^2: 30-55 % of an adult hand's palmar area, 132-147 cm^2 [S13]
        area = s.u(40, 80)
        bare = s.p(BARE_PROB[loc])
        zc = np.where(bare[:, None], z_skin_skin(s, area), z_cloth(s, area))
        br["Y_BA"] = 1.0 / zc
        if loc == "wrist":
            on_electrode = s.p(0.85)
            prox = yc((s.u(0.5, 3) if design != "single" else s.u(0.2, 1)) * pF)  # [E]
            br["Y_A0"] = np.where(on_electrode[:, None], y_outer_contact(s, design), prox)
        elif loc == "forearm":
            # his hand grips her forearm 1-5 cm from the strap edge [E: grip position; closer than
            # 1 cm counts as a wrist grab]; coupling from the 3D boundary-element solve [G, fem/],
            # confirmed with FastCap to within 1 % -> ~0.12-1.4 pF (outer electrode)
            br["Y_A0"] = yc(hand_near_strap_pF(s.u(1, 5), design) * pF)
        else:
            # his body 0.3-0.6 m from the watch: 2-20 % of the watch's return path [E, settled]
            br["Y_A0"] = yc(p_now["C_GE_free"] * s.u(0.02, 0.20))
    elif kind == "self":
        r_arms = 2 * s.u(100, 400)                      # two limb segments [S5]
        br["Y_B0"] = br["Y_B0"] + 1.0 / (1.0 / y_outer_contact(s, design) + r_arms[:, None])
    elif kind == "object":
        if detail in ("railing_hand", "railing_wrist"):  # earthed metal, 20-40 cm^2 grip [E, settled]
            h, a = _skin(s)
            A = s.u(20, 40)
            br["Y_BE"] = br["Y_BE"] + 1.0 / (z_sc(A, h, a) + z_metal(A, h, s.u(0.5, 0.6)))
            if detail == "railing_wrist":
                if design == "single":
                    c = plate(3.0, s.u(1, 3) * CM2, s.u(1.5e-3, 3e-3))      # case side [G]
                else:
                    c = plate(3.0, s.u(2, 10) * CM2, s.u(25e-6, 100e-6))    # coated strap [G]
                br["Y_0E"] = br["Y_0E"] + yc(c)
        elif detail == "phone":
            # phone self-capacitance 8*eps0*r, r_eq 6-10 cm -> 4-7 pF, up to 12 pF [G/E]
            h, a = _skin(s)
            br["Y_BE"] = br["Y_BE"] + 1.0 / (z_sc(s.u(20, 40), h, a) + 1.0 / yc(s.u(4, 12) * pF))
        elif detail == "wood_table":
            br["Y_0E"] = br["Y_0E"] + yc(s.u(1, 5) * pF)   # [E]
            br["Y_BE"] = br["Y_BE"] + yc(s.u(5, 20) * pF)  # [E]
        elif detail == "bag":
            br["Y_BE"] = br["Y_BE"] + yc(s.u(2, 10) * pF)  # bag [E, settled]
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
    """Per-frequency amplitude change in units of full scale (the drive amplitude Vs),
    which is what an ADC reading of the envelope gives, and phase change (rad)."""
    da = np.abs(v_evt) - np.abs(v_base)
    dph = np.angle(v_evt / v_base)
    return da, dph


def change_score(v_base, v_evt):
    """Single number: RMS amplitude change across the sweep, as a fraction of full
    scale (amplitude-only measurement, as in Touché [S1])."""
    da = np.abs(v_evt) - np.abs(v_base)
    return np.sqrt(np.mean(da ** 2, axis=-1))


def peak_freq(v):
    a = np.abs(v)
    return FREQS[np.argmax(a, axis=-1)]


def add_noise(v, sigma, rng):
    """ADC-style measurement noise, absolute, as a fraction of full scale.
    1e-3 FS: ESP32 built-in ADC fluctuates ~21.8 mV (~0.66 % of 3.3 V) [S15]; averaging
    16 sweeps gives ~0.03-0.17 % depending on whether that figure is p-p or std. dev."""
    if sigma <= 0:
        return v
    nz = rng.normal(0, sigma, v.shape) + 1j * rng.normal(0, sigma, v.shape)
    return v + nz
