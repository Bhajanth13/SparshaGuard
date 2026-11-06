// Tests of the Guard Mode state machine in firmware.js (PIN, duress, switching off, strap removal).
// Run: node demo/test_firmware.js   (about a second; exits 1 on any failure)
// The sensing itself is covered by check_demo.js; here frames are synthetic so each rule is tested alone.
const assert = require("assert");
const { Firmware, FS } = require("./firmware.js");

const N = 200;                                        // sweep points
const OFF = new Float64Array(N).fill(0.5);            // the "off the wrist" signature
const WORN = new Float64Array(N).fill(0.6);           // her wrist, no touch
const TOUCH = new Float64Array(N).fill(0.62);         // +2 % of full scale: a hand at the watch
const run = (fw, amp, seconds) => { for (let i = 0; i < seconds * FS; i++) fw.frame(amp); };
const armedWatch = () => { const fw = new Firmware(OFF, { RULE: "active" }); fw.setGuard(true); run(fw, WORN, 6); assert.strictEqual(fw.state, "armed"); return fw; };
const prompted = () => { const fw = armedWatch(); run(fw, TOUCH, 2.4); assert.strictEqual(fw.state, "prompt"); return fw; };
const typed = (fw, pin) => [...pin].forEach((k) => fw.pressKey(k));
const said = (fw, re) => fw.log.some((e) => re.test(e.text));

const tests = {
  "a 2 s touch prompts and the correct PIN cancels": () => {
    const fw = prompted(); typed(fw, "1234");
    assert.strictEqual(fw.state, "armed"); assert.strictEqual(fw.micOn, false);
  },
  "no PIN in 15 s alerts": () => { const fw = prompted(); run(fw, WORN, 15.2); assert.strictEqual(fw.state, "alert"); },
  "a wrong PIN at the prompt alerts": () => { const fw = prompted(); typed(fw, "1111"); assert.strictEqual(fw.state, "alert"); },
  "the duress PIN shows Cancelled and alerts silently": () => {
    const fw = prompted(); typed(fw, "9999");
    assert.strictEqual(fw.state, "armed"); assert.strictEqual(fw.silentAlert, true); assert.strictEqual(fw.screen, "cancelled");
  },
  "after a duress PIN a new touch does not show him a second prompt": () => {
    const fw = prompted(); typed(fw, "9999"); run(fw, WORN, 3); run(fw, TOUCH, 2.4);
    assert.strictEqual(fw.state, "armed"); assert.ok(said(fw, /no new prompt/));
  },
  "Guard Mode cannot be switched off without her PIN": () => {
    const fw = armedWatch();
    assert.strictEqual(fw.setGuard(false), false); assert.notStrictEqual(fw.state, "off");
  },
  "a wrong PIN on the off screen starts the PIN prompt": () => {
    const fw = armedWatch(); fw.setGuard(false, "5555"); assert.strictEqual(fw.state, "prompt");
  },
  "her PIN switches Guard Mode off": () => { const fw = armedWatch(); assert.strictEqual(fw.setGuard(false, "1234"), true); assert.strictEqual(fw.state, "off"); },
  "the duress PIN on the off screen fakes off and alerts silently": () => {
    const fw = armedWatch(); fw.setGuard(false, "9999");
    assert.strictEqual(fw.state, "armed"); assert.strictEqual(fw.screen, "off"); assert.strictEqual(fw.silentAlert, true);
  },
  "Guard Mode cannot be switched off during a PIN prompt": () => {
    const fw = prompted(); assert.strictEqual(fw.setGuard(false, "1234"), false); assert.strictEqual(fw.state, "prompt");
  },
  "an alert ends only with her PIN": () => {
    const fw = prompted(); typed(fw, "1111");
    fw.setGuard(false, "4321"); assert.strictEqual(fw.state, "alert");
    fw.setGuard(false, "1234"); assert.strictEqual(fw.state, "off"); assert.ok(said(fw, /told she is safe/));
  },
  "a wrong PIN while learning prompts once the baseline is learnt": () => {
    const fw = new Firmware(OFF, { RULE: "active" }); fw.setGuard(true); run(fw, WORN, 1);
    fw.setGuard(false, "5555"); assert.strictEqual(fw.state, "learning");
    run(fw, WORN, 5); assert.strictEqual(fw.state, "prompt");
  },
  "strap removal alerts at once, even while learning": () => {
    const fw = new Firmware(OFF, { RULE: "active" }); fw.setGuard(true); run(fw, WORN, 1); run(fw, OFF, 1);
    assert.strictEqual(fw.state, "alert"); assert.ok(said(fw, /Strap removed/));
  },
  "her own PINs replace the defaults; bad pairs are refused": () => {
    const fw = armedWatch();
    assert.strictEqual(fw.setPins("12a4", "0000"), false); assert.strictEqual(fw.setPins("2580", "2580"), false);
    assert.strictEqual(fw.setPins("2580", "0852"), true);
    run(fw, TOUCH, 2.4); typed(fw, "1234"); assert.strictEqual(fw.state, "alert");   // the old PIN no longer works
  },
};

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log(`ok    ${name}`); } catch (e) { failed++; console.log(`FAIL  ${name}\n      ${e.message}`); }
}
console.log(`${Object.keys(tests).length - failed}/${Object.keys(tests).length} passed`);
process.exit(failed ? 1 : 0);
