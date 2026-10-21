// Optional browser check: npm install --no-save playwright, then node smoke-test.cjs.
// Start both servers in demo mode first. Uses an installed Microsoft Edge browser.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

function recording() {
  const samples = 16000;
  const wav = Buffer.alloc(44 + samples * 2);
  wav.write("RIFF");
  wav.writeUInt32LE(wav.length - 8, 4);
  wav.write("WAVEfmt ", 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(16000, 24);
  wav.writeUInt32LE(32000, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write("data", 36);
  wav.writeUInt32LE(samples * 2, 40);
  for (let i = 0; i < samples; i++)
    wav.writeInt16LE(
      Math.round(Math.sin((i * 2 * Math.PI * 440) / 16000) * 12000),
      44 + i * 2,
    );
  return wav;
}

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto("http://localhost:3000");
    await page.getByText("DEMO MODE ENABLED", { exact: true }).waitFor();
    assert.equal(await page.locator(".species-card").count(), 10);
    await page
      .locator("input[type=file]")
      .setInputFiles({
        name: "test.wav",
        mimeType: "audio/wav",
        buffer: recording(),
      });
    await page
      .getByRole("img", { name: "Waveform of your recording" })
      .waitFor();
    await page.getByRole("button", { name: "Run demo analysis" }).click();
    await page
      .getByText("DEMO COMPLETE · NOT AI INFERENCE", { exact: true })
      .waitFor();
    await page.getByRole("button", { name: "Explore results" }).click();
    await page
      .getByText("DEMO RESULT — NOT AN AI PREDICTION", { exact: true })
      .waitFor();
    assert.equal(await page.locator(".ranking").count(), 3);
    await page.screenshot({ path: "demo-results.png", fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    );
    await page.getByRole("link", { name: "Explore another recording" }).click();
    await page.getByText("DEMO MODE ENABLED", { exact: true }).waitFor();
    await page.screenshot({ path: "mobile-home.png", fullPage: true });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    );
    await page
      .locator("input[type=file]")
      .setInputFiles({
        name: "invalid.wav",
        mimeType: "audio/wav",
        buffer: Buffer.from("not valid audio"),
      });
    await page.getByRole("button", { name: "Run demo analysis" }).click();
    await page
      .getByRole("alert")
      .filter({ hasText: "Cannot decode" })
      .waitFor();
    await page.goto("http://localhost:3000/results");
    await page.getByRole("heading", { name: "No result yet." }).waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "PASS: real HTTP demo upload, waveform, ten species, analysis success/error, results labels, refresh fallback, and mobile overflow.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
