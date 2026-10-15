const { execSync } = require("child_process");
const { chromium } = require(execSync("npm root -g").toString().trim() + "/playwright");
const fs = require("fs");
const BASE = "http://localhost:8800";
const WPS = 2.6;
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: "rec3", size: { width: 1920, height: 1080 } },
    timezoneId: "Asia/Kolkata", locale: "en-IN" });
  const pg = await ctx.newPage(); const T0 = Date.now(); const now = () => (Date.now() - T0) / 1000;
  const log = []; const mark = (ev, extra = {}) => log.push({ t: now(), ev, ...extra });
  await pg.route(BASE + "/__wrapper.html", (r) => r.fulfill({ contentType: "text/html", body: fs.readFileSync("wrapper3.html", "utf8") }));
  await pg.goto(BASE + "/__wrapper.html");
  const sleep = (s) => pg.waitForTimeout(s * 1000);
  const frameFor = async (part) => { for (let i = 0; i < 80; i++) { const f = pg.frames().find((x) => x.url().includes(part)); if (f) return f; await sleep(0.1); } };
  let F = await frameFor("/index.html"); await F.waitForSelector(".card"); await sleep(0.8);
  const words = (t) => t.split(/\s+/).length;
  const say = async (t, extra = 0) => { mark("caption", { text: t }); await pg.evaluate((t) => caption(t), t); await sleep(Math.max(0, words(t) / WPS + extra)); };
  const sayAsync = async (t) => { mark("caption", { text: t }); await pg.evaluate((t) => caption(t), t); };
  const moveXY = async (x, y, ms) => { await pg.mouse.move(x, y); await pg.evaluate(([x, y, ms]) => moveCursor(x, y, ms), [x, y, ms]); await sleep(ms / 1000); };
  const to = async (sel, ms = 900, dx = 0.5, dy = 0.5) => { const bb = await F.locator(sel).first().boundingBox(); const x = bb.x + bb.width * dx, y = bb.y + bb.height * dy; await moveXY(x, y, ms); return [x, y]; };
  const rip = () => pg.evaluate(() => ripple());
  const click = async (sel, ms = 800) => { const [x, y] = await to(sel, ms); await sleep(0.15); await rip(); await pg.mouse.click(x, y); await sleep(0.2); };
  const status = () => F.$eval("#status", (e) => e.innerText);
  const waitFast = async (pred, max = 30) => { const t = now(); let on = false, ok = false;
    for (let i = 0; i < max * 10; i++) { if (pred(await status())) { ok = true; break; } if (!on && now() - t > 0.4) { mark("fast_on"); on = true; } await sleep(0.1); }
    if (on) mark("fast_off");
    if (!ok) throw new Error("MISSED: the twin did not reach the expected state (a missed detection); retake"); };
  const typePin = async (pin) => { for (const d of pin) { await click(`.pad button[data-key="${d}"]`, 380); await sleep(0.15); } };
  const TABS = ["SparshaGuard", "SparshaGuard Digital Twin", "SparshaGuard Touch Explorer"];
  let statusOn = false;
  const statusLog = setInterval(async () => { if (!statusOn) return; try { const s = await status(); if (s !== statusLog.last) { statusLog.last = s; mark("status", { text: s }); } } catch (e) {} }, 100);

  mark("start");
  // ---------- front page: intro and website
  await to("h1", 1300, 0.3, 0.5);
  await say("Hi! We are Bhajanth V and Sukruth A Chinnur, co-developers of SparshaGuard at RV University, Mysuru.", 0.4);
  await moveXY(560, 100, 900);
  await sayAsync("Everything here is live at bhajanth13.github.io/SparshaGuard: anyone can try the digital twin and the explorer.");
  await sleep(2.2);
  await to('a.card[href*="demo"] .go', 1000);
  await sleep(Math.max(0, 16 / WPS - 3.2));
  await rip(); await sleep(0.3);
  // opens in a new tab
  await pg.evaluate((t) => setTabs(t.slice(0, 2), 1), TABS);
  await pg.evaluate(() => openPage("/demo/sparshaguard_demo.html", "/SparshaGuard/demo/sparshaguard_demo.html", 1));
  F = await frameFor("sparshaguard_demo"); await F.waitForSelector("#status");
  await F.addStyleTag({ content: ".tiles{grid-template-columns:repeat(11,minmax(0,1fr))!important} .tile{padding:8px 4px!important;font-size:12.5px!important}" });
  statusOn = true; await sleep(0.6);

  // ---------- twin
  await to(".watch", 900);
  await sayAsync("The digital twin runs the watch's own firmware on a simulated sensor. We switch Guard Mode on.");
  await sleep(2.0);
  await click("#tab-try", 800);
  await F.evaluate(() => window.scrollTo({ top: 40, behavior: "smooth" }));
  await sleep(Math.max(0, 16 / WPS - 3.2));
  await waitFast((s) => s.startsWith("Guarding"));
  await to("#cv-score", 900, 0.55, 0.6);
  await say("Physics 1, capacitance: the watch sweeps 200 frequencies through a skin electrode, five times a second.", 0.3);

  await click('.tile[data-k="person:wrist"]', 800);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await to(".watch", 500, 0.5, 0.3);
  await say("A stranger grabs her wrist: the watch vibrates, asks for a PIN, and the mic turns on.", 0);
  await to("#cv-score", 600, 0.93, 0.25);
  await say("Capacitance: his hand closes a path back to the watch. Signal: 0.1 % → 16 %.", 0);
  await waitFast((s) => s.startsWith("Alert sent"), 20);
  await to(".phone .msg", 900, 0.5, 0.35);
  await say("No PIN: her location and the voice recording go to her emergency contact, and 112 is called.", 0.4);
  await click('.tile[data-k="person:wrist"]', 600);
  await click("#reset", 600);
  await click('#screen button[data-act="on"]', 700);
  await sayAsync("Guard Mode back on.");
  await sleep(1.2); await waitFast((s) => s.startsWith("Guarding"));

  await click('.tile[data-k="person:shoulder"]', 800);
  await to("#cv-static", 800, 0.92, 0.4);
  await say("Physics 2, static electricity: every body carries charge. Touching bodies share it within a microsecond, so her voltage jumps.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await sayAsync("She cancels with her PIN; a duress PIN would cancel on screen but alert silently.");
  await typePin("1234"); await sleep(Math.max(0, 14 / WPS - 4.0));
  await to("#cv-static", 800, 0.92, 0.4);
  await say("That grab was on her shoulder: too far for the capacitive sensor, but the static jump and her pulled arm gave it away.", 0.2);
  await click('.tile[data-k="person:shoulder"]', 600);

  await click('.tile[data-k="struggle:null"]', 800);
  await to("#cv-static", 800, 0.85, 0.8);
  await say("She struggles to get free: the accelerometer and gyroscope see irregular jerks. A PIN prompt, even without a touch.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await typePin("1234"); await sleep(0.3);
  await click('.tile[data-k="struggle:null"]', 600);

  await click('.tile[data-k="self:null"]', 800);
  await to("#status", 800);
  await say("Her own hand on the watch is the same body: no static jump, so no alarm.", 0.5);
  await click('.tile[data-k="self:null"]', 600);
  statusOn = false;

  // ---------- explorer: research basis
  await sayAsync("Every threshold and value comes from published research: 60 sources, checked with SPICE and FastCap.");
  const [tx, ty] = await pg.evaluate(() => { setTabs(["SparshaGuard", "SparshaGuard Digital Twin"], 1); return tabCenter(0); });
  await moveXY(tx, ty, 900); await rip(); await sleep(0.3);
  await pg.evaluate(() => { setTabs(["SparshaGuard", "SparshaGuard Digital Twin"], 0); showTab(0, "/SparshaGuard/"); });
  F = await frameFor("/index.html"); await sleep(0.4);
  await to('a.card[href*="explorer"] .go', 900); await rip(); await sleep(0.3);
  await pg.evaluate((t) => setTabs(t, 2), TABS);
  await pg.evaluate(() => openPage("/explorer/sparshaguard_explorer.html", "/SparshaGuard/explorer/sparshaguard_explorer.html", 2));
  F = await frameFor("sparshaguard_explorer"); await F.waitForSelector("#presets");
  await sleep(Math.max(0, 15 / WPS - 3.6));
  await click('#presets [data-p="self"]', 900);
  await to("#pill", 800);
  await say("The explorer runs the same physics: pick a situation and see whether the watch would notice, and why.", 0.3);
  await F.evaluate(() => document.getElementById("references").scrollIntoView({ behavior: "smooth" }));
  await sleep(1.2);
  await to(".ieee li:nth-child(4)", 900, 0.3, 0.5);
  await say("Each value is cited like a research paper: these are the 60 references.", 0.6);
  await pg.evaluate(() => caption("")); await sleep(0.6);
  mark("end"); clearInterval(statusLog);
  const vpath = await pg.video().path(); await ctx.close(); await b.close();
  fs.writeFileSync("timeline4.json", JSON.stringify({ video: vpath, log }, null, 1));
  console.log("video", vpath, "length", log[log.length - 1].t.toFixed(1));
})();
