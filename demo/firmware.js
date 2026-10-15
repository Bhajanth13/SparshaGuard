// SparshaGuard watch firmware logic (what would run on the ESP32), fed one sensor frame at a time.
//
// Detection is the pipeline of event_stream.py (run_pipeline, no classifier gate, the
// recommended setting from fig 9):
//   score = RMS over the sweep of (amplitude now - baseline amplitude), fraction of full scale
//   baseline: 5 s start-up average, then follows slow drift (EMA, 60 s) but FREEZES during a
//   suspected touch; re-learns if frozen 30 s without a prompt (e.g. wrist resting on a table)
//   hysteresis: a touch starts above 0.3 % of full scale and ends below 0.15 %
//   a PIN prompt fires when the touch has lasted 2 s
// Strap removal: the sweep is compared with the watch's own "off the wrist" signature (stored at
// the factory); a match for 0.6 s means the electrode has left the skin -> alert at once.
// Passive channel (sg_passive.py, passive_stream.py): the same electrode also reads her body voltage
// at 500 Hz. When another person touches her ANYWHERE, the two bodies share static charge and her
// voltage jumps in under 1 ms. A "contact step" must be sharp (> 6x noise in one sample), settle at
// once, and stand out from the signal's local roughness (her footsteps and arm movements are slower).
// Steps are classed: earthed metal (pulled to and held at 0 V, or the 50 Hz hum gone indoors), a
// small object (pulls her < 12 % toward 0 V: phone, bag), or another person.
// Fused rule F (recommended by passive_stream.py, fig 17):
//   wrist path    the active sweep held 2 s AND a person step within 4 s before the hold began
//   anywhere path a person step AND agitation (>= 2 jerks over 1.25 g on the wrist accelerometer
//                 within 3 s): a grab that pulls or shakes her, anywhere on her body
// Her own hand, a metal pole, a phone or a table make no person step, so they never prompt.
// Signs of assault from her own movement (accelerometer + gyroscope; thresholds are estimates [E]):
//   running        wrist ENMO above 0.45 g for 4 s and periodic (autocorrelation above 0.5 at the
//                  arm-swing period; running is above 600 mg [S43]); while she runs, and 10 s
//                  after, any person step prompts at once
//   struggling     5 or more jerks over 2 g in 4 s, not periodic, at irregular intervals
//                  (CV > 0.35), with the wrist turning faster than 400 deg/s: a PIN prompt even if
//                  no touch was felt (running is periodic and her own gestures are single); paused
//                  until the 4 s window no longer contains running (a window half running, half
//                  not, looks irregular)
//   heart rate     confirmation only: the alert reports it against her usual rate over the last 2 min
//   microphone     turns on at the PIN prompt; deleted on the correct PIN, sent with the alert
//                  (and kept secretly after a duress PIN)
// Then the product's state machine: 15 s PIN window; correct PIN cancels, wrong PIN or no PIN
// alerts, the duress PIN shows "Cancelled" but alerts silently.
(function (root) {
  const FS = 5;
  const CFG = {
    T_ENTER: 0.003, EXIT_RATIO: 0.5, SUSTAIN_S: 2, TAU_BASE_S: 60, MAX_FREEZE_S: 30, LEARN_S: 5,
    OFF_WRIST_TOL: 0.004, OFF_WRIST_FRAMES: 3, PIN_WINDOW_S: 15, PIN: "1234", DURESS_PIN: "9999",
    RULE: "fused",            // "fused" (rule F) or "active" (today's rule A: active sweep alone)
    PFS: 500, IMU_FS: 50, STEP_K: 6, SETTLE: 0.3, LOCAL_K: 8, OBJECT_FRAC: 0.12,
    PERSON_BEFORE_S: 4, AGIT_G: 1.25, AGIT_N: 2, AGIT_S: 3,
    RUN_ENMO: 0.45, RUN_HOLD_S: 10, STRUGGLE_G: 2.0, STRUGGLE_N: 5, STRUGGLE_CV: 0.35, STRUGGLE_GYRO: 400, MOTION_S: 4, PERIODIC: 0.5,
  };
  const median = (a) => { const b = Float64Array.from(a).sort(), m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const mean = (a, i0, i1) => { let s = 0; for (let i = i0; i < i1; i++) s += a[i]; return s / (i1 - i0); };

  // contact-step detector on a stream (port of sg_passive.contact_steps); decides 0.5 s late
  class StepDetector {
    constructor(c) { this.c = c; this.u = []; this.hum = []; this.off = 0; this.next = 0; this.last = -10; this.indoor = false; this.rms = 5e-4; }
    push(p) {
      for (let i = 0; i < p.u.length; i++) { this.u.push(p.u[i]); this.hum.push(p.hum[i]); }
      this.rms = p.rms; this.indoor = p.indoor;
      const out = [], c = this.c, FSP = c.PFS, u = this.u, rms = this.rms, thr = c.STEP_K * rms * Math.SQRT2;
      const N = this.off + u.length, at = (g) => u[g - this.off], d = (g) => at(g + 1) - at(g);
      if (this.next < this.off + 30) this.next = this.off + 30;
      for (; this.next + 252 < N; this.next++) {
        const i = this.next, di = d(i);
        if (Math.abs(di) <= thr) continue;
        const t = (i + 1) / FSP;
        if (t - this.last < 0.25) continue;
        if (Math.abs(at(i + 16) - at(i + 1)) > c.SETTLE * Math.abs(di) + 4 * rms) continue;   // still moving 30 ms later
        const around = []; for (let j = i - 25; j < i - 2; j++) around.push(d(j)); for (let j = i + 3; j < i + 26; j++) around.push(d(j));
        const md = median(around), rough = 1.4826 * median(around.map((x) => Math.abs(x - md)));
        if (Math.abs(at(i + 2) - at(i - 1)) < c.LOCAL_K * rough) continue;           // rough signal: her own movement
        if (Math.abs(at(i) - at(i - 7)) > c.SETTLE * Math.abs(di) + 4 * rms) continue; // already moving before
        let kind = "person";
        let pm = 0, ps = 0; for (let j = i + 1; j < i + 251; j++) pm += at(j); pm /= 250;
        for (let j = i + 1; j < i + 251; j++) ps += (at(j) - pm) ** 2; ps = Math.sqrt(ps / 250);
        if (Math.abs(pm) < Math.max(4 * rms, 0.03 * Math.abs(di)) && ps < 4 * rms + 0.03 * Math.abs(di)) kind = "earthed";
        let u0 = 0; for (let j = i - 25; j < i; j++) u0 += at(j); u0 /= 25;
        if (kind === "person" && Math.abs(u0) > 10 * rms && di / u0 > -c.OBJECT_FRAC && di / u0 < 0) kind = "object";
        if (this.indoor) {
          const h = this.hum, o = this.off, h0 = mean(h, Math.max(0, i - 250 - o), i + 1 - o), h1 = mean(h, i + 1 - o, i + 251 - o);
          if (h0 > 0 && h1 < 0.3 * h0) kind = "earthed";
        }
        out.push({ t, size: di, kind, u0 });
        this.last = t;
      }
      const keep = 3 * FSP;                                    // keep the last 3 s
      if (u.length > keep) { const cut = u.length - keep; this.u = u.slice(cut); this.hum = this.hum.slice(cut); this.off += cut; }
      return out;
    }
  }

  const rmsDiff = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) { const d = a[i] - b[i]; s += d * d; } return Math.sqrt(s / a.length); };

  class Firmware {
    constructor(offWristRef, cfg = {}) {
      this.cfg = Object.assign({}, CFG, cfg);
      this.offRef = offWristRef;
      this.t = 0;                     // frames since power-on
      this.state = "off";             // off | learning | armed | prompt | alert
      this.log = [];
      this.silentAlert = false;
      this.steps = new StepDetector(this.cfg);
      this.imu = [];                  // [t, |a| in g, |omega| in deg/s] over the last 5 s
      this.hrHist = []; this.hr = null; this.runningUntil = -1; this.motionQuiet = -1; this.mic = null;
      this.passiveSeen = false;
      this._reset();
    }
    _reset() {
      this.base = null; this.learn = []; this.active = false; this.count = 0; this.frozen = 0;
      this.prompted = false; this.offCount = 0; this.score = 0; this.offDist = 1;
      this.personSteps = []; this.lastStep = null; this.watching = null; this.holdStart = 0; this.vetoed = false;
    }
    _emit(type, text) { const e = { t: this.t / FS, type, text }; this.log.push(e); this.onEvent && this.onEvent(e); }

    setGuard(on) {
      if (on && this.state === "off") { this._reset(); this.state = "learning"; this.silentAlert = false;
        this._emit("info", "Guard Mode on: learning her baseline for 5 s"); }
      if (!on && this.state !== "off") { this.state = "off"; this._emit("info", "Guard Mode off"); }
    }

    get fused() { return this.cfg.RULE === "fused" && this.passiveSeen; }

    // the passive channel and accelerometer of this frame (optional: without them the watch runs rule A)
    _passive(p) {
      const c = this.cfg, now = this.t / FS;
      this.passiveSeen = true;
      const n = p.acc.length;
      for (let i = 0; i < n; i++) this.imu.push([now - (n - 1 - i) / c.IMU_FS, p.acc[i], p.gyro ? p.gyro[i] : 0]);
      if (p.hr) { this.hr = p.hr; this.hrHist.push(p.hr); if (this.hrHist.length > 120 * FS) this.hrHist.shift(); }
      while (this.imu.length && this.imu[0][0] < now - 5) this.imu.shift();
      const guarding = this.state === "armed";
      for (const s of this.steps.push(p)) {
        this.lastStep = s;
        if (!guarding) continue;
        const v = `${(1000 * Math.abs(s.size)).toFixed(0)} mV`;
        if (s.kind === "earthed") this._emit("info", `Static: her body pulled to 0 V (${v} step), metal or earth: not a person`);
        else if (s.kind === "object") this._emit("info", `Static: small pull toward 0 V (${v}), a phone or bag: not a person`);
        else {
          this.personSteps.push(s.t);
          this._emit("touch", `Static: charge-sharing step ${v} in under 2 ms: another body touched her`);
          if (this.fused && now < this.runningUntil) {
            this.prompted = true; this._startPrompt("Another body touched her while she was running: ask for PIN (15 s)"); continue;
          }
          if (this.fused && !this.watching) { this.watching = s.t; this._emit("info", "Watching her arm for 3 s: is she being pulled?"); }
        }
      }
      this.personSteps = this.personSteps.filter((t) => t > now - 10);
      if (this.fused) this._motion(now, guarding);
      if (this.watching !== null) {
        const jerks = this.jerksSince(this.watching);
        if (guarding && this.fused && jerks >= c.AGIT_N) {
          this.watching = null; this.prompted = true;
          this._startPrompt(`Another person touched her and her arm was pulled (${jerks} jerks): ask for PIN (15 s)`);
        } else if (now > this.watching + c.AGIT_S) {
          this._emit("info", "No pulling within 3 s: a brush, ignored"); this.watching = null;
        }
      }
    }
    // running and struggling, from the last MOTION_S seconds of accelerometer + gyroscope
    _motion(now, guarding) {
      const c = this.cfg, win = this.imu.filter(([t]) => t > now - c.MOTION_S);
      if (win.length < c.MOTION_S * c.IMU_FS * 0.9) return;
      let enmo = 0, gmax = 0; const edges = []; let prev = null;
      for (const [t, a, g] of win) {
        enmo += Math.max(0, Math.abs(a) - 1); gmax = Math.max(gmax, g);
        const x = Math.abs(a - 1) > c.STRUGGLE_G; if (prev === false && x) edges.push(t); prev = x;
      }
      enmo /= win.length;
      let cv = 0;
      if (edges.length > 2) {
        const d = edges.slice(1).map((t, i) => t - edges[i]), m = d.reduce((s, x) => s + x, 0) / d.length;
        cv = Math.sqrt(d.reduce((s, x) => s + (x - m) ** 2, 0) / d.length) / m;
      }
      // periodicity: the highest autocorrelation of |a| - 1 g at lags of 0.2-0.8 s (arm swing)
      const x = win.map(([, a]) => Math.abs(a) - 1), m = x.reduce((s, v) => s + v, 0) / x.length;
      let r0 = 0; for (const v of x) r0 += (v - m) ** 2;
      let rmax = 0;
      for (let L = Math.round(0.2 * c.IMU_FS); L <= Math.round(0.8 * c.IMU_FS); L++) {
        let r = 0; for (let i = L; i < x.length; i++) r += (x[i] - m) * (x[i - L] - m);
        rmax = Math.max(rmax, r0 > 0 ? r / r0 : 0);
      }
      this.periodicity = rmax;
      const periodic = rmax > c.PERIODIC;
      if (enmo > c.RUN_ENMO && periodic) {
        if (now >= this.runningUntil && guarding) this._emit("info", `Running (wrist motion ${(1000 * enmo).toFixed(0)} mg, regular arm swing): a touch now prompts at once`);
        this.runningUntil = now + c.RUN_HOLD_S; this.lastRunSeen = now;
      }
      if (guarding && now > this.motionQuiet && now > (this.lastRunSeen ?? -99) + c.MOTION_S && !periodic && edges.length >= c.STRUGGLE_N && cv > c.STRUGGLE_CV && gmax > c.STRUGGLE_GYRO) {
        this.motionQuiet = now + 10; this.prompted = true;
        this._startPrompt(`Signs of a struggle: ${edges.length} irregular jerks over 2 g in ${c.MOTION_S} s, wrist turning ${gmax.toFixed(0)} deg/s: ask for PIN (15 s)`);
      }
    }
    get running() { return this.t / FS < this.runningUntil; }
    get hrRest() { if (this.hrHist.length < 10) return null; const s = [...this.hrHist].sort((a, b) => a - b); return s[Math.floor(s.length * 0.2)]; }
    get micOn() { return !!this.mic; }

    jerksSince(t0) {                  // rising edges of |a - 1 g| > 1.25 g in [t0, t0 + 3 s]
      let n = 0, prev = null;
      for (const [t, a] of this.imu) {
        if (t < t0 || t > t0 + this.cfg.AGIT_S) continue;
        const x = Math.abs(a - 1) > this.cfg.AGIT_G;
        if (prev === false && x) n++;
        prev = x;
      }
      return n;
    }

    frame(amp, pas) {
      this.t += 1;
      const c = this.cfg;
      if (pas) this._passive(pas);
      this.offDist = rmsDiff(amp, this.offRef);
      if (this.state === "off" || this.state === "alert") { this.score = this.base ? rmsDiff(amp, this.base) : 0; this._tickPrompt(); return; }

      if (this.state === "learning") {
        this.learn.push(amp);
        if (this.learn.length >= c.LEARN_S * FS) {
          this.base = new Float64Array(amp.length);
          for (const a of this.learn) for (let i = 0; i < a.length; i++) this.base[i] += a[i] / this.learn.length;
          this.state = "armed"; this._emit("info", "Armed: watching for a sustained touch");
        }
        return;
      }

      // strap removal check (independent of the baseline)
      this.offCount = this.offDist < c.OFF_WRIST_TOL ? this.offCount + 1 : 0;
      if (this.offCount >= c.OFF_WRIST_FRAMES) { this._alert("Strap removed: electrode lost skin contact"); return; }

      // touch detection, exactly as run_pipeline in event_stream.py
      const sc = rmsDiff(amp, this.base);
      this.score = sc;
      if (!this.active && sc > c.T_ENTER) { this.active = true; this.count = 0; this.frozen = 0; this.prompted = false; this.vetoed = false; this.holdStart = this.t / FS;
        this._emit("touch", `Change ${(100 * sc).toFixed(2)} % > 0.3 %: possible touch, baseline frozen`); }
      else if (this.active && sc < c.EXIT_RATIO * c.T_ENTER) { this.active = false;
        if (!this.prompted && !this.vetoed) this._emit("info", `Change back below 0.15 % after ${(this.count / FS).toFixed(1)} s: ignored`); }
      if (this.active) {
        this.frozen += 1; this.count += 1;
        if (this.count >= c.SUSTAIN_S * FS && !this.prompted && !this.vetoed) {
          const person = this.personSteps.some((t) => t >= this.holdStart - c.PERSON_BEFORE_S);
          if (!this.fused || person) { this.prompted = true; this._startPrompt(person ? "Touch held 2 s and another body touched her: vibrate, ask for PIN (15 s)" : undefined); }
          else if (this.count >= c.SUSTAIN_S * FS + 3) {                         // allow the 0.5 s static decision
            this.vetoed = true;
            this._emit("info", "Held 2 s but no other body touched her (no static step): her own hand, metal or an object, ignored");
          }
        }
        if (this.frozen > c.MAX_FREEZE_S * FS && !this.prompted) {
          this.base = Float64Array.from(amp); this.active = false;
          this._emit("info", "Change lasted 30 s without a prompt: accepted as the new normal");
        }
      } else {
        const a = 1 / (FS * c.TAU_BASE_S);
        for (let i = 0; i < amp.length; i++) this.base[i] = (1 - a) * this.base[i] + a * amp[i];
      }
      this._tickPrompt();
    }

    _startPrompt(why) {
      if (this.state !== "armed") return;
      this.state = "prompt"; this.pinLeft = this.cfg.PIN_WINDOW_S * FS; this.entry = ""; this.watching = null;
      this._emit("prompt", why || "Touch held 2 s: vibrate, ask for PIN (15 s)");
      this.mic = { start: this.t / FS }; this.motionQuiet = this.t / FS + 10;
      this._emit("info", "Microphone on: recording from the PIN prompt");
    }
    _tickPrompt() {
      if (this.state !== "prompt") return;
      this.pinLeft -= 1;
      if (this.pinLeft <= 0) this._alert("No PIN within 15 s");
    }
    get pinSecondsLeft() { return this.state === "prompt" ? Math.ceil(this.pinLeft / FS) : 0; }
    get holdSeconds() { return this.active ? this.count / FS : 0; }
    // has another body touched her since (4 s before) this hold began? (rule F's wrist path)
    get holdHasPerson() { return this.active && this.personSteps.some((t) => t >= this.holdStart - this.cfg.PERSON_BEFORE_S); }

    pressKey(k) {
      if (this.state !== "prompt") return;
      if (k === "del") { this.entry = this.entry.slice(0, -1); return; }
      if (this.entry.length < 4) this.entry += k;
      if (this.entry.length === 4) this.submitPin(this.entry);
    }
    submitPin(pin) {
      if (this.state !== "prompt") return;
      if (pin === this.cfg.PIN) { this.state = "armed"; this.mic = null; this._emit("cancel", "Correct PIN: cancelled, still guarding; recording deleted"); }
      else if (pin === this.cfg.DURESS_PIN) {
        this.state = "armed"; this.silentAlert = true;
        this._emit("cancel", "Screen shows \"Cancelled\"");
        this._emit("silent", `Duress PIN: SMS + GPS + voice recording sent and 112 called silently${this._hrText()}`);
      } else this._alert("Wrong PIN");
      this.entry = "";
    }
    _alert(why) {
      if (this.state === "alert") return;
      this.state = "alert";
      this._emit("alert", `${why}: SMS + GPS + voice recording (from the PIN prompt) to contacts, calling 112${this._hrText()}`);
    }
    _hrText() {
      const r = this.hrRest;
      return this.hr && r ? `; heart rate ${this.hr.toFixed(0)} bpm (her usual ~${r.toFixed(0)} before this)` : "";
    }
  }

  const api = { Firmware, StepDetector, CFG, FS };
  if (typeof module !== "undefined") module.exports = api; else root.SGFirmware = api;
})(this);
