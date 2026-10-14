"""SparshaGuard passive channel: her body voltage over time, and what the wrist electrode sees.

Static charge on bodies, sampled at 500 Hz, plus a wrist accelerometer at 50 Hz. Tags as in sg_model.py.

Her body (capacitance C_B, charge Q_B, V_B = Q_B / C_B):
  C_B, C_A 110-250 pF on both feet                                        [S4]
  standing on one foot C_B drops to 100/160 = 0.625 of that               [S40]
    gait timing: double support 0-10 % and 50-60 % of the stride, loading
    response (foot landing) 0-10 %, toe-off at 60 %                       [S46]
  charge leaks to ground with tau = R C, R 2e10 [S18] to 1e11 ohm [S40]
    (log-uniform) -> tau 3-25 s
  walking charges her by dq per step; the peak voltage is R n dq           [S18]
    -> dq = V_peak / (R n); V_peak is set by floor, shoes and humidity:
       250 V (humid) to 12 kV (dry) on vinyl                               [S17]
       roads, tiles, bus floors: unknown -> swept by the scale v0          [E]
    cadence n: women 96-138 steps/min -> 1.6-2.3 steps/s                  [S41]
  a step's charge separates while the foot lifts, over 20-60 ms            [E]
  her own arm movement changes C_B by 2-7 %; changing posture (sitting
  down) changes body capacitance by under 10 pF of ~150 pF [S42]; ~0.3 s [E]
Another person: his voltage at contact is his own walking level, v0 x lognormal, random sign [E].
Contact (charge sharing, settles in well under 1 ms):
  bare skin:   both bodies reach (Q_A + Q_B) / (C_A + C_B)
  through cloth: series capacitor C_c (fabric [S7], hand area [S13]):
               dV_B = (V_A - V_B) / (C_B (1/C_A + 1/C_B + 1/C_c))
Approach without touching: induced shift V_A C_AB(d) / (C_B + C_AB), C_AB = 21 pF at 1 m, 6.6 pF at
  5 m [S12] -> C_AB ~ 21 pF (1 m / d)^0.72, extrapolated below 1 m [E]; a walk-up takes ~1 s.
Earthed metal (railing, pole): pulls her to 0 V and holds her there while she touches it.
50 Hz hum (indoors only): drops to ~5 % on earthed metal, changes 0.6-1.6x on a person [S22 / E].
The watch sees k = C_GE / (C_GE + C_GB + C_in) of V_B (whole_body.py, fig 11), plus ADC noise:
  ADS1115 ~2 mV, ESP32 ~21.8 mV fluctuation, taken here as 4x the rms noise   [S15 / E].
Wrist accelerometer, magnitude in g:
  walking: arm swing at half the step rate [S44], amplitude pi x ENMO with wrist ENMO 140 mg
    (slow) to 350 mg (brisk walking) [S43]
  bus: random sway 0.1 g [E] plus starting/braking jolts of 0.1-0.34 g (bus maxima 3.37 m/s^2
    starting, 3.12 m/s^2 braking [S45]), 12 per hour [E]
  desk: 0.02 g [E]; her own brisk gestures 15/h, 1.0-2.2 g for 0.2-0.4 s [E]
  a grab with pulling: 2-5 jerks of 1.5-3 g in 3 s (70 % of grabs pull; the rest just hold) [E:
    no published wrist accelerations for being grabbed were found]
"""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter

FS = 500                    # passive channel, samples per second
FS_IMU = 50
pF, EPS0, CM2 = 1e-12, 8.854e-12, 1e-4
R_GROUND = (2e10, 1e11)     # body-to-ground resistance range, log-uniform [S18, S40]
CADENCE = (1.6, 2.3)        # steps per second, women [S41]
ONE_FOOT = 100 / 160        # C_B on one foot / on both feet [S40]
POSTURE = (0.02, 0.07)      # her own movement: relative change of C_B [S42 bound]
FRONT = {"current": dict(cgb=12.4 * pF, cin=5 * pF, adc=21.8e-3, label="Current input, ESP32 ADC"),
         "improved": dict(cgb=2.0 * pF, cin=0.5 * pF, adc=2e-3, label="Bootstrapped input + ADS1115")}
BARE_PROB = {"wrist": 0.9, "forearm": 0.6, "upper_arm": 0.3, "other_arm": 0.5,
             "shoulder": 0.1, "waist": 0.05, "face_hair": 0.8}            # as sg_model.py [E]


def walk_peak_vinyl(rh):
    """Peak walking voltage on vinyl vs relative humidity: 12 kV at 15 %, 250 V at 77.5 % [S17],
    log-interpolated [E]."""
    t = np.clip((rh - 15) / 62.5, 0, 1)
    return float(np.exp(np.log(12000) + (np.log(250) - np.log(12000)) * t))


def c_ab(d):
    """Body-to-body capacitance at distance d (m), from Nath et al. 21 pF @ 1 m, 6.6 pF @ 5 m [S12]."""
    return 21 * pF * (1.0 / np.maximum(d, 0.15)) ** 0.72


def watch_fraction(front, cge):
    f = FRONT[front]
    return cge / (cge + f["cgb"] + f["cin"])


def cloth_capacitance(rng, area_cm2):
    return EPS0 * rng.uniform(1.2, 5.1) * area_cm2 * CM2 / (rng.uniform(0.16e-3, 0.58e-3) * rng.uniform(1, 2))


def share(va, vb, ca, cb, cc=None):
    """Her new voltage after touching body A (cc=None: bare skin)."""
    if cc is None:
        return (va * ca + vb * cb) / (ca + cb)
    return vb + (va - vb) / (cb * (1 / ca + 1 / cb + 1 / cc))


def smooth_motion(n, rng, tau=0.3):
    """Unit-variance arm-movement signal, smooth on the ms scale (two cascaded 0.3 s lags)."""
    a = np.exp(-1 / (FS * tau))
    x = lfilter([1 - a], [1, -a], lfilter([1 - a], [1, -a], rng.normal(0, 1, n)))
    return x / (np.std(x) + 1e-12)


class Scene:
    """One stretch of her day. Events are dicts with t0, t1 (s) and a kind:
       'person' (loc, attack: bool, pull: bool, v_a), 'approach' (v_a, dmin), 'earthed', 'gesture', 'jolt'."""

    def __init__(self, ctx, seconds, v0, front, rng, rh=50):
        self.ctx, self.T, self.v0, self.front, self.rng = ctx, seconds, v0, front, rng
        self.n = int(seconds * FS)
        self.cb = rng.uniform(110, 250) * pF
        self.R = np.exp(rng.uniform(np.log(R_GROUND[0]), np.log(R_GROUND[1])))
        self.cadence = rng.uniform(*CADENCE)
        self.posture = rng.uniform(*POSTURE)
        self.enmo = rng.uniform(0.14, 0.35)
        self.cge = np.exp(rng.uniform(np.log(0.6), np.log(2.0))) * pF          # [S5/S11]
        self.k = watch_fraction(front, self.cge)
        self.walking = ctx == "walking"
        self.indoor = ctx == "desk"
        self.sign = rng.choice([-1.0, 1.0])
        self.vpeak = v0 * np.exp(rng.normal(0, 0.7)) if self.walking or ctx == "bus" else v0 * 0.1 * np.exp(rng.normal(0, 0.7))
        self.events = []
        self.heel = np.arange(rng.uniform(0, 1 / self.cadence), seconds, 1 / self.cadence) if self.walking else np.array([])

    def foot_factor(self):
        """C_B(t) / C_B on both feet while walking: 1 in double support, ONE_FOOT in single support.
        Each heel strike starts the loading response (0-10 % of the stride: the landing foot comes
        down) and the other foot lifts off over the next 10 % [S46]."""
        f = np.ones(self.n)
        if not self.walking:
            return f
        stride = 2 / self.cadence
        t = np.arange(self.n) / FS
        lift = np.ones(self.n)
        for th in self.heel:
            i0, i1, i2 = (int((th + x * stride) * FS) for x in (0.0, 0.1, 0.2))
            i1, i2 = min(i1, self.n), min(i2, self.n)
            if i0 >= self.n:
                break
            lift[i0:i1] = np.linspace(1, 0, i1 - i0) if i1 > i0 else lift[i0:i1]   # landing: C rises
            lift[i1:i2] = np.linspace(0, 1, i2 - i1) if i2 > i1 else lift[i1:i2]   # other foot lifts
        del t
        return 1 - (1 - ONE_FOOT) * lift

    def add(self, **ev):
        self.events.append(ev)

    # ------------------------------------------------------------------ signals
    def body_voltage(self):
        """Her charge Q_B leaks with tau = R C_B and is fed by her steps; events jump it.
        Returns t, V_B(t) and the indoor hum envelope."""
        n, rng = self.n, self.rng
        t = np.arange(n) / FS
        a = np.exp(-1 / (FS * self.R * self.cb))
        inj = np.zeros(n)                                     # charge added per sample
        if self.walking:
            dq = self.sign * self.vpeak / (self.R * self.cadence)   # V_peak = R n dq  [S18]
            for th in self.heel:
                i0, w = int(th * FS), int(rng.uniform(0.02, 0.06) * FS)
                inj[i0:i0 + w] += dq / w                      # separated while the foot lifts [E]
        elif self.ctx == "bus":                               # shifting her feet now and then [E]
            dq = self.sign * self.vpeak / (self.R * self.cadence)
            for th in np.sort(rng.uniform(0, self.T, int(self.T * 0.2))):
                i0, w = int(th * FS), int(rng.uniform(0.02, 0.06) * FS)
                inj[i0:i0 + w] += dq / w
        q = np.empty(n)
        q_prev = self.sign * self.vpeak * self.cb * rng.uniform(0.3, 1.0)   # charge she already carries
        cuts = sorted(self.events, key=lambda e: e["t0"])
        hum = np.full(n, 1.0 if self.indoor else 0.0)
        vind = np.zeros(n)                                    # induced by charged people nearby
        for ev in cuts:
            if ev["kind"] != "approach":
                continue
            i0, i1 = int(ev["t0"] * FS), min(n, int(ev["t1"] * FS))   # walk-up over ~1 s, stay, leave
            L = i1 - i0
            d = np.full(L, ev["dmin"])
            r = min(FS, L // 2)
            d[:r] = np.linspace(3.0, ev["dmin"], r)
            if not ev.get("stay"):                            # he walks away again
                d[L - r:] = np.linspace(ev["dmin"], 3.0, r)
            cab = c_ab(d) - c_ab(3.0)                         # starts and ends at 0 (3 m away)
            vind[i0:i1] += ev["v_a"] * cab / (self.cb + cab)
        cmov = (1 + self.posture * smooth_motion(n, rng)) * self.foot_factor()   # her movement and her feet [S40, S42]
        pinned = np.zeros(n, bool)
        pos, pin_until = 0, -1
        for ev in cuts + [{"t0": self.T + 1, "kind": "end"}]:
            i0 = min(n, int(ev["t0"] * FS))
            if i0 > pos:                                      # evolve to the event
                seg, zi = lfilter([1.0], [1, -a], inj[pos:i0], zi=[a * q_prev])
                q[pos:i0] = seg
                if pin_until > pos:                           # still holding earthed metal
                    hold = min(pin_until, i0)
                    q[pos:hold] = 0.0
                    if hold < i0:                             # let go: keeps the charge that cancelled vind
                        q[hold:i0] = lfilter([1.0], [1, -a], inj[hold:i0], zi=[-a * vind[hold] * self.cb * cmov[hold]])[0]
                q_prev = q[i0 - 1]
                pos = i0
            if ev["kind"] == "end" or i0 >= n:
                continue
            i1 = min(n, int(ev["t1"] * FS))
            vb = q_prev / self.cb
            if ev["kind"] == "person" and ev.get("small"):     # phone or other small floating object [G/E]
                q_prev = share(ev["v_a"], vb, rng.uniform(4, 12) * pF, self.cb) * self.cb
            elif ev["kind"] == "person":
                ca = rng.uniform(110, 250) * pF
                cc = None if rng.random() < BARE_PROB[ev["loc"]] else cloth_capacitance(rng, rng.uniform(40, 80))
                q_prev = share(ev["v_a"], vb, ca, self.cb, cc) * self.cb
                hum[i0:i1] *= rng.uniform(0.6, 1.6)
            elif ev["kind"] == "earthed":
                q_prev, pin_until = 0.0, i1
                pinned[i0:i1] = True                          # held at 0 V: induced charge drains too
                hum[i0:i1] *= 0.05
        v = q / (self.cb * cmov) + np.where(pinned, 0.0, vind)
        return t, v, hum

    def watch_signal(self, v):
        rms = FRONT[self.front]["adc"] / 4
        return self.k * v + self.rng.normal(0, rms, v.size)

    def accel(self):
        rng, n = self.rng, int(self.T * FS_IMU)
        t = np.arange(n) / FS_IMU
        acc = np.ones(n)
        if self.walking:
            acc += np.pi * self.enmo * np.sin(np.pi * self.cadence * t + rng.uniform(0, 6.3))   # [S43, S44]
        sway = {"walking": 0.05, "bus": 0.10, "desk": 0.02}[self.ctx]
        acc += lfilter([np.sqrt(1 - np.exp(-2 / (FS_IMU * 1.0)))], [1, -np.exp(-1 / FS_IMU)], rng.normal(0, sway, n))
        for ev in self.events:
            i0 = int(ev["t0"] * FS_IMU)
            if ev["kind"] == "gesture":
                w = int(rng.uniform(0.2, 0.4) * FS_IMU)
                acc[i0:i0 + w] += rng.uniform(1.0, 2.2) * np.hanning(w)[: len(acc[i0:i0 + w])]
            if ev["kind"] == "jolt":
                w = int(0.3 * FS_IMU)
                acc[i0:i0 + w] += rng.uniform(0.1, 0.34) * np.hanning(w)[: len(acc[i0:i0 + w])]   # [S45]
            if ev["kind"] == "person" and ev.get("pull"):
                for _ in range(rng.integers(2, 6)):
                    j = i0 + int(rng.uniform(0.2, 3.0) * FS_IMU)
                    w = int(0.15 * FS_IMU)
                    acc[j:j + w] += rng.uniform(1.5, 3.0) * np.hanning(w)[: len(acc[j:j + w])]
        return t, acc


# ---------------------------------------------------------------------- detectors (firmware)
STEP_K = 6.0              # a contact step must exceed 6x the rms noise within one 2 ms sample [E, tuned]
SETTLE = 0.3              # ...and move less than 30 % of that over the next 30 ms (charge sharing settles)
GATE = 0.0                # heel-strike gate (s); not needed once the local-roughness test is in [tested]
LOCAL_K = 8.0             # ...and exceed 8x the local roughness of the signal in the +-50 ms around it
OBJECT_FRAC = 0.12        # a small floating object takes at most C/(C_B+C) ~ 10 % of her voltage
AGIT_G = 1.25             # agitation: |a - 1 g| above 1.25 g ...
AGIT_N = 2                # ... in at least 2 separate jerks within 3 s of the contact step


def contact_steps(u, rms, heel=None, hum=None, indoor=False):
    """Sharp steps in the wrist signal u (500 Hz). Returns list of (time s, size V, kind)."""
    d = np.diff(u)
    thr = STEP_K * rms * np.sqrt(2)                          # noise of a sample-to-sample difference
    cand = np.where(np.abs(d) > thr)[0]
    out, last = [], -10.0
    for i in cand:
        t = (i + 1) / FS
        if t - last < 0.25:
            continue
        j = i + 1 + int(0.03 * FS)
        if j >= u.size or i < 26 or i + 27 >= d.size:
            continue
        around = np.r_[d[i - 25:i - 2], d[i + 3:i + 26]]          # +-50 ms, the step itself left out
        md = np.median(around)
        rough = 1.4826 * np.median(np.abs(around - md))
        slope = 0.0      # a slope-aware test caught 3 % more grabs while walking but let false steps through
        di = d[i] - slope                                         # the step on top of any ramp
        if abs(u[i + 2] - u[i - 1] - 3 * slope) < LOCAL_K * rough:   # rough signal: her own movement
            continue
        if abs(u[j] - u[i + 1] - slope * (j - i - 1)) > SETTLE * abs(di) + 4 * rms:   # still moving: not a contact
            continue
        k0 = i - int(0.015 * FS)
        if abs(u[i] - u[k0] - slope * (i - k0)) > SETTLE * abs(di) + 4 * rms:   # already moving before it
            continue
        if GATE and heel is not None and heel.size and np.any((t - heel >= -0.01) & (t - heel <= GATE)):
            continue
        kind = "person"
        post = u[i + 1:i + 1 + int(0.5 * FS)]
        pre = u[max(0, i - int(0.5 * FS)):i]
        if post.size > 50 and abs(np.mean(post)) < max(4 * rms, 0.03 * abs(di)) and np.std(post) < 4 * rms + 0.03 * abs(di):
            kind = "earthed"                                 # pulled to, and held at, 0 V [physics; DC-coupled input E]
        u0 = np.mean(u[max(0, i - 25):i])                      # her voltage just before (as the watch sees it)
        if kind == "person" and abs(u0) > 10 * rms and -OBJECT_FRAC < di / u0 < 0:
            kind = "object"                                  # small pull toward 0 V: phone, bag, keys (4-12 pF)
        if indoor and hum is not None:
            h0, h1 = np.mean(hum[max(0, i - FS // 2):i + 1]), np.mean(hum[i + 1:i + 1 + FS // 2])
            if h0 > 0 and h1 < 0.3 * h0:
                kind = "earthed"
        out.append((t, float(di), kind))
        last = t
    return out


def agitation(t_imu, acc, t0, heel=None):
    """Jerks of |a - 1 g| > AGIT_G within 3 s after t0, not on a heel strike."""
    sel = (t_imu >= t0) & (t_imu <= t0 + 3.0)
    x = np.abs(acc[sel] - 1.0) > AGIT_G
    jerks = np.sum(np.diff(x.astype(int)) == 1)
    return jerks >= AGIT_N
