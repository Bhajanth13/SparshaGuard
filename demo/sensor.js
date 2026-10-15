// SparshaGuard sensor twin: what the watch's sense circuit would output, frame by frame.
//
// It wraps the circuit model in explorer/model.js (a faithful port of sg_model.py, checked
// against SPICE) and adds what event_stream.py adds in Python:
//   - slow sweat drift (skin hydration, minutes), strap jitter on the wrist coupling (~1 s) and
//     feet lifting while walking (~0.5 s), as Ornstein-Uhlenbeck processes [E, as in event_stream.py]
//   - ADC noise: 0.1 % of full scale per sweep point after averaging 16 sweeps [S15]
//   - per-event random draws over the same ranges as sg_model.py (e.g. a wrist grab lands his palm
//     on the outer electrode 85 % of the time; a forearm grip sits 1-5 cm from the strap)
// The output is amplitude only (200 Touché frequencies), which is all an envelope detector gives.
//
// PassiveTwin adds the second, passive channel on the same electrode (port of sg_passive.py):
// her body voltage from static charge, sampled at 500 Hz, and a wrist accelerometer at 50 Hz.
//   body capacitance 110-250 pF [S4], 0.625x on one foot while walking [S40] (gait timing [S46]);
//   charge leaks with tau = R C_B, R 2e10-1e11 ohm [S18, S40]; walking (1.6-2.3 steps/s [S41])
//   charges her with V_peak = R n dq [S18]; her own movement changes C_B by 2-7 % [S42]; contact shares charge between the two bodies (fabric as
//   a series capacitor [S7, S13]); a charged person nearby induces V_A C_AB/(C_B + C_AB), with
//   C_AB = 21 pF at 1 m [S12]; earthed metal holds her at 0 V and removes the 50 Hz hum indoors
//   [S22]; a phone or bag (4-12 pF) takes a few % of her voltage; the watch sees k = C_GE /
//   (C_GE + C_GB + C_in) of it (bootstrapped input, C_GB 2 pF, C_in 0.5 pF) plus ADS1115 noise
//   (2 mV, rms 0.5 mV) [S15]. The typical body voltage v0 is not yet measured on Indian floors [E].
//   Accelerometer: arm swing at half the step rate [S44], wrist ENMO 140-350 mg [S43]; bus
//   starting/braking 0.1-0.34 g [S45]; gestures and grab jerks are estimates [E].
//   Her own activities (all [E] unless tagged): running, 2.5-3.0 steps/s with wrist ENMO above
//   600 mg [S43]; struggling to get free, irregular jerks of 2-4 g (~2.5 per second) with fast
//   wrist rotation. Gyroscope |omega| in deg/s [E]: arm swing 100-200 walking, 300-600 running,
//   gestures 150-350, pulls 200-500, struggling 400-900. Heart rate [E]: resting 65-85 bpm,
//   +15 walking, +55 running, +30 under stress (a pull or a struggle), rising with a ~20 s and
//   falling with a ~60 s time constant.
// The firmware never sees which scenario is playing, only these numbers.
(function (root) {
  const FS = 5;                  // frames per second; each frame = 16 averaged sweeps
  const NOISE = 1e-3;            // fraction of full scale, as in the Python pipeline
  const DESIGN = "dual_shield";  // the recommended design
  const pF = 1e-12;

  // daily contexts, as in event_stream.py: footwear/floor, strap jitter, feet movement
  const CONTEXTS = {
    walking: { label: "Walking alone at night", env: "street_shoes", motion: 0.015, feet: 0.05 },
    bus: { label: "Bus / metro commute", env: "street_shoes", motion: 0.010, feet: 0.03 },
    desk: { label: "At a desk / home", env: "barefoot_tile", motion: 0.005, feet: 0.01 },
  };

  function rng(seed) {             // mulberry32 + Box-Muller
    let a = seed >>> 0, spare = null;
    const u = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const n = () => { if (spare !== null) { const s = spare; spare = null; return s; }
      let x, y, r; do { x = 2 * u() - 1; y = 2 * u() - 1; r = x * x + y * y; } while (r >= 1 || r === 0);
      const f = Math.sqrt(-2 * Math.log(r) / r); spare = y * f; return x * f; };
    return { u, n, uni: (lo, hi) => lo + (hi - lo) * u(), p: (q) => u() < q };
  }

  class OU {                       // Ornstein-Uhlenbeck, stationary std sigma, time constant tau (s)
    constructor(tau, sigma, R) { this.a = Math.exp(-1 / (FS * tau)); this.s = sigma; this.R = R; this.x = R.n() * sigma; }
    step() { this.x = this.a * this.x + this.s * Math.sqrt(1 - this.a * this.a) * this.R.n(); return this.x; }
  }

  // one event = the sensor-relevant parameters of a touch, drawn like sg_model.py draws them
  function drawEvent(kind, detail, R) {
    const st = { touch: kind, loc: detail, object: detail, bare: true, clothMm: 0.555 };
    const BARE = { wrist: 0.9, forearm: 0.6, upper_arm: 0.3, shoulder: 0.1, other_arm: 0.5, waist: 0.05, face_hair: 0.8 };
    if (kind === "person") {
      st.bare = R.p(BARE[detail] ?? 0.5);
      st.clothMm = R.uni(0.16, 0.58) * R.uni(1, 2);             // 1-2 fabric layers [S7]
      if (detail === "wrist") { st.offElectrode = !R.p(0.85); st.handPF = R.uni(0.5, 3); }
      if (detail === "forearm") st.gapCm = R.uni(1, 5);          // grip 1-5 cm from the strap [E]
      st.pull = false;                                           // a grab that pulls or shakes her arm
    }
    if (kind === "strap_off") { st.offSBpF = R.uni(0.05, 0.3); st.offB0pF = R.uni(0.05, 0.5); }
    return st;
  }


  // ------------------------------------------------------------------ passive channel
  const PFS = 500, IMU_FS = 50, ONE_FOOT = 100 / 160;
  const ACTIVITY = new Set(["run", "struggle"]);       // her own movements, not touches
  const FRONT = { improved: { cgb: 2.0 * pF, cin: 0.5 * pF, adc: 2e-3 }, current: { cgb: 12.4 * pF, cin: 5 * pF, adc: 21.8e-3 } };
  const cAB = (d) => 21 * pF * Math.pow(1 / Math.max(d, 0.15), 0.72);           // [S12]
  const share = (va, vb, ca, cb, cc) => cc ? vb + (va - vb) / (cb * (1 / ca + 1 / cb + 1 / cc)) : (va * ca + vb * cb) / (ca + cb);

  class PassiveTwin {
    constructor(R, ctxName, v0 = 10, front = "improved") {
      this.R = R; this.v0 = v0; this.front = front; this.f = FRONT[front];
      this.cb = R.uni(110, 250) * pF;
      this.cge = Math.exp(R.uni(Math.log(0.6), Math.log(2.0))) * pF;            // [S5/S11]
      this.k = this.cge / (this.cge + this.f.cgb + this.f.cin);
      this.Rg = Math.exp(R.uni(Math.log(2e10), Math.log(1e11)));
      this.cadence = R.uni(1.6, 2.3); this.posture = R.uni(0.02, 0.07); this.enmo = R.uni(0.14, 0.35);
      this.a = Math.exp(-1 / (PFS * this.Rg * this.cb));
      this.lastHeel = -10; this.liftS = 0;
      this.sign = R.p(0.5) ? 1 : -1;
      this.setContext(ctxName, true);
      this.q = this.sign * this.vpeak * this.cb * R.uni(0.3, 1.0);           // charge she already carries
      const am = Math.exp(-1 / (PFS * 0.3));                                    // arm movement: two 0.3 s lags
      this.am = am; this.m1 = 0; this.m2 = 0; this.mnorm = 1 / Math.sqrt(Math.pow(1 - am, 4) * (1 + am * am) / Math.pow(1 - am * am, 3));
      this.inj = [];                                                            // charge being separated [{left, per}]
      this.app = null; this.pinned = false; this.small = null; this.hum = 1;
      this.sway = 0; this.phase = R.uni(0, 6.3); this.pulses = []; this.n = 0; this.ni = 0;
      this.running = false; this.struggling = false; this.stress = 0;
      this.runCad = R.uni(2.5, 3.0); this.runEnmo = R.uni(0.6, 1.0);
      this.swing = R.uni(100, 200); this.hrRest = R.uni(65, 85); this.hr = this.hrRest + 10;
    }
    setContext(name, first) {
      this.ctxName = name; this.walking = name === "walking"; this.indoor = name === "desk";
      if (first || this.vpeak === undefined) this.vpeak0 = this.v0 * Math.exp(0.7 * this.R.n());
      this.vpeak = name === "desk" ? 0.1 * this.vpeak0 : this.vpeak0;
      // start walking from double support (both feet down), so C_B changes smoothly
      if (this.walking && this.cadence) { this.lastHeel = this.n / PFS - 0.1 * 2 / this.cadence; this.nextHeel = this.lastHeel + 1 / this.cadence; }
      else this.nextHeel = this.n / PFS + this.R.uni(0, 1 / (this.cadence || 2));
    }
    setV0(v0) { this.v0 = v0; this.setContext(this.ctxName, true); }
    strangerVoltage() { return this.v0 * Math.exp(0.7 * this.R.n()) * (this.R.p(0.5) ? 1 : -1); }

    start(ev) {                                                                 // ev: the drawn event of SensorTwin
      const R = this.R, vb = this.q / this.cb;
      this.contact = ev;
      if (ev.kind === "person") {
        const va = ev.vA ?? this.strangerVoltage();
        const cc = ev.bare ? null : 8.854e-12 * R.uni(1.2, 5.1) * R.uni(40, 80) * 1e-4 / (R.uni(0.16e-3, 0.58e-3) * R.uni(1, 2));
        this.q = share(va, vb, R.uni(110, 250) * pF, this.cb, cc) * this.cb;
        this.hum = R.uni(0.6, 1.6);
        if (ev.pull) {                                                          // 2-5 jerks of 1.5-3 g in 3 s [E]
          const times = ev.pullTimes || Array.from({ length: 2 + Math.floor(R.u() * 4) }, () => R.uni(0.2, 3.0));
          for (const tj of times) this.pulses.push({ at: this.ni + Math.round(tj * IMU_FS), w: Math.round(0.15 * IMU_FS), g: R.uni(1.5, 3.0), gy: R.uni(200, 500) });
          this.stress = 30;
        }
      } else if (ev.kind === "run") {
        this.running = true;
      } else if (ev.kind === "struggle") {
        this.struggling = true; this.stress = 30;
      } else if (ev.kind === "bystander") {
        this.app = { va: this.strangerVoltage(), dmin: R.uni(0.2, 0.6), s: 0, leaving: false };
      } else if (ev.kind === "object" && /railing|pole|metal/.test(ev.detail || "")) {
        this.pinned = true; this.q = 0; this.hum = 0.05;
      } else if (ev.kind === "object" && /phone|bag|keys/.test(ev.detail || "")) {
        this.q = share(0, vb, R.uni(4, 12) * pF, this.cb) * this.cb;
      }
    }
    end() {
      if (this.pinned) { this.pinned = false; this.q = -this._vind() * this.cb * this._cm; }   // keeps the charge that cancelled vind
      if (this.app) { this.app.leaving = true; this.app.s = 0; }
      this.hum = 1; this.contact = null; this.running = false; this.struggling = false;
    }
    _vind() {
      const A = this.app; if (!A) return 0;
      const r = PFS, x = Math.min(1, A.s / r);
      const d = A.leaving ? A.dmin + (3 - A.dmin) * x : 3 + (A.dmin - 3) * x;
      const c = cAB(d) - cAB(3.0);
      return A.va * c / (this.cb + c);
    }
    // one firmware frame (0.2 s): 100 passive samples, 10 accelerometer samples
    frame(nP = PFS / FS) {
      const R = this.R, u = new Float64Array(nP), hum = new Float64Array(nP), rms = this.f.adc / 4;
      const dq = this.sign * this.vpeak / (this.Rg * this.cadence), stride = 2 / this.cadence;
      for (let i = 0; i < nP; i++, this.n++) {
        const t = this.n / PFS;
        if (this.walking && t >= this.nextHeel) { const w = Math.round(R.uni(0.02, 0.06) * PFS); this.inj.push({ left: w, per: dq / w }); this.lastHeel = this.nextHeel; this.nextHeel += 1 / this.cadence; }
        if (this.ctxName === "bus" && R.u() < 0.2 / PFS) { const w = Math.round(R.uni(0.02, 0.06) * PFS); this.inj.push({ left: w, per: dq / w }); }
        let add = 0; for (const s of this.inj) { add += s.per; s.left--; }
        this.inj = this.inj.filter((s) => s.left > 0);
        this.q = this.pinned ? 0 : this.a * this.q + add;
        this.m1 = this.am * this.m1 + (1 - this.am) * R.n(); this.m2 = this.am * this.m2 + (1 - this.am) * this.m1;
        let lift = 1;                                                           // landing 0-10 %, lift-off 10-20 % of the stride [S46]
        if (this.walking) { const x = (t - this.lastHeel) / stride; if (x < 0.1) lift = 1 - x / 0.1; else if (x < 0.2) lift = (x - 0.1) / 0.1; }
        else lift = 0;
        this.liftS += (lift - this.liftS) / (0.03 * PFS);                       // feet move over tens of ms, never in one sample
        lift = this.liftS;
        this._cm = (1 + this.posture * this.m2 * this.mnorm) * (1 - (1 - ONE_FOOT) * lift);   // [S40, S42]
        if (this.app) { this.app.s++; if (this.app.leaving && this.app.s >= PFS) this.app = null; }
        const v = this.pinned ? 0 : this.q / (this.cb * this._cm) + this._vind();
        u[i] = this.k * v + rms * R.n();
        hum[i] = this.indoor ? this.hum : 0;
      }
      const nI = IMU_FS / FS, acc = new Float64Array(nI), gyro = new Float64Array(nI);
      const sw = { walking: 0.05, bus: 0.10, desk: 0.02 }[this.ctxName], ai = Math.exp(-1 / IMU_FS);
      for (let i = 0; i < nI; i++, this.ni++) {
        const t = this.ni / IMU_FS;
        this.sway = ai * this.sway + Math.sqrt(1 - Math.exp(-2 / IMU_FS)) * sw * R.n();
        const ph = Math.sin((this.running ? this.runCad : this.cadence) * Math.PI * t + this.phase);
        let a = 1 + this.sway, w = Math.abs(this.sway) * 100 + 5 * Math.abs(R.n());
        if (this.running) { a += Math.PI * this.runEnmo * ph; w += 450 * Math.abs(ph); }         // [S43 / E]
        else if (this.walking) { a += Math.PI * this.enmo * ph; w += this.swing * Math.abs(ph); }  // [S43, S44 / E]
        if (R.u() < 15 / 3600 / IMU_FS) this.pulses.push({ at: this.ni, w: Math.round(R.uni(0.2, 0.4) * IMU_FS), g: R.uni(1.0, 2.2), gy: R.uni(150, 350) });   // her own gestures [E]
        if (this.ctxName === "bus" && R.u() < 12 / 3600 / IMU_FS) this.pulses.push({ at: this.ni, w: 15, g: R.uni(0.1, 0.34), gy: 20 });   // starting/braking [S45], 12/h [E]
        if (this.struggling && R.u() < 2.5 / IMU_FS) this.pulses.push({ at: this.ni, w: Math.round(R.uni(0.08, 0.2) * IMU_FS), g: R.uni(2, 4), gy: R.uni(400, 900) });   // [E]
        for (const p of this.pulses) { const j = this.ni - p.at; if (j >= 0 && j < p.w) { const k = 0.5 * (1 - Math.cos(2 * Math.PI * j / Math.max(1, p.w - 1))); a += p.g * k; w = Math.max(w, (p.gy || 0) * k); } }
        this.pulses = this.pulses.filter((p) => this.ni - p.at < p.w);
        acc[i] = a; gyro[i] = w;
      }
      // heart rate, once per frame [E]
      const target = this.hrRest + (this.running ? 55 : this.walking ? 15 : 0) + this.stress;
      this.hr += (target - this.hr) * (1 / FS) / (target > this.hr ? 20 : 60);
      this.stress *= Math.exp(-1 / (FS * 120));
      if (this.struggling) this.stress = 30;
      return { u, hum, acc, gyro, hr: this.hr, rms, indoor: this.indoor };
    }
  }

  class SensorTwin {
    constructor(SG, opts = {}) {
      this.SG = SG;
      this.R = rng(opts.seed ?? 12);
      this.setContext(opts.context ?? "walking");
      this.hyd = new OU(300, 0.15, this.R);
      this.event = null;
      this.F = SG.TOUCHE;
      this.passive = new PassiveTwin(this.R, this.ctxName, opts.v0 ?? 10, opts.front ?? "improved");
    }
    setContext(name) {
      this.ctx = CONTEXTS[name]; this.ctxName = name;
      if (this.passive) this.passive.setContext(name);
      this.gb = new OU(1.0, this.ctx.motion, this.R);
      this.be = new OU(0.5, this.ctx.feet, this.R);
    }
    // force: values that override the random draw (e.g. { pull: true } for a grab that pulls her arm)
    startEvent(kind, detail, force) {
      this.event = drawEvent(kind, detail, this.R); this.event.kind = kind; this.event.detail = detail;
      if (force) Object.assign(this.event, force);
      this.passive.start(this.event);
    }
    endEvent() { if (this.event) this.passive.end(); this.event = null; }
    passiveFrame() { return this.passive.frame(); }

    // complex sense-node voltage for parameter set p and touch state st (or none)
    _sweep(p, st) {
      const SG = this.SG, out = new Array(this.F.length);
      const full = Object.assign({ design: DESIGN, env: this.ctx.env, hyd: p.hyd }, st || { touch: "none" });
      for (let i = 0; i < this.F.length; i++) out[i] = SG.solve(SG.branches(this.F[i], p, full, !!st));
      return out;
    }

    frame() {                      // -> Float64Array of 200 amplitudes, fraction of full scale
      const SG = this.SG;
      const p = SG.base({ design: DESIGN, env: this.ctx.env, hyd: 0.5 });
      p.hyd = Math.min(1, Math.max(0, 0.5 + this.hyd.step()));
      p.C_GB *= 1 + this.gb.step();
      p.C_BE *= Math.exp(this.be.step());
      const touch = this.event && !ACTIVITY.has(this.event.kind) ? this.event : null;   // running or struggling is not a touch
      const v = this._sweep(p, touch);
      const out = new Float64Array(v.length);
      for (let i = 0; i < v.length; i++)
        out[i] = Math.hypot(v[i].re + NOISE * this.R.n(), v[i].im + NOISE * this.R.n());
      return out;
    }

    // the watch alone in free air: what the factory would store as the "off the wrist" signature
    offWristReference() {
      const p = this.SG.base({ design: DESIGN, env: this.ctx.env, hyd: 0.5 });
      const v = this._sweep(p, { touch: "strap_off", offSBpF: 0, offB0pF: 0 });
      return Float64Array.from(v, (z) => Math.hypot(z.re, z.im));
    }
  }

  const api = { SensorTwin, PassiveTwin, CONTEXTS, FS, NOISE, DESIGN, PFS, IMU_FS, FRONT };
  if (typeof module !== "undefined") module.exports = api; else root.SGSensor = api;
})(this);
