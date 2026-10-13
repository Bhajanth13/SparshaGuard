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
// Then the product's state machine: 15 s PIN window; correct PIN cancels, wrong PIN or no PIN
// alerts, the duress PIN shows "Cancelled" but alerts silently.
(function (root) {
  const FS = 5;
  const CFG = {
    T_ENTER: 0.003, EXIT_RATIO: 0.5, SUSTAIN_S: 2, TAU_BASE_S: 60, MAX_FREEZE_S: 30, LEARN_S: 5,
    OFF_WRIST_TOL: 0.004, OFF_WRIST_FRAMES: 3, PIN_WINDOW_S: 15, PIN: "1234", DURESS_PIN: "9999",
  };

  const rmsDiff = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) { const d = a[i] - b[i]; s += d * d; } return Math.sqrt(s / a.length); };

  class Firmware {
    constructor(offWristRef, cfg = {}) {
      this.cfg = Object.assign({}, CFG, cfg);
      this.offRef = offWristRef;
      this.t = 0;                     // frames since power-on
      this.state = "off";             // off | learning | armed | prompt | alert
      this.log = [];
      this.silentAlert = false;
      this._reset();
    }
    _reset() {
      this.base = null; this.learn = []; this.active = false; this.count = 0; this.frozen = 0;
      this.prompted = false; this.offCount = 0; this.score = 0; this.offDist = 1;
    }
    _emit(type, text) { const e = { t: this.t / FS, type, text }; this.log.push(e); this.onEvent && this.onEvent(e); }

    setGuard(on) {
      if (on && this.state === "off") { this._reset(); this.state = "learning"; this.silentAlert = false;
        this._emit("info", "Guard Mode on: learning her baseline for 5 s"); }
      if (!on && this.state !== "off") { this.state = "off"; this._emit("info", "Guard Mode off"); }
    }

    frame(amp) {
      this.t += 1;
      const c = this.cfg;
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
      if (!this.active && sc > c.T_ENTER) { this.active = true; this.count = 0; this.frozen = 0; this.prompted = false;
        this._emit("touch", `Change ${(100 * sc).toFixed(2)} % > 0.3 %: possible touch, baseline frozen`); }
      else if (this.active && sc < c.EXIT_RATIO * c.T_ENTER) { this.active = false;
        if (!this.prompted) this._emit("info", `Change back below 0.15 % after ${(this.count / FS).toFixed(1)} s: ignored`); }
      if (this.active) {
        this.frozen += 1; this.count += 1;
        if (this.count >= c.SUSTAIN_S * FS && !this.prompted) { this.prompted = true; this._startPrompt(); }
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

    _startPrompt() {
      if (this.state !== "armed") return;
      this.state = "prompt"; this.pinLeft = this.cfg.PIN_WINDOW_S * FS; this.entry = "";
      this._emit("prompt", "Touch held 2 s: vibrate, ask for PIN (15 s)");
    }
    _tickPrompt() {
      if (this.state !== "prompt") return;
      this.pinLeft -= 1;
      if (this.pinLeft <= 0) this._alert("No PIN within 15 s");
    }
    get pinSecondsLeft() { return this.state === "prompt" ? Math.ceil(this.pinLeft / FS) : 0; }
    get holdSeconds() { return this.active ? this.count / FS : 0; }

    pressKey(k) {
      if (this.state !== "prompt") return;
      if (k === "del") { this.entry = this.entry.slice(0, -1); return; }
      if (this.entry.length < 4) this.entry += k;
      if (this.entry.length === 4) this.submitPin(this.entry);
    }
    submitPin(pin) {
      if (this.state !== "prompt") return;
      if (pin === this.cfg.PIN) { this.state = "armed"; this._emit("cancel", "Correct PIN: cancelled, still guarding"); }
      else if (pin === this.cfg.DURESS_PIN) {
        this.state = "armed"; this.silentAlert = true;
        this._emit("cancel", "Screen shows \"Cancelled\"");
        this._emit("silent", "Duress PIN: SMS + GPS sent and 112 called silently");
      } else this._alert("Wrong PIN");
      this.entry = "";
    }
    _alert(why) {
      if (this.state === "alert") return;
      this.state = "alert";
      this._emit("alert", `${why}: SMS + GPS to contacts, calling 112, recording audio`);
    }
  }

  const api = { Firmware, CFG, FS };
  if (typeof module !== "undefined") module.exports = api; else root.SGFirmware = api;
})(this);
