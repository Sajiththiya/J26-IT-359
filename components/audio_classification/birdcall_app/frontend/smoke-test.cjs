// Run with both servers started. Requires Playwright and Microsoft Edge.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path");
(async () => {
 const browser = await chromium.launch({channel:"msedge",headless:true});
 try {
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on("pageerror", e=>errors.push(e.message));
  await page.goto("http://localhost:3000");
  const health=await (await page.request.get("http://localhost:8000/health")).json();
  assert(health.ready);
  if(process.env.EXPECT_DEMO) assert.equal(health.demo_mode,process.env.EXPECT_DEMO==="true");
  await page.getByText(health.demo_mode?"DEMO MODE ENABLED":"TRAINED MODEL READY",{exact:true}).waitFor();
  assert.equal(await page.locator("#prediction-results,#species,#model,.project-note,.species-card,.metric-grid").count(),0);
  assert.equal(await page.getByRole("link",{name:/Model results|The species/}).count(),0);
  const upload=page.locator('input[type="file"]');
  const fixture=path.resolve(__dirname,"../../colab_training_package/val/Chestnut-backed_Owlet/Chestnut-backed_Owlet__clip_00001.wav");
  const analyze=page.getByRole("button",{name:health.demo_mode?"Run demo analysis":"Analyze recording",exact:true});
  async function widths(){for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}px`);}}
  await upload.setInputFiles(fixture);
  await page.getByRole("img",{name:"Waveform of your recording"}).waitFor();
  await widths();
  assert.equal(await page.locator("#prediction-results").count(),0);
  await page.route("**/predict",async route=>{await new Promise(r=>setTimeout(r,600));await route.continue();},{times:1});
  const response=page.waitForResponse(r=>r.url().endsWith("/predict")&&r.status()===200,{timeout:120000});
  await analyze.click();
  await page.getByRole("button",{name:/Analyzing recording/}).waitFor();
  assert.equal(await page.locator("#prediction-results").count(),0);
  assert(await page.locator("audio").isVisible());
  const result=await (await response).json();
  await page.locator("#prediction-results").waitFor();
  await page.waitForURL("**/results");
  assert.equal(new URL(page.url()).pathname,"/results");
  assert(await page.getByText(path.basename(fixture),{exact:true}).isVisible());
  assert.equal(await page.locator(".prediction-card h2").innerText(),result.prediction.species);
  assert.equal((await page.locator(".big-score").innerText()).replace(/\s/g,""),`${(result.prediction.confidence*100).toFixed(1)}%`);
  assert.equal(await page.locator(".ranking").count(),Math.min(result.top_three.length,3));
  if(!health.demo_mode) await page.getByText("Model confidence",{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.scrollY),0);
  await page.locator("audio").evaluate(async audio=>{await audio.play();});
  await page.waitForTimeout(300);
  assert(await page.locator("audio").evaluate(audio=>audio.currentTime>0));
  await page.locator("audio").evaluate(audio=>audio.pause());
  await widths();
  await page.screenshot({path:"simplified-results.png",fullPage:true});
  await page.getByRole("button",{name:"Analyze another recording"}).click();
  await page.waitForURL("**/#listen");
  assert.equal(await page.locator("#prediction-results").count(),0);
  assert(await page.locator("audio").isVisible());
  await upload.setInputFiles({name:"invalid.txt",mimeType:"text/plain",buffer:Buffer.from("invalid")});
  await page.getByRole("alert").filter({hasText:"WAV, MP3, or M4A"}).waitFor();
  assert(await page.locator("audio").isVisible());
  await upload.setInputFiles({name:"invalid.wav",mimeType:"audio/wav",buffer:Buffer.from("invalid")});
  await analyze.click();
  await page.getByRole("alert").filter({hasText:"Cannot decode"}).waitFor();
  await page.waitForURL("**/#listen");
  assert.equal(await page.locator("#prediction-results").count(),0);
  assert(await page.locator("audio").isVisible());
  await upload.setInputFiles(fixture);
  // Invalid score must be rejected, never presented as a percentage.
  await page.route("**/predict",route=>route.fulfill({json:{...result,prediction:{...result.prediction,confidence:2}}}),{times:1});
  await analyze.click();
  await page.getByRole("alert").filter({hasText:"invalid probability scores"}).waitFor();
  assert.equal(await page.locator("#prediction-results").count(),0);
  // Reuse the actual response to check cancellation, without invented predictions.
  await page.route("**/predict",async route=>{await new Promise(r=>setTimeout(r,1200));await route.fulfill({json:result}).catch(()=>{});},{times:1});
  await analyze.click();
  await page.getByRole("button",{name:/Analyzing recording/}).waitFor();
  await page.getByRole("button",{name:"Clear recording"}).click();
  await page.waitForTimeout(1500);
  assert.equal(await page.locator("#prediction-results,audio").count(),0);
  for(const route of ["analysis","results"]){await page.goto(`http://localhost:3000/${route}`);await page.waitForURL("**/#listen");assert.equal(await page.locator("#prediction-results").count(),0);}
  assert.deepEqual(errors,[]);
  console.log("PASS: results-page navigation with actual API results, preserved audio, loading/errors, score guard, cancellation, redirects, and mobile/tablet/desktop layout.");
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
