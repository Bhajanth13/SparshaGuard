const { execSync } = require("child_process");
const { chromium } = require(execSync("npm root -g").toString().trim() + "/playwright");
const fs = require("fs");
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: ".", size: { width: 1920, height: 1080 } },
    timezoneId: "Asia/Kolkata", locale: "en-IN" });
  const pg = await ctx.newPage(); const T0 = Date.now();
  await pg.goto("file:///home/user/SparshaGuard/demo/sparshaguard_demo.html");
  // frame the stage for video: bigger, control bar moved out of view (still driven through its buttons)
  await pg.addStyleTag({ content: "html{zoom:1.38} #bar-guided,#bar-try,.science,footer{position:absolute!important;left:-99999px!important} .wrap{padding-top:8px}" });
  await pg.waitForTimeout(1500);
  const log = []; const t = () => (Date.now() - T0) / 1000;
  log.push({ t: t(), ev: "start" });
  await pg.$eval("#playall", (x) => x.click());
  let last = "", lastSt = "";
  while (t() < 200) {
    const cap = await pg.$eval("#caption", (e) => e.innerText.split("\n")[0]);
    const st = await pg.$eval("#status", (e) => e.innerText);
    if (cap !== last) { log.push({ t: t(), ev: "caption", text: cap }); last = cap; }
    if (st.split(":")[0] !== lastSt) { log.push({ t: t(), ev: "status", text: st }); lastSt = st.split(":")[0]; }
    const done = await pg.$$eval("#chapters button.done", (x) => x.length);
    if (done === 8) { await pg.waitForTimeout(2500); log.push({ t: t(), ev: "end" }); break; }
    await pg.waitForTimeout(100);
  }
  const vpath = await pg.video().path();
  await ctx.close(); await b.close();
  fs.writeFileSync("timeline.json", JSON.stringify({ video: vpath, log }, null, 1));
  console.log("video", vpath, "end at", log[log.length - 1].t.toFixed(1), "s,", log.length, "events");
})();
