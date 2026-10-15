const { execSync } = require("child_process");
const { chromium } = require(execSync("npm root -g").toString().trim() + "/playwright");
const fs = require("fs");
const BASE = "http://localhost:8800";
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: "rec", size: { width: 1920, height: 1080 } },
    timezoneId: "Asia/Kolkata", locale: "en-IN" });
  const pg = await ctx.newPage(); const T0 = Date.now(); const now = () => (Date.now() - T0) / 1000;
  const log = []; const mark = (ev, extra = {}) => log.push({ t: now(), ev, ...extra });
  await pg.route(BASE + "/__wrapper.html", (r) => r.fulfill({ contentType: "text/html", body: fs.readFileSync("wrapper.html", "utf8") }));
  await pg.goto(BASE + "/__wrapper.html");
  const fr = () => pg.frames().find((f) => f.url().includes("sparshaguard_demo"));
  for (let i = 0; i < 50 && !fr(); i++) await pg.waitForTimeout(100);
  const F = fr(); await F.waitForSelector("#status");
  await F.addStyleTag({ content: ".tiles{grid-template-columns:repeat(11,minmax(0,1fr))!important} .tile{padding:8px 4px!important;font-size:12.5px!important}" });
  await pg.waitForTimeout(800);
  const sleep = (s) => pg.waitForTimeout(s * 1000);
  const words = (t) => t.split(/\s+/).length;
  const say = async (t, extra = 0) => { mark("caption", { text: t }); await pg.evaluate((t) => caption(t), t); await sleep(Math.max(0, words(t) / 2.6 + extra)); };
  const sayAsync = async (t) => { mark("caption", { text: t }); await pg.evaluate((t) => caption(t), t); };
  const box = async (sel) => { const bb = await F.locator(sel).first().boundingBox(); return bb; };
  const to = async (sel, ms = 900, dx = 0.5, dy = 0.5) => { const bb = await box(sel); const x = bb.x + bb.width * dx, y = bb.y + bb.height * dy;
    await pg.mouse.move(x, y); await pg.evaluate(([x, y, ms]) => moveCursor(x, y, ms), [x, y, ms]); return [x, y]; };
  const click = async (sel, ms = 900) => { const [x, y] = await to(sel, ms); await sleep(0.25); await pg.evaluate(() => ripple()); await pg.mouse.click(x, y); await sleep(0.2); };
  const status = () => F.$eval("#status", (e) => e.innerText);
  const waitFor = async (pred, max = 30) => { for (let i = 0; i < max * 10; i++) { if (pred(await status())) return; await sleep(0.1); } };
  const typePin = async (pin) => { for (const d of pin) { await click(`.pad button[data-key="${d}"]`, 450); await sleep(0.25); } };
  const statusLog = setInterval(async () => { try { const s = await status(); if (s !== statusLog.last) { statusLog.last = s; mark("status", { text: s }); } } catch (e) {} }, 100);

  // waits that actually take time are marked fast, so the edit can speed them up
  const waitFast = async (pred, max = 30) => { const t = now(); let on = false;
    for (let i = 0; i < max * 10; i++) { if (pred(await status())) break; if (!on && now() - t > 0.4) { mark("fast_on"); on = true; } await sleep(0.1); }
    if (on) mark("fast_off"); };
  mark("start");
  await to(".watch", 1500);
  await say("SparshaGuard's digital twin: the watch's own firmware, running live in Chrome.", 0.4);
  await click("#tab-try", 900);
  await F.evaluate(() => window.scrollTo({ top: 40, behavior: "smooth" }));
  await sayAsync("Guard Mode on: the watch first learns the wearer's body.");
  await to(".watch", 800, 0.5, 0.15);
  await sleep(2.6);
  await waitFast((s) => s.startsWith("Guarding"));
  await to("#cv-score", 900, 0.6, 0.6);
  await say("Guarding. The touch signal stays flat, inside the noise.", 0.3);

  // 1. stranger grabs her wrist -> alert
  await click('.tile[data-k="person:wrist"]', 800);
  await say("A stranger grabs her wrist.", 0.3);
  await to("#cv-score", 800, 0.93, 0.25);
  await say("The touch signal jumps from 0.1 % to 16 %…", 0.2);
  await to("#cv-static", 800, 0.93, 0.4);
  await say("…and her static voltage jumps: another person's body touched her.", 0.2);
  await waitFast((s) => s.startsWith("Enter PIN"));
  await to(".watch", 800, 0.5, 0.3);
  await say("Held 2 seconds: the watch vibrates, asks for a PIN, and the mic turns on.", 0.2);
  await waitFast((s) => s.startsWith("Alert sent"), 20);
  await to(".phone .msg", 1000, 0.5, 0.35);
  await say("No PIN: her location and the voice recording go to her emergency contact. 112 is called.", 0.4);
  await click('.tile[data-k="person:wrist"]', 700);
  await click("#reset", 700);
  await click('#screen button[data-act="on"]', 800);
  await sayAsync("Guard Mode back on.");
  await sleep(1.5); await waitFast((s) => s.startsWith("Guarding"));

  // 2. friend -> PIN 1234
  await click('.tile[data-k="person:wrist"]', 800);
  await say("A friend holds her hand. Every hand is another body to the sensor, so the PIN decides.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"));
  await sayAsync("She types 1234: cancelled, and the recording is deleted.");
  await typePin("1234"); await sleep(1.6);
  await click('.tile[data-k="person:wrist"]', 700); await sleep(0.4);

  // 3. duress
  await click('.tile[data-k="person:wrist"]', 800);
  await sayAsync("Forced to cancel? She types the duress PIN, 9999.");
  await sleep(1.0); await waitFast((s) => s.startsWith("Enter PIN")); await sleep(0.6);
  await typePin("9999");
  await to(".phone .msg", 900, 0.5, 0.3);
  await say("It shows \"Cancelled\", but her emergency contact gets a silent alert.", 0.4);
  await click('.tile[data-k="person:wrist"]', 700); await sleep(0.4);

  // 4. shoulder grab
  await click('.tile[data-k="person:shoulder"]', 800);
  await to("#cv-score", 800, 0.9, 0.7);
  await say("A shoulder grab: the wrist sensor can't feel it…", 0.2);
  await to("#cv-static", 800, 0.92, 0.75);
  await say("…but the static jump and her pulled arm can. PIN prompt.", 0.2);
  await waitFast((s) => s.startsWith("Enter PIN"));
  await sayAsync("She cancels to continue.");
  await typePin("1234"); await sleep(0.6);
  await click('.tile[data-k="person:shoulder"]', 700); await sleep(0.3);

  // 5. struggle
  await click('.tile[data-k="struggle:null"]', 800);
  await to("#cv-static", 800, 0.85, 0.8);
  await say("She struggles to get free: motion sensors see irregular, violent jerks.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"));
  await to(".watch", 700, 0.5, 0.3);
  await say("PIN prompt and mic on, even with no touch felt.", 0.2);
  await typePin("1234"); await sleep(0.4);
  await click('.tile[data-k="struggle:null"]', 700); await sleep(0.3);

  // 6. everyday life
  await click('.tile[data-k="self:null"]', 800);
  await to("#status", 800);
  await say("Her own hand on the watch: same body, no static jump. Ignored.", 0.6);
  await click('.tile[data-k="self:null"]', 700);
  await pg.evaluate(() => caption("")); await sleep(0.8);
  mark("end");
  clearInterval(statusLog);
  const vpath = await pg.video().path(); await ctx.close(); await b.close();
  fs.writeFileSync("timeline3.json", JSON.stringify({ video: vpath, log }, null, 1));
  console.log("video", vpath, "length", log[log.length - 1].t.toFixed(1), "s");
})();
