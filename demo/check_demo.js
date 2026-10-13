// Headless check of the digital twin: runs the same sensor and firmware code as the demo page,
// with no scripting of outcomes, and compares the rates with the Python study (event_stream.py).
//   node demo/check_demo.js          (~3 min)   -> demo/demo_check.json
// 1. Grabs: 120 trials each at the wrist, forearm and shoulder (20 s calm, 10 s grab, 10 s after),
//    as attack_runs() in event_stream.py; a grab counts as caught if the PIN prompt fires during it.
// 2. Daily life: 2 simulated hours per context with the event mix of event_stream.py; counts
//    PIN prompts per hour that nobody wanted (the PIN is never entered here, so each prompt is
//    cancelled at once to keep the hour going).
// 3. Strap removal: 120 trials; and how close normal wearing ever gets to the off-wrist signature.
const SG = require("../explorer/model.js");
const { SensorTwin, FS } = require("./sensor.js");
const { Firmware } = require("./firmware.js");

function grabTrials(detail, n) {
  let caught = 0;
  for (let i = 0; i < n; i++) {
    const ctx = ["walking", "bus", "desk"][i % 3];
    const s = new SensorTwin(SG, { seed: 1000 + i, context: ctx });
    const fw = new Firmware(s.offWristReference());
    fw.setGuard(true);
    let hit = false;
    for (let t = 0; t < 40 * FS; t++) {
      if (t === 20 * FS) detail === "strap_off" ? s.startEvent("strap_off") : s.startEvent("person", detail);
      if (t === 30 * FS) s.endEvent();
      fw.frame(s.frame());
      if (t >= 20 * FS && t <= 30 * FS && (fw.state === "prompt" || fw.state === "alert")) hit = true;
    }
    caught += hit;
  }
  return caught / n;
}

// event mix per context, from event_stream.py: [kind, detail, per hour, min s, max s]
const MIX = {
  walking: [["self", null, 3, 1, 4], ["object", "railing_hand", 4, 3, 10], ["bystander", null, 6, 2, 6],
            ["object", "phone", 6, 30, 120], ["object", "bag", 2, 60, 300]],
  bus: [["object", "railing_wrist", 6, 20, 120], ["object", "railing_hand", 6, 30, 300], ["bystander", null, 30, 5, 60],
        ["person", "shoulder", 10, 1, 3], ["person", "other_arm", 6, 1, 3], ["person", "forearm", 4, 0.5, 2.5],
        ["self", null, 4, 1, 4], ["object", "phone", 6, 30, 200]],
  desk: [["object", "wood_table", 10, 60, 600], ["self", null, 6, 1, 5], ["object", "phone", 10, 30, 200],
         ["person", "wrist", 1, 2, 6]],
};

function poisson(lam, u) { let k = 0, p = Math.exp(-lam), s = p; const x = u(); while (x > s) { k++; p *= lam / k; s += p; } return k; }

function dailyLife(ctx, hours, seed) {
  const s = new SensorTwin(SG, { seed, context: ctx });
  const R = s.R, T = 3600 * FS;
  let prompts = 0, offWristMin = 1, falseStrap = 0;
  const causes = {};
  for (let h = 0; h < hours; h++) {
    const evs = [];
    for (const [kind, detail, rate, dmin, dmax] of MIX[ctx]) {
      const k = poisson(rate, R.u);
      for (let j = 0; j < k; j++) { const d = Math.round(R.uni(dmin, dmax) * FS); const t0 = Math.round(R.uni(10 * FS, T - d - 1)); evs.push({ kind, detail, t0, t1: t0 + d }); }
    }
    evs.sort((a, b) => a.t0 - b.t0);
    const fw = new Firmware(s.offWristReference());
    fw.setGuard(true);
    let cur = null;
    for (let t = 0; t < T; t++) {
      if (cur && t >= cur.t1) { s.endEvent(); cur = null; }
      if (!cur) { const e = evs.find((x) => x.t0 === t || (x.t0 < t && x.t1 > t && !x.done)); if (e && !e.done) { e.done = true; cur = e; s.startEvent(e.kind, e.detail); } }
      const before = fw.state;
      fw.frame(s.frame());
      if (fw.state === "armed" || fw.state === "prompt") offWristMin = Math.min(offWristMin, fw.offDist);
      if (before === "armed" && fw.state === "prompt") {
        prompts++;
        const name = cur ? `${cur.kind}${cur.detail ? ":" + cur.detail : ""}` : "drift / no event";
        causes[name] = (causes[name] || 0) + 1 / hours;
        fw.submitPin("1234");
      }
      if (fw.state === "alert") { falseStrap++; fw.state = "armed"; fw.base = null; fw.setGuard(false); fw.setGuard(true); }
    }
  }
  return { prompts_per_hour: prompts / hours, causes_per_hour: causes, false_strap_alerts: falseStrap, closest_to_off_wrist_pct: 100 * offWristMin };
}

const t0 = Date.now();
const out = { note: "Same code as demo/sparshaguard_demo.html; compare with data/event_stream_results.json (0.3 %, 2 s, no classifier gate)" };
out.grabs_caught = { wrist: grabTrials("wrist", 120), forearm: grabTrials("forearm", 120), shoulder: grabTrials("shoulder", 120) };
out.strap_removal_caught = grabTrials("strap_off", 120);
console.log("grabs", out.grabs_caught, "strap", out.strap_removal_caught, `${((Date.now() - t0) / 1000).toFixed(0)} s`);
out.daily_life = {};
for (const [i, ctx] of ["walking", "bus", "desk"].entries()) { out.daily_life[ctx] = dailyLife(ctx, 2, 77 + i); console.log(ctx, out.daily_life[ctx]); }
const avg = Object.values(out.daily_life).reduce((a, r) => a + r.prompts_per_hour, 0) / 3;
out.mean_prompts_per_hour = avg;
console.log(`mean nuisance prompts per hour ${avg.toFixed(1)}   (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
require("fs").writeFileSync(__dirname + "/demo_check.json", JSON.stringify(out, null, 1));
