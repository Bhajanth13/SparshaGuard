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
    const BARE = { wrist: 0.9, forearm: 0.6, shoulder: 0.1, other_arm: 0.5 };
    if (kind === "person") {
      st.bare = R.p(BARE[detail] ?? 0.5);
      st.clothMm = R.uni(0.16, 0.58) * R.uni(1, 2);             // 1-2 fabric layers [S7]
      if (detail === "wrist") { st.offElectrode = !R.p(0.85); st.handPF = R.uni(0.5, 3); }
      if (detail === "forearm") st.gapCm = R.uni(1, 5);          // grip 1-5 cm from the strap [E]
    }
    if (kind === "strap_off") { st.offSBpF = R.uni(0.05, 0.3); st.offB0pF = R.uni(0.05, 0.5); }
    return st;
  }

  class SensorTwin {
    constructor(SG, opts = {}) {
      this.SG = SG;
      this.R = rng(opts.seed ?? 12);
      this.setContext(opts.context ?? "walking");
      this.hyd = new OU(300, 0.15, this.R);
      this.event = null;
      this.F = SG.TOUCHE;
    }
    setContext(name) {
      this.ctx = CONTEXTS[name]; this.ctxName = name;
      this.gb = new OU(1.0, this.ctx.motion, this.R);
      this.be = new OU(0.5, this.ctx.feet, this.R);
    }
    startEvent(kind, detail) { this.event = drawEvent(kind, detail, this.R); this.event.kind = kind; this.event.detail = detail; }
    endEvent() { this.event = null; }

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
      const v = this._sweep(p, this.event);
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

  const api = { SensorTwin, CONTEXTS, FS, NOISE, DESIGN };
  if (typeof module !== "undefined") module.exports = api; else root.SGSensor = api;
})(this);
