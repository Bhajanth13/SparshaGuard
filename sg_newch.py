"""SparshaGuard new channels (28 Oct 2026): her own hand on the watch, electrode motion noise, the
100 kHz transmit check, and electrodermal activity (EDA). Tags as in sg_model.py.

1. Her own hand on the watch changes the fraction k the static channel sees
   The static channel reads k x V_B with k = C_GE / (C_GE + C_GB + C_in) (whole_body.py). Her finger
   or palm over the glass couples her body to the watch ground through the display stack, adding
   C_hand to C_GB, so k drops in a few ms with no charge moving.
     fingertip pad 0.5-1.5 cm^2 [E]; palm over the face 4-12 cm^2 [G: 1.43" round display ~10 cm^2]
     display stack 1.5-3 mm, effective er 3-7 (cover glass er ~6-7 plus layers) [G/E]
     rest of the hand hovering 1-5 cm away: 0.3-1.5 pF (as the 3D solve, fem/) [G/E]
     a tap takes ~133 ms to complete [S72] -> the finger lands at ~0.1-0.3 m/s [E]
     a touch session holds 1-4 taps of 0.1-0.3 s [E]; 30 % of sessions cover the face with the palm [E]
2. Electrode motion noise on the static channel
   Forearm skin carries ~15 mV across the epidermis; stretching the skin reduces it, which appears
   as a motion artefact under a dry electrode, growing with stretch force [S67]. Each arm jerk adds
   a smooth 0.3-3 mV bump lasting as long as the jerk; walking adds 0.05-0.5 mV of arm-swing ripple [E].
3. Transmit check (loading mode, Zimmerman et al. [S70])
   The steel back sends a small 100 kHz signal into her skin and the watch measures that current.
   Her hand over the watch adds C_hand between her body and the watch ground, so the current jumps
   at the same instant as the static step; a stranger touching her elsewhere leaves it flat (the
   earth around a floating watch sits at her own potential, so his body adds almost nothing).
   Shunt mode (a receive electrode on the strap whose signal drops when a grounded hand blocks it,
   as in DiamondTouch [S71]) does not work on a floating watch: a stranger's hand raises the
   received signal just like hers (transmit_study below, fig 19).
   Safety: 0.5 V at 100 kHz drives ~10-60 uA through her body, under the 100 uA patient auxiliary
   current that IEC 60601-1 allows even at DC-1 kHz (type B/BF, normal condition) [S69].
4. Electrodermal activity on the split case back (two pads, ~0.5 V DC [D])
   skin conductance response: onset 1-3 s after the stimulus, rise 1-3 s, half-recovery 2-10 s,
     smallest scored response 0.01-0.05 uS [S61, S62]
   non-specific (spontaneous) responses 1-5 per minute at rest; ~20-25 per minute at high arousal [S62]
   first response to an aversive startle: 1.56 +- 0.35 uS at 2.34 s (finger/palm) [S63]
   the wrist responds less than the palm (intermediate site; r = 0.55-0.59 with the finger) [S65],
     but the distal forearm is a usable site [S64] -> wrist responses 0.2-0.6 x the finger [E]
   70 % of women assaulted reported significant tonic immobility (freezing) [S68]: many grabs hold her
     without any pulling, which is what the EDA path is for
   grab -> fear response with probability 0.9 [E]; a harmless brush by a stranger -> orienting
     response with probability 0.3, median 0.3 uS (finger) [E]; a friend holding her wrist 0.2 [E]
   motion artefacts: pressure changes at the pads during jerks add fast 0.05-0.5 uS blips [E];
     firmware rejects rises faster than 1 uS/s or during an arm jerk (rule structure as Kleckner [S66])
"""
from __future__ import annotations

import numpy as np

pF, EPS0, CM2 = 1e-12, 8.854e-12, 1e-4
FS_EDA = 8                     # EDA samples per second
TX_FREQ = 100e3                # transmit check frequency [D]
TX_NOISE = 0.003               # relative noise of the transmit current per 2 ms sample [E]
P_COVER = 0.3                  # touch sessions that cover the face with the palm [E]
P_STRANGER_FACE = 0.3          # wrist grabs where his palm also covers her watch face [E]


# ----------------------------------------------------------------------------- own hand / k
def hand_contact_pF(rng, cover):
    """Capacitance her hand adds between her body and the watch ground once it rests on the glass."""
    area = rng.uniform(4, 12) if cover else rng.uniform(0.5, 1.5)          # [G] / [E]
    er, d = rng.uniform(3, 7), rng.uniform(1.5e-3, 3e-3)                    # [G/E]
    hover = rng.uniform(0.3, 1.5) * pF                                      # rest of the hand [G/E]
    return EPS0 * er * area * CM2 / d + hover, d / er


def landing(c_contact, d_eff, speed, fs, g0=10e-3):
    """C(t) while the hand closes a g0 gap at constant speed: C = C_contact d_eff / (g + d_eff)."""
    n = max(2, int(g0 / speed * fs))
    g = np.linspace(g0, 0.0, n)
    return c_contact * d_eff / (g + d_eff)


def self_touch_trace(rng, n_session, fs, cover):
    """C_hand(t) over one touch session of n_session samples (taps or a covering palm)."""
    c = np.zeros(n_session)
    cc, de = hand_contact_pF(rng, cover)
    speed = rng.uniform(0.1, 0.3)                                           # [E, from S72]
    ramp = landing(cc, de, speed, fs)
    if cover:
        spans = [(0, n_session)]
    else:
        k = rng.integers(1, 5)                                              # 1-4 taps [E]
        starts = np.sort(rng.uniform(0, max(1, n_session - 0.4 * fs), k)).astype(int)
        spans = [(s, min(n_session, s + int(rng.uniform(0.1, 0.3) * fs))) for s in starts]
    for s0, s1 in spans:
        L = len(ramp)
        up = ramp[: max(0, min(L, s1 - s0))]
        c[s0:s0 + up.size] = np.maximum(c[s0:s0 + up.size], up)
        c[s0 + up.size:s1] = cc
        down = ramp[::-1][: max(0, min(L, n_session - s1))]                  # lifting off
        c[s1:s1 + down.size] = np.maximum(c[s1:s1 + down.size], down)
    return c


# ------------------------------------------------------------------------ motion artefacts
def skin_stretch(rng, n, fs, jerks, walking_swing=None):
    """Skin-stretch artefact (V) at the electrode: a smooth bump per arm jerk [S67/E] and arm-swing
    ripple while walking [E]. jerks: list of (t_s, width_s)."""
    a = np.zeros(n)
    for t, w in jerks:
        i0, L = int(t * fs), max(4, int(w * fs))
        if i0 >= n:
            continue
        bump = rng.uniform(0.3e-3, 3e-3) * rng.choice([-1, 1]) * np.hanning(L)
        a[i0:i0 + L] += bump[: n - i0]
    if walking_swing is not None:
        f, ph = walking_swing
        t = np.arange(n) / fs
        a += rng.uniform(0.05e-3, 0.5e-3) * np.sin(2 * np.pi * f * t + ph)
    return a


# ---------------------------------------------------------------------------- transmit check
def tx_trace(c_hand, c_load0, rng):
    """Relative 100 kHz transmit current: 1 + C_hand / C_load0, plus noise [G/E]."""
    return 1 + c_hand / c_load0 + rng.normal(0, TX_NOISE, c_hand.size)


def tx_says_own_hand(u, tx, i, rms, gain):
    """Firmware check at a static step at sample i+1: did the transmit current jump at the same
    moment, and does the step match the k change that jump predicts (her own hand, no charge
    moved)? gain: C_load0 / (C_GE + C_GB + C_in) as the firmware calibrated it at start-up, so a
    current jump j means k'/k = 1 / (1 + j gain); the calibration is off by up to 20 % [E]."""
    if i < 25 or i + 25 >= tx.size:
        return False
    before, after = np.median(tx[i - 20:i - 4]), np.median(tx[i + 6:i + 22])
    jump = after / before - 1
    if abs(jump) < 0.02:                                                    # 2 % [E] >> noise
        return False
    u0, u1 = np.median(u[i - 20:i - 4]), np.median(u[i + 6:i + 22])
    rho = 1 / (1 + jump * gain)                                    # predicted k'/k
    pred = (rho - 1) * u0
    return abs((u1 - u0) - pred) < 0.25 * abs(pred) + 6 * rms


# --------------------------------------------------------------------------------- EDA
class EDA:
    """Skin conductance (uS) at the dorsal wrist, FS_EDA samples per second."""

    def __init__(self, rng, ctx, seconds):
        self.rng, self.T = rng, seconds
        self.n = int(seconds * FS_EDA)
        self.wrist = rng.uniform(0.2, 0.6)                                    # [E, S65]
        self.scl = rng.uniform(0.5, 5.0)                                      # tonic level [E]
        base = rng.uniform(1, 5) / 60                                         # NS-SCRs per s [S62]
        self.ns_rate = base * (1.5 if ctx == "walking" else 1.0)              # alone at night [E]
        self.responses = []                                                   # (t_onset, amp_uS_at_wrist)
        self.artefacts = []

    def respond(self, t_stim, kind):
        """A skin conductance response to a stimulus: 'attack', 'brush', 'friend'."""
        rng = self.rng
        p, med, sd = {"attack": (0.9, 1.56, 0.25), "brush": (0.3, 0.3, 0.6), "friend": (0.2, 0.3, 0.6)}[kind]
        if rng.random() < p:                                                  # [E]; attack amp [S63]
            amp = med * np.exp(rng.normal(0, sd)) * self.wrist
            self.responses.append((t_stim + rng.uniform(1, 3), amp, rng.uniform(1, 3), rng.uniform(2, 10)))

    def jerk(self, t):
        """Pressure change at the pads during an arm jerk [E]."""
        self.artefacts.append((t, self.rng.uniform(0.05, 0.5) * self.rng.choice([-1, 1])))

    def signal(self):
        rng, n = self.rng, self.n
        t = np.arange(n) / FS_EDA
        sc = np.full(n, self.scl) + np.cumsum(rng.normal(0, 0.002, n))        # slow tonic drift [E]
        events = list(self.responses)
        for t0 in np.sort(rng.uniform(0, self.T, rng.poisson(self.ns_rate * self.T))):
            events.append((t0, rng.exponential(0.1) * self.wrist, rng.uniform(1, 3), rng.uniform(2, 10)))  # [S62/E]
        for t0, amp, tr, th in events:                                        # [S61] shape
            dt = t - t0
            rise = (dt >= 0) & (dt < tr)
            sc[rise] += amp * 0.5 * (1 - np.cos(np.pi * dt[rise] / tr))
            fall = dt >= tr
            sc[fall] += amp * 2 ** (-(dt[fall] - tr) / th)
        for t0, amp in self.artefacts:                                        # fast blips [E]
            dt = t - t0
            m = (dt >= 0) & (dt < 2.0)
            sc[m] += amp * np.where(dt[m] < 0.2, dt[m] / 0.2, np.exp(-(dt[m] - 0.2) / 0.6))
        return t, np.maximum(sc + rng.normal(0, 0.005, n), 0.01)


EDA_TH = 0.45         # uS at the wrist [E, tuned in passive_stream.py: 0.3 let bus brushes through]
EDA_WIN = (0.8, 4.5)  # onset window after the contact step (s): 1-3 s latency [S61] with margin


def scr_after(t, sc, t0, jerk_times, th=EDA_TH):
    """Firmware: a skin conductance response starting 0.8-4.5 s after t0, at least th uS high,
    rising no faster than 1 uS/s and not during an arm jerk (artefact rules as Kleckner [S66])."""
    sm = np.convolve(sc, np.ones(4) / 4, mode="same")
    d = np.gradient(sm) * FS_EDA
    i0, i1 = int((t0 + EDA_WIN[0]) * FS_EDA), min(sc.size - 1, int((t0 + EDA_WIN[1]) * FS_EDA))
    i = i0
    while i < i1:
        if d[i] > 0.02:                                                        # rising
            j = i
            while j < sc.size - 1 and d[j] > 0.0:
                j += 1
            amp, rate = sm[j] - sm[i], np.max(d[i:j + 1]) if j > i else 0
            jerk = any(t[i] - 0.5 <= tj <= t[j] + 0.5 for tj in jerk_times)
            if amp >= th and rate < 1.0 and not jerk and (j - i) / FS_EDA >= 0.5:
                return True
            i = j + 1
        else:
            i += 1
    return False


# --------------------------------------------------------------- transmit/shunt circuit study
def transmit_study(n=4000, seed=1):
    """100 kHz nodal solve on a floating watch (sg_model branches). The back electrode drives her
    body; we read (a) the transmit current and (b) the current into a shielded receive electrode on
    the strap (shunt/transmit mode). Returns {case: (transmit ratio, receive ratio)} vs nobody."""
    import sg_model as m
    keep = m.FREQS
    m.FREQS = np.array([TX_FREQ])
    w = 2 * np.pi * TX_FREQ

    def run(case):
        rng = np.random.default_rng(seed)
        s = m.Sampler(rng, n)
        p = m.sample_base(s, "dual_shield", "street_shoes")
        y_tb = 1 / (m.z_electrode(p["el_area"], p["hyd"], p["alpha"], p["beta"])[:, 0] + p["Rbody"])
        y_b0, y_be, y_0e, y_ae = (1j * w * p[k] for k in ("C_GB", "C_BE", "C_GE", "C_AE"))
        cstrap = m.plate(s.u(2.5, 3.5), s.u(20, 30) * CM2, s.u(1.5e-3, 3e-3))
        y_br = 1j * w * cstrap * s.u(0.20, 0.50)              # receive pad to wrist, through the shield [G, S14]
        z = np.zeros(n, complex)
        y_ba, y_ar, y_er = z.copy(), z.copy(), z.copy()
        has_a = case.startswith("stranger")
        outer = lambda: m.y_outer_contact(s, "dual_shield")[:, 0]
        if case == "her hand on the strap":
            y_br = y_br + 1 / (1 / outer() + 2 * s.u(100, 400))
        elif case == "her hand on the glass":
            y_b0 = y_b0 + 1j * w * EPS0 * s.u(3, 7) * s.u(4, 12) * CM2 / s.u(1.5e-3, 3e-3)
        elif case == "stranger: hand on the strap only":
            y_ar, y_ba = outer(), 1j * w * s.u(1, 5) * pF
        elif case == "stranger: grabs wrist skin + strap":
            y_ba, y_ar = 1 / m.z_skin_skin(s, s.u(40, 80))[:, 0], outer()
        elif case == "stranger: grabs forearm":
            y_ba = 1 / m.z_skin_skin(s, s.u(40, 80))[:, 0]
            y_ar = 1j * w * m.hand_near_strap_pF(s.u(1, 5), "dual") * pF
        elif case == "stranger: grabs shoulder":
            y_ba = 1 / m.z_skin_skin(s, s.u(40, 80))[:, 0]
        elif case == "metal pole on the strap":
            y_er = 1j * w * m.plate(s.u(2.65, 3.15), s.u(2, 10) * CM2, s.u(25e-6, 100e-6))
        Y = np.zeros((n, 3, 3), complex)
        B, A, E = 0, 1, 2
        Y[:, B, B] = y_tb + y_b0 + y_be + y_ba + y_br
        Y[:, B, A] = Y[:, A, B] = -y_ba
        Y[:, B, E] = Y[:, E, B] = -y_be
        Y[:, A, A] = y_ba + y_ae * has_a + y_ar + (0 if has_a else 1.0)
        Y[:, A, E] = Y[:, E, A] = -y_ae * has_a
        Y[:, E, E] = y_be + y_ae * has_a + y_0e + y_er
        I = np.zeros((n, 3, 1), complex)
        I[:, B, 0] = y_tb * 0.5                                # 0.5 V drive [D]
        V = np.linalg.solve(Y, I)[..., 0]
        i_r = y_br * V[:, B] + y_ar * V[:, A] + y_er * V[:, E]
        i_t = y_tb * (0.5 - V[:, B])
        return i_t, i_r, V
    t0, r0, v0 = run("nobody")
    out = {"_baseline": {"transmit_uA": float(np.median(np.abs(t0)) * 1e6), "receive_uA": float(np.median(np.abs(r0)) * 1e6),
                         "earth_over_body": float(np.median(np.abs(v0[:, 2] / v0[:, 0])))}}
    for case in ["her hand on the glass", "her hand on the strap", "stranger: hand on the strap only",
                 "stranger: grabs wrist skin + strap", "stranger: grabs forearm", "stranger: grabs shoulder",
                 "metal pole on the strap"]:
        ti, ri, _ = run(case)
        out[case] = {"transmit": np.percentile(np.abs(ti) / np.abs(t0), [5, 50, 95]).tolist(),
                     "receive": np.percentile(np.abs(ri) / np.abs(r0), [5, 50, 95]).tolist()}
    m.FREQS = keep
    return out


def main():
    import json
    import matplotlib.pyplot as plt
    import plotstyle as ps
    ps.apply()
    res = transmit_study()
    json.dump(res, open("data/transmit_results.json", "w"), indent=1)
    cases = [c for c in res if not c.startswith("_")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), sharey=True)
    y = np.arange(len(cases))
    for ax, key, title, col in ((axes[0], "receive", "Shunt / transmit mode: signal on a strap receive pad", ps.SERIES[0]),
                                (axes[1], "transmit", "Transmit check: current the back electrode drives into her", ps.SERIES[2])):
        lo, med, hi = (np.array([res[c][key][i] for c in cases]) for i in range(3))
        ax.barh(y, med, color=col, height=0.55)
        ax.errorbar(med, y, xerr=[med - lo, hi - med], fmt="none", ecolor=ps.INK2, capsize=3, lw=1)
        ax.axvline(1, color=ps.MUTED, ls="--", lw=1)
        ax.set_xscale("log")
        ax.set_xlabel("Change vs nobody touching (×, median and 5–95 %)")
        ax.set_title(title, pad=8)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(cases)
    axes[0].invert_yaxis()
    fig.suptitle("A floating watch: a stranger's hand raises the strap signal just like hers (shunt mode fails),\n"
                 "but the transmit current flags her own hand on the glass while a stranger elsewhere leaves it flat",
                 x=0.01, ha="left", fontsize=12, fontweight="bold", color=ps.INK)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    ps.save(fig, "figures/fig19_transmit_check.png")
    for c in cases:
        print(f"{c:36s} receive x{res[c]['receive'][1]:7.2f}  transmit x{res[c]['transmit'][1]:6.2f}")
    print(res["_baseline"])


if __name__ == "__main__":
    main()
