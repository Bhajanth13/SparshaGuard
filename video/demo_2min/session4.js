// Records the 2-minute explainer for someone who has never seen SparshaGuard: a Chrome-style window, a cursor, captions only.
const { execSync } = require("child_process");
const { chromium } = require(execSync("npm root -g").toString().trim() + "/playwright");
const fs = require("fs");
const BASE = "http://localhost:8800";
const WPS = 2.6;
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: "rec4", size: { width: 1920, height: 1080 } },
    timezoneId: "Asia/Kolkata", locale: "en-IN" });
  const pg = await ctx.newPage(); const T0 = Date.now(); const now = () => (Date.now() - T0) / 1000;
  const log = []; const mark = (ev, extra = {}) => log.push({ t: now(), ev, ...extra });
  await pg.route(BASE + "/__wrapper.html", (r) => r.fulfill({ contentType: "text/html", body: fs.readFileSync("wrapper4.html", "utf8") }));
  for (const id of ["ncrb", "title", "end"])
    await pg.route(BASE + `/__card_${id}.png`, (r) => r.fulfill({ contentType: "image/png", body: fs.readFileSync(`card4_${id}.png`) }));
  await pg.goto(BASE + "/__wrapper.html");
  const sleep = (s) => pg.waitForTimeout(s * 1000);
  const frameFor = async (part) => { for (let i = 0; i < 80; i++) { const f = pg.frames().find((x) => x.url().includes(part)); if (f) return f; await sleep(0.1); } };
  let F = await frameFor("/index.html"); await F.waitForSelector(".card");
  // the cards are preloaded under the slide layer so the first frame is already the NCRB card
  await pg.evaluate(() => { cursorVisible(false); showSlide("/__card_ncrb.png"); });
  await pg.evaluate(() => Promise.all(["/__card_title.png", "/__card_end.png"].map((s) => new Promise((r) => { const i = new Image(); i.onload = r; i.src = s; }))));
  await sleep(0.8);
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
  // ---------- the problem and the idea
  await say("In 2022, India registered 4,45,256 crimes against women: about 51 every hour.", 0.6);
  await say("Nearly one in five was a grab or an unwanted touch. There's no time to unlock a phone.", 0.6);
  await pg.evaluate(() => showSlide("/__card_title.png")); await sleep(0.3);
  await say("SparshaGuard: a smartwatch that notices when another person touches her, and calls for help itself.", 0.5);
  await say("Designed by co-developers Bhajanth V and Sukruth A Chinnur, RV University, Mysuru.", 0.5);

  // ---------- the website
  await pg.evaluate(() => { showSlide(null); cursorVisible(true); }); await sleep(0.7);
  await sayAsync("The watch isn't built yet, so we made a digital twin: its real software on a simulated body. Try it here.");
  await moveXY(330, 66, 1100); await sleep(1.6);
  await to('a.card[href*="demo"] .go', 1100);
  await sleep(Math.max(0, 21 / WPS - 4.4));
  await rip(); await sleep(0.3);
  await pg.evaluate((t) => setTabs(t.slice(0, 2), 1), TABS);
  await pg.evaluate(() => openPage("/demo/sparshaguard_demo.html", "/SparshaGuard/demo/sparshaguard_demo.html", 1));
  F = await frameFor("sparshaguard_demo"); await F.waitForSelector("#status");
  await F.addStyleTag({ content: ".tiles{grid-template-columns:repeat(11,minmax(0,1fr))!important} .tile{padding:8px 4px!important;font-size:12.5px!important}" });
  await click("#tab-try", 800);
  await F.evaluate(() => window.scrollTo({ top: 40, behavior: "smooth" }));
  statusOn = true; await sleep(0.4);

  // ---------- a tour of the twin
  await sayAsync("Left: the wearer. Middle: her watch. Right: her emergency contact's phone. Tiles: things that can happen to her.");
  await to(".bodycard", 900, 0.5, 0.4);
  await sleep(1.0); await to(".watch", 900); await sleep(1.0); await to(".phone", 900); await sleep(1.0);
  await to('.tile[data-k="person:wrist"]', 900, 0.5, 0.5); await moveXY(1500, 960 - 70, 1400);
  await sleep(Math.max(0, 18 / WPS - 7.5));
  await waitFast((s) => s.startsWith("Guarding"));
  await to(".watch", 800);
  await say("She has turned on Guard Mode: the watch is watching for touches.", 0.3);
  await to("#cv-score", 900, 0.55, 0.6);
  await say("Physics 1, capacitance: her body holds a little electric charge, and the watch measures how much.", 0.3);

  // ---------- 1. a stranger grabs her wrist
  await click('.tile[data-k="person:wrist"]', 800);
  await to("#cv-score", 600, 0.93, 0.25);
  await say("A stranger grabs her wrist. His body holds charge too: the reading jumps from 0.1 % to 16 %.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await to(".watch", 600, 0.5, 0.3);
  await say("The watch vibrates and asks for her PIN within 15 seconds. The mic starts recording.", 0);
  await waitFast((s) => s.startsWith("Alert sent"), 20);
  await to(".phone .msg", 900, 0.5, 0.35);
  await say("No PIN: her GPS location and the recording go to her contact, and 112 is called.", 0.4);
  await click('.tile[data-k="person:wrist"]', 600);
  await click("#reset", 600);
  await click('#screen button[data-act="on"]', 700);
  await sleep(0.8); await waitFast((s) => s.startsWith("Guarding"));

  // ---------- 2. a grab on her shoulder: static electricity
  await to('.tile[data-k="person:shoulder"]', 900);
  await say("What if he grabs her shoulder, far from the watch? Physics 2, static electricity.", -0.6);
  await click('.tile[data-k="person:shoulder"]', 400);
  await to("#cv-static", 800, 0.92, 0.4);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await say("Every body carries static charge. Touching bodies share it in a microsecond, so her voltage jumps.", 0.2);
  await sayAsync("This time it's a friend: she types her PIN, and it cancels.");
  await to(".watch", 600, 0.5, 0.3);
  await typePin("1234"); await sleep(Math.max(0, 12 / WPS - 3.6));
  await click('.tile[data-k="person:shoulder"]', 600);

  // ---------- 3. a struggle, 4. her own hand
  await click('.tile[data-k="struggle:null"]', 800);
  await to("#cv-static", 800, 0.85, 0.8);
  await say("If she struggles, motion sensors feel the irregular jerks and ask for the PIN, even without a touch.", 0);
  await waitFast((s) => s.startsWith("Enter PIN"), 8);
  await click('.tile[data-k="struggle:null"]', 600);
  await typePin("1234"); await sleep(0.3);
  await click('.tile[data-k="self:null"]', 800);
  await to("#status", 800);
  await say("Her own hand is the same body: no new charge, so no alarm.", 0.5);
  await click('.tile[data-k="self:null"]', 600);
  statusOn = false;

  // ---------- research basis and the explorer
  await sayAsync("These numbers aren't guesses: every threshold comes from 60 published papers, checked with SPICE and FastCap.");
  const [tx, ty] = await pg.evaluate(() => { setTabs(["SparshaGuard", "SparshaGuard Digital Twin"], 1); return tabCenter(0); });
  await moveXY(tx, ty, 900); await rip(); await sleep(0.3);
  await pg.evaluate(() => { setTabs(["SparshaGuard", "SparshaGuard Digital Twin"], 0); showTab(0, "/SparshaGuard/"); });
  F = await frameFor("/index.html"); await sleep(0.4);
  await to('a.card[href*="explorer"] .go', 900); await rip(); await sleep(0.3);
  await pg.evaluate((t) => setTabs(t, 2), TABS);
  await pg.evaluate(() => openPage("/explorer/sparshaguard_explorer.html", "/SparshaGuard/explorer/sparshaguard_explorer.html", 2));
  F = await frameFor("sparshaguard_explorer"); await F.waitForSelector("#presets");
  await sleep(Math.max(0, 16 / WPS - 3.6));
  await click('#presets [data-p="wrist"]', 900);
  await to("#pill", 800);
  await say("The physics explorer shows, for any situation, whether the watch would notice, and why.", 0.3);
  await F.evaluate(() => document.getElementById("references").scrollIntoView({ behavior: "smooth" }));
  await sleep(1.2);
  await to(".ieee li:nth-child(4)", 900, 0.3, 0.5);
  await say("Every value is cited, like in a research paper.", 0.5);

  // ---------- close
  await pg.evaluate(() => { cursorVisible(false); showSlide("/__card_end.png"); }); await sleep(0.3);
  await say("Try it at bhajanth13.github.io/SparshaGuard. Next: a real prototype. SparshaGuard: the touch itself raises the alarm.", 0.8);
  mark("end"); clearInterval(statusLog);
  const vpath = await pg.video().path(); await ctx.close(); await b.close();
  fs.writeFileSync("timeline5.json", JSON.stringify({ video: vpath, log }, null, 1));
  console.log("video", vpath, "length", log[log.length - 1].t.toFixed(1));
})();
