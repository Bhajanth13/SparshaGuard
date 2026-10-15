const { execSync } = require("child_process");
const { chromium } = require(execSync("npm root -g").toString().trim() + "/playwright");
(async () => {
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await pg.goto("file://" + __dirname + "/cards.html"); await pg.waitForTimeout(1500);
  for (const id of ["title", "ncrb1", "ncrb2", "end"]) {
    await pg.evaluate((id) => document.querySelectorAll(".card").forEach((c) => (c.style.display = c.id === id ? "flex" : "none")), id);
    await pg.screenshot({ path: `card_${id}.png` });
  }
  console.log("fonts:", await pg.evaluate(() => document.fonts.check("800 40px Archivo"))); await b.close();
})();
