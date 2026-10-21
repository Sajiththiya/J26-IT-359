// Start the trained-model backend and frontend, then: node smoke-model.cjs
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path");

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
    await page.goto("http://localhost:3000");
    await page.getByText("TRAINED MODEL READY", { exact: true }).waitFor({ timeout: 120000 });
    await page.getByRole("heading", { name: "Wav2Vec2, trained on your ten species." }).waitFor();
    assert.equal(await page.locator(".metric-grid article").count(), 4);
    assert.match(await page.locator(".metric-grid").innerText(), /63\.57/);
    assert.match(await page.locator(".metric-grid").innerText(), /0\.6349/);
    await page.locator(".report-details summary").click();
    assert.equal(await page.locator(".table-scroll tbody tr").count(), 10);
    await page.locator("#model").scrollIntoViewIfNeeded();
    await page.waitForFunction(() => [...document.querySelectorAll(".research-figures img")].every(image => image.complete && image.naturalWidth > 0));
    await page.locator("#model").screenshot({ path: "trained-model-report.png" });
    await page.locator('input[type="file"]').setInputFiles(path.resolve(__dirname, "../../colab_training_package/val/Chestnut-backed_Owlet/Chestnut-backed_Owlet__clip_00001.wav"));
    await page.getByRole("img", { name: "Waveform of your recording" }).waitFor();
    await page.getByRole("button", { name: "Analyze recording", exact: true }).click();
    await page.getByRole("heading", { name: "Your result is ready." }).waitFor({ timeout: 120000 });
    await page.getByRole("button", { name: "Explore results" }).click();
    await page.getByText("MODEL INFERENCE", { exact: true }).waitFor();
    assert.match(await page.locator(".prediction-card h2").innerText(), /Chestnut-backed Owlet/);
    assert.match(await page.locator(".ranking-card").innerText(), /Wav2Vec2/);
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.goto("http://localhost:3000/#model");
    await page.locator(".metric-grid").waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: "trained-model-mobile.png", fullPage: true });
    assert.deepEqual(errors, []);
    console.log("PASS: saved validation report, ten species, research figures, real Wav2Vec2 upload/results, and mobile layout.");
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
