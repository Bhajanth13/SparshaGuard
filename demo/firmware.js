// SparshaGuard Guard Mode logic, fed one sensor frame at a time.
//
// Target (flagship architecture, ANVAYA 2k26 design): this is the code of the SAFETY CORE, an
// nRF5340 running Zephyr ("SparshaOS"), which owns the sensing front end (AD9833 sweep, bootstrapped
// input + ADS1115 static channel, BMI270 IMU, EDA, PPG) and the 4G VoLTE + GNSS modem. The app
// processor (STM32U5G9, display and apps) only draws the PIN screen and forwards key presses, so a
// frozen app can never block an alert. The same file runs unchanged in the digital twin and in
// the headless check (demo/check_demo.js).
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
// New channels, rule F2 (default since 28 Oct 2026; sg_newch.py, passive_stream.py):
//   transmit check  a static step that lands at the same instant as a jump in the 100 kHz transmit
//                   current, and matches the k change that jump predicts, is her own hand on the
//                   watch, never a person
//   EDA path        a person step with no pulling still prompts if, 0.8-4.5 s later, her skin
//                   conductance rises by at least 0.45 uS (no faster than 1 uS/s, not during an arm
//                   jerk): a grab that holds her while she freezes
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
// Who can switch Guard Mode off: only someone who knows her PIN (setGuard(false, pin)). While a PIN
// prompt is running it cannot be switched off at all; a wrong PIN on the off screen starts the 15 s
// PIN prompt; the duress PIN shows "Guard Mode off" but alerts silently and keeps guarding. After a
// duress alert the watch keeps recording silently and does not prompt again (that would show the
// attacker a second prompt). An alert ends only with her real PIN; contacts are told she is safe.
// Strap removal is checked from the moment Guard Mode is on, including the 5 s of learning.
// PINs are set by her (setPins), 4 digits, the duress PIN different from the real one.
(function (root) {
  const FS = 5;
  const CFG = {
    T_ENTER: 0.003, EXIT_RATIO: 0.5, SUSTAIN_S: 2, TAU_BASE_S: 60, MAX_FREEZE_S: 30, LEARN_S: 5,
    OFF_WRIST_TOL: 0.004, OFF_WRIST_FRAMES: 3, PIN_WINDOW_S: 15, PIN: "1234", DURESS_PIN: "9999",
    RULE: "fused2",           // "fused2" (rule F2, default), "fused" (rule F of 14 Oct) or "active" (rule A: active sweep alone)
    PFS: 500, IMU_FS: 50, STEP_K: 6, SETTLE: 0.3, LOCAL_K: 8, OBJECT_FRAC: 0.12,
    PERSON_BEFORE_S: 4, AGIT_G: 1.25, AGIT_N: 2, AGIT_S: 3,
    TX_JUMP: 0.02, EDA_TH: 0.45, EDA_LO: 0.8, EDA_HI: 4.5, EDA_MAX_RATE: 1.0,
    RUN_ENMO: 0.45, RUN_HOLD_S: 10, STRUGGLE_G: 2.0, STRUGGLE_N: 5, STRUGGLE_CV: 0.35, STRUGGLE_GYRO: 400, MOTION_S: 4, PERIODIC: 0.5,
  };
  const median = (a) => { const b = Float64Array.from(a).sort(), m = b.length >> 1; return b.length % 2 ? b[m] : (b[m - 1] + b[m]) / 2; };
  const mean = (a, i0, i1) => { let s = 0; for (let i = i0; i < i1; i++) s += a[i]; return s / (i1 - i0); };

  // contact-step detector on a stream (port of sg_passive.contact_steps); decides 0.5 s late
  class StepDetector {
    constructor(c) { this.c = c; this.u = []; this.hum = []; this.tx = []; this.off = 0; this.next = 0; this.last = -10; this.indoor = false; this.rms = 5e-4; }
    // port of sg_newch.tx_says_own_hand: did the transmit current jump with this step, and does the
    // step match the k change that jump predicts (her own hand, no charge moved)?
    ownHand(g, rms, gain) {
      const o = this.off, seg = (a, b) => median(this.tx.slice(a - o, b - o)), useg = (a, b) => median(this.u.slice(a - o, b - o));
      if (g - 20 < o || g + 22 > o + this.tx.length) return null;
      const jump = seg(g + 6, g + 22) / seg(g - 20, g - 4) - 1;
      if (Math.abs(jump) < this.c.TX_JUMP) return null;
      const u0 = useg(g - 20, g - 4), u1 = useg(g + 6, g + 22), rho = 1 / (1 + jump * gain), pred = (rho - 1) * u0;
      return Math.abs((u1 - u0) - pred) < 0.25 * Math.abs(pred) + 6 * rms ? jump : null;
    }
    push(p) {
      for (let i = 0; i < p.u.length; i++) { this.u.push(p.u[i]); this.hum.push(p.hum[i]); this.tx.push(p.tx ? p.tx[i] : 1); }
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
        let txJump = null;
        if (kind === "person" && p.tx && (txJump = this.ownHand(i, rms, p.txGain ?? 1)) !== null) kind = "self";
        out.push({ t, size: di, kind, u0, txJump });
        this.last = t;
      }
      const keep = 3 * FSP;                                    // keep the last 3 s
      if (u.length > keep) { const cut = u.length - keep; this.u = u.slice(cut); this.hum = this.hum.slice(cut); this.tx = this.tx.slice(cut); this.off += cut; }
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
      this.eda = [];                  // [t, skin conductance uS] over the last 12 s
      this.hrHist = []; this.hr = null; this.runningUntil = -1; this.motionQuiet = -1; this.mic = null;
      this.passiveSeen = false;
      this.pin = this.cfg.PIN; this.duressPin = this.cfg.DURESS_PIN;
      this.screen = null;             // what the watch face shows when it differs from the state (duress)
      this._reset();
    }
    _reset() {
      this.base = null; this.learn = []; this.active = false; this.count = 0; this.frozen = 0;
      this.prompted = false; this.offCount = 0; this.score = 0; this.offDist = 1; this.pendingPrompt = null;
      this.personSteps = []; this.lastStep = null; this.watching = null; this.holdStart = 0; this.vetoed = false;
    }
    _emit(type, text) { const e = { t: this.t / FS, type, text }; this.log.push(e); this.onEvent && this.onEvent(e); }

    // her own PINs; returns false (and changes nothing) if they are not two different 4-digit codes
    setPins(pin, duress) {
      const ok = (p) => /^[0-9]{4}$/.test(p);
      if (!ok(pin) || !ok(duress) || pin === duress) return false;
      this.pin = pin; this.duressPin = duress; return true;
    }

    // switching on needs nothing; switching off needs her PIN (see the header)
    setGuard(on, pin) {
      if (on) {
        if (this.state !== "off") { if (this.screen === "off") this.screen = null; return true; }
        this._reset(); this.state = "learning"; this.silentAlert = false; this.screen = null; this.offCount = 0;
        this._emit("info", "Guard Mode on: learning her baseline for 5 s");
        return true;
      }
      if (this.state === "off") return true;
      if (this.state === "prompt") { this._emit("info", "Guard Mode cannot be switched off during a PIN prompt: answer the prompt"); return false; }
      if (pin === this.pin) {
        if (this.state === "alert") this._emit("cancel", "Alert ended with her PIN: contacts told she is safe; recording kept");
        this.state = "off"; this.silentAlert = false; this.screen = null; this.mic = null;
        this._emit("info", "Guard Mode off (her PIN)");
        return true;
      }
      if (pin === this.duressPin) {
        this.screen = "off";
        if (this.state !== "alert" && !this.silentAlert) {
          this.silentAlert = true; this.mic = this.mic || { start: this.t / FS };
          this._emit("silent", `Duress PIN on the off screen: screen shows "Guard Mode off"; SMS + GPS + voice recording sent and 112 called silently${this._hrText()}`);
        }
        return false;
      }
      if (this.state === "alert") { this._emit("info", "Wrong PIN: the alert continues"); return false; }
      this._emit("touch", "Wrong PIN on the off screen");
      const why = "Wrong PIN to switch Guard Mode off: ask for her PIN (15 s)";
      if (this.state === "learning") this.pendingPrompt = why;    // prompts as soon as the baseline is learnt
      else this._startPrompt(why);
      return false;
    }
    _learnedBase() {
      if (!this.learn.length) return null;
      const b = new Float64Array(this.learn[0].length);
      for (const a of this.learn) for (let i = 0; i < a.length; i++) b[i] += a[i] / this.learn.length;
      return b;
    }

    get fused() { return (this.cfg.RULE === "fused" || this.cfg.RULE === "fused2") && this.passiveSeen; }
    get f2() { return this.cfg.RULE === "fused2"; }

    // the passive channel and accelerometer of this frame (optional: without them the watch runs rule A)
    _passive(p) {
      const c = this.cfg, now = this.t / FS;
      this.passiveSeen = true;
      const n = p.acc.length;
      for (let i = 0; i < n; i++) this.imu.push([now - (n - 1 - i) / c.IMU_FS, p.acc[i], p.gyro ? p.gyro[i] : 0]);
      if (p.hr) { this.hr = p.hr; this.hrHist.push(p.hr); if (this.hrHist.length > 120 * FS) this.hrHist.shift(); }
      if (p.eda !== undefined) { this.eda.push([now, p.eda]); while (this.eda.length && this.eda[0][0] < now - 12) this.eda.shift(); }
      this.txNow = p.tx ? median(p.tx) : 1;
      while (this.imu.length && this.imu[0][0] < now - 5) this.imu.shift();
      const guarding = this.state === "armed";
      for (const s of this.steps.push(this.f2 ? p : Object.assign({}, p, { tx: null }))) {
        this.lastStep = s;
        if (!guarding) continue;
        const v = `${(1000 * Math.abs(s.size)).toFixed(0)} mV`;
        if (s.kind === "self") this._emit("info", `Static step (${v}) at the same instant the transmit current jumped ${(100 * s.txJump).toFixed(0)} %: her own hand on the watch, not a person`);
        else if (s.kind === "earthed") this._emit("info", `Static: her body pulled to 0 V (${v} step), metal or earth: not a person`);
        else if (s.kind === "object") this._emit("info", `Static: small pull toward 0 V (${v}), a phone or bag: not a person`);
        else {
          this.personSteps.push(s.t);
          this._emit("touch", `Static: charge-sharing step ${v} in under 2 ms: another body touched her`);
          if (this.fused && now < this.runningUntil) {
            this.prompted = true; this._startPrompt("Another body touched her while she was running: ask for PIN (15 s)"); continue;
          }
          if (this.fused && !this.watching) { this.watching = s.t; this.saidNoPull = false; this._emit("info", "Watching her arm for 3 s and her skin for 4.5 s: is she being pulled, or frozen with fear?"); }
        }
      }
      this.personSteps = this.personSteps.filter((t) => t > now - 10);
      if (this.fused) this._motion(now, guarding);
      if (this.watching !== null) {
        const jerks = this.jerksSince(this.watching);
        if (guarding && this.fused && jerks >= c.AGIT_N) {
          this.watching = null; this.prompted = true;
          this._startPrompt(`Another person touched her and her arm was pulled (${jerks} jerks): ask for PIN (15 s)`);
        } else if (guarding && this.f2 && this.scrSince(this.watching) !== null) {
          const a = this.scrSince(this.watching); this.watching = null; this.prompted = true;
          this._startPrompt(`Another person touched her and her skin responded ${(a).toFixed(2)} µS (fear sweat, no pulling: she may be frozen): ask for PIN (15 s)`);
        } else if (now > this.watching + (this.f2 ? c.EDA_HI + 3 : c.AGIT_S)) {
          this._emit("info", this.f2 ? "No pulling and no strong skin response: a brush, ignored" : "No pulling within 3 s: a brush, ignored"); this.watching = null;
        } else if (this.f2 && !this.saidNoPull && now > this.watching + c.AGIT_S) {
          this.saidNoPull = true; this._emit("info", "No pulling within 3 s; watching her skin response (EDA)");
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

    // a skin conductance response starting 0.8-4.5 s after t0 (port of sg_newch.scr_after, on the 5 Hz
    // frame stream): rise of at least EDA_TH uS, no faster than 1 uS/s, at least 0.5 s long, not during an
    // arm jerk; returns its size so far, or null
    scrSince(t0) {
      const c = this.cfg, e = this.eda.filter(([t]) => t >= t0 + c.EDA_LO - 0.6);
      if (e.length < 4) return null;
      const sm = e.map((_, i) => { let s = 0, n = 0; for (let j = Math.max(0, i - 1); j <= Math.min(e.length - 1, i + 1); j++) { s += e[j][1]; n++; } return s / n; });
      let i = 1;
      while (i < sm.length) {
        const d = (sm[i] - sm[i - 1]) * FS;
        if (d > 0.02 && e[i - 1][0] <= t0 + c.EDA_HI && e[i - 1][0] >= t0 + c.EDA_LO - 0.2) {
          let j = i, rate = d;
          while (j + 1 < sm.length && sm[j + 1] > sm[j]) { j++; rate = Math.max(rate, (sm[j] - sm[j - 1]) * FS); }
          const amp = sm[j] - sm[i - 1], ta = e[i - 1][0], tb = e[j][0];
          const jerk = this.imu.some(([t, a]) => t >= ta - 0.5 && t <= tb + 0.5 && Math.abs(a - 1) > c.AGIT_G);   // an arm jerk, not her arm swing
          if (amp >= c.EDA_TH && rate < c.EDA_MAX_RATE && tb - ta >= 0.5 && !jerk) return amp;
          i = j + 1;
        } else i++;
      }
      return null;
    }
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

      // strap removal check (independent of the baseline, so it also runs while learning)
      this.offCount = this.offDist < c.OFF_WRIST_TOL ? this.offCount + 1 : 0;
      if (this.offCount >= c.OFF_WRIST_FRAMES) { this._alert("Strap removed: electrode lost skin contact"); return; }

      if (this.state === "learning") {
        this.learn.push(amp);
        if (this.learn.length >= c.LEARN_S * FS) {
          this.base = this._learnedBase();
          this.state = "armed"; this._emit("info", "Armed: watching for a sustained touch");
          if (this.pendingPrompt) { const w = this.pendingPrompt; this.pendingPrompt = null; this._startPrompt(w); }
        }
        return;
      }

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
      if (this.silentAlert) {                    // already alerting silently after a duress PIN
        this._emit("silent", `${why ? why.replace(/: ask for PIN.*$/, "") : "Touch held 2 s"}: no new prompt (it would show him a second prompt); added to the silent alert`);
        return;
      }
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
      if (pin === this.pin) { this.state = "armed"; this.mic = null; this._emit("cancel", "Correct PIN: cancelled, still guarding; recording deleted"); }
      else if (pin === this.duressPin) {
        this.state = "armed"; this.silentAlert = true; this.screen = "cancelled";
        this._emit("cancel", "Screen shows \"Cancelled\"");
        this._emit("silent", `Duress PIN: SMS + GPS + voice recording sent and 112 called silently${this._hrText()}`);
      } else this._alert("Wrong PIN");
      this.entry = "";
      if (this.state === "armed") this.motionQuiet = this.t / FS + 10;   // the same struggle must not re-prompt right after a cancel
    }
    _alert(why) {
      if (this.state === "alert") return;
      this.state = "alert"; this.screen = null;
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
