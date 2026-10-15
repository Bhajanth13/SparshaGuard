// Headless check of the digital twin: runs the same sensor and firmware code as the demo page,
// with no scripting of outcomes, and compares the rates with the Python studies (event_stream.py,
// passive_stream.py). Two firmwares watch the same sensor side by side: rule A (active sweep only,
// today) and rule F (fused: active sweep + static channel + accelerometer).
//   node demo/check_demo.js          (~5 min)   -> demo/demo_check.json
// 1. Grabs: 120 trials at each body location (20 s calm, 10 s grab, 10 s after), as attack_runs()
//    in event_stream.py; 70 % of grabs pull her arm [E]; caught if the PIN prompt fires during it.
// 2. Daily life: 2 simulated hours per context with the event mix of event_stream.py; counts
//    PIN prompts per hour that nobody wanted (the PIN is never entered here, so each prompt is
//    cancelled at once to keep the hour going).
// 3. Strap removal: 120 trials; and how close normal wearing ever gets to the off-wrist signature.
const SG = require("../explorer/model.js");
const { SensorTwin, FS } = require("./sensor.js");
const { Firmware } = require("./firmware.js");

const V0 = 10;                     // typical body voltage of each person (V): not yet measured [E]
const RULES = ["active", "fused"];
const pair = (s) => RULES.map((r) => { const f = new Firmware(s.offWristReference(), { RULE: r }); f.setGuard(true); return f; });
function feed(s, fws) { const amp = s.frame(), pas = s.passiveFrame(); for (const f of fws) f.frame(amp, pas); }

function grabTrials(detail, n) {
  const caught = { active: 0, fused: 0 };
  for (let i = 0; i < n; i++) {
    const ctx = ["walking", "bus", "desk"][i % 3];
    const s = new SensorTwin(SG, { seed: 1000 + i, context: ctx, v0: V0 });
    const fws = pair(s), hit = [false, false];
    for (let t = 0; t < 40 * FS; t++) {
      if (t === 20 * FS) detail === "strap_off" ? s.startEvent("strap_off") : s.startEvent("person", detail, { pull: s.R.p(0.7) });
      if (t === 30 * FS) s.endEvent();
      feed(s, fws);
      fws.forEach((f, j) => { if (t >= 20 * FS && t <= 30 * FS && (f.state === "prompt" || f.state === "alert")) hit[j] = true; });
    }
    RULES.forEach((r, j) => (caught[r] += hit[j]));
  }
  return { active: caught.active / n, fused: caught.fused / n };
}

// event mix per context, from event_stream.py: [kind, detail, per hour, min s, max s], or a
// log-normal duration ["logn", median s, mean s, cap s]: her hand on the watch [S38], phone use [S39]
const SELF_D = ["logn", 5, 9, 60], PHONE_D = ["logn", 30, 212, 1800];
const MIX = {
  walking: [["self", null, 3, ...SELF_D], ["object", "railing_hand", 4, 3, 10], ["bystander", null, 6, 2, 6],
            ["object", "phone", 5.3, ...PHONE_D], ["object", "bag", 2, 60, 300],
            ["run", null, 2, 10, 60]],                 // she runs (for a bus, across a road): 2 per hour [E]
  bus: [["object", "railing_wrist", 6, 20, 120], ["object", "railing_hand", 6, 30, 300], ["bystander", null, 30, 5, 60],
        ["person", "shoulder", 10, 1, 3], ["person", "other_arm", 6, 1, 3], ["person", "forearm", 4, 0.5, 2.5],
        ["self", null, 3, ...SELF_D], ["object", "phone", 5.3, ...PHONE_D]],
  desk: [["object", "wood_table", 10, 60, 600], ["self", null, 3, ...SELF_D], ["object", "phone", 5.3, ...PHONE_D],
         ["person", "wrist", 1, 2, 6]],
};
function duration(R, a, b, c, d) { return a === "logn" ? Math.min(d, b * Math.exp(Math.sqrt(2 * Math.log(c / b)) * R.n())) : R.uni(a, b); }

function poisson(lam, u) { let k = 0, p = Math.exp(-lam), s = p; const x = u(); while (x > s) { k++; p *= lam / k; s += p; } return k; }

function dailyLife(ctx, hours, seed) {
  const s = new SensorTwin(SG, { seed, context: ctx, v0: V0 });
  const R = s.R, T = 3600 * FS;
  const prompts = { active: 0, fused: 0 }, friend = { active: 0, fused: 0 };
  let offWristMin = 1, falseStrap = 0;
  const causes = { active: {}, fused: {} };
  for (let h = 0; h < hours; h++) {
    const evs = [];
    for (const [kind, detail, rate, ...dur] of MIX[ctx]) {
      const k = poisson(rate, R.u);
      for (let j = 0; j < k; j++) { const d = Math.max(1, Math.round(duration(R, ...dur) * FS)); const t0 = Math.round(R.uni(10 * FS, T - d - 1)); evs.push({ kind, detail, t0, t1: t0 + d }); }
    }
    evs.sort((a, b) => a.t0 - b.t0);
    const fws = pair(s);
    let cur = null;
    for (let t = 0; t < T; t++) {
      if (cur && t >= cur.t1) { s.endEvent(); cur = null; }
      if (!cur) { const e = evs.find((x) => x.t0 === t || (x.t0 < t && x.t1 > t && !x.done)); if (e && !e.done) { e.done = true; cur = e; s.startEvent(e.kind, e.detail); } }
      const before = fws.map((f) => f.state);
      feed(s, fws);
      fws.forEach((fw, j) => {
        const r = RULES[j];
        if (fw.state === "armed" || fw.state === "prompt") offWristMin = Math.min(offWristMin, fw.offDist);
        if (before[j] === "armed" && fw.state === "prompt") {
          const name = cur ? `${cur.kind}${cur.detail ? ":" + cur.detail : ""}` : "no event (static / motion)";
          if (name === "person:wrist") friend[r]++; else prompts[r]++;   // a friend holding her wrist: the PIN's job
          causes[r][name] = (causes[r][name] || 0) + 1 / hours;
          fw.submitPin("1234");
        }
        if (fw.state === "alert") { falseStrap++; fw.setGuard(false); fw.setGuard(true); }
      });
    }
  }
  const per = (o) => ({ active: o.active / hours, fused: o.fused / hours });
  return { unwanted_prompts_per_hour: per(prompts), friend_wrist_prompts_per_hour: per(friend), causes_per_hour: causes,
           false_strap_alerts: falseStrap, closest_to_off_wrist_pct: 100 * offWristMin };
}

const t0 = Date.now();
const out = { note: "Same code as demo/sparshaguard_demo.html; compare with data/event_stream_results.json (rule A) and data/passive_stream_results.json (rule F, improved input, v0 = 10 V)",
  body_voltage_v0: V0 };
out.grabs_caught = {};
for (const loc of ["wrist", "forearm", "upper_arm", "other_arm", "shoulder", "waist", "face_hair"]) {
  out.grabs_caught[loc] = grabTrials(loc, 120); console.log(loc, out.grabs_caught[loc]);
}
const locs = Object.values(out.grabs_caught);
out.body_average = { active: locs.reduce((a, r) => a + r.active, 0) / locs.length, fused: locs.reduce((a, r) => a + r.fused, 0) / locs.length };
out.strap_removal_caught = grabTrials("strap_off", 120);
// signs of assault from her own movement (digital twin only; thresholds and motions are estimates)
function motionTrials(plan, n) {
  const hit = { active: 0, fused: 0 };
  for (let i = 0; i < n; i++) {
    const s = new SensorTwin(SG, { seed: 3000 + i, context: ["walking", "bus", "desk"][i % 3], v0: V0 });
    const fws = pair(s), got = [false, false];
    for (let t = 0; t < 40 * FS; t++) {
      for (const [at, fn] of plan) if (t === at * FS) fn(s);
      feed(s, fws);
      fws.forEach((f, j) => { if (t >= 20 * FS && (f.state === "prompt" || f.state === "alert")) got[j] = true; });
    }
    RULES.forEach((r, j) => (hit[r] += got[j]));
  }
  return { active: hit.active / n, fused: hit.fused / n };
}
out.struggle_without_touch_caught = motionTrials([[20, (s) => s.startEvent("struggle")], [26, (s) => s.endEvent()]], 120);
out.running_alone_prompted = motionTrials([[15, (s) => s.startEvent("run")], [35, (s) => s.endEvent()]], 120);
out.touch_while_running_caught = motionTrials([[15, (s) => s.startEvent("run")], [25, (s) => s.startEvent("person", "shoulder", { pull: false })], [27, (s) => s.endEvent()]], 120);
console.log("struggle", out.struggle_without_touch_caught, "run alone", out.running_alone_prompted, "touch while running", out.touch_while_running_caught);
console.log("body average", out.body_average, "strap", out.strap_removal_caught, `${((Date.now() - t0) / 1000).toFixed(0)} s`);
out.daily_life = {};
for (const [i, ctx] of ["walking", "bus", "desk"].entries()) { out.daily_life[ctx] = dailyLife(ctx, 3, 77 + i); console.log(ctx, JSON.stringify(out.daily_life[ctx])); }
out.mean_unwanted_prompts_per_hour = Object.fromEntries(RULES.map((r) => [r, Object.values(out.daily_life).reduce((a, d) => a + d.unwanted_prompts_per_hour[r], 0) / 3]));
console.log("mean unwanted prompts per hour", out.mean_unwanted_prompts_per_hour, `(${((Date.now() - t0) / 1000).toFixed(0)} s)`);
require("fs").writeFileSync(__dirname + "/demo_check.json", JSON.stringify(out, null, 1));
