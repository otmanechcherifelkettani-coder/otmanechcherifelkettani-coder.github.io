// Real-browser test of the primary workflows (Chromium via Playwright). Mirrors docs/DEMO_SCRIPT.md.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp } from '../../server/app.mjs';

const require = createRequire(import.meta.url);
let chromium; try { ({ chromium } = require('playwright')); } catch { chromium = null; }
let app, base, browser, page;
const errors = [];

before(async () => {
  app = createApp({ dataDir: mkdtempSync(join(tmpdir(), 'rn-e2e-')), fixedNow: Date.parse('2026-03-08T08:00:00Z') });
  await new Promise((r) => app.server.listen(0, r));
  base = `http://127.0.0.1:${app.server.address().port}`;
  if (chromium) { browser = await chromium.launch(); page = await browser.newPage({ viewport: { width: 1440, height: 950 } }); page.on('pageerror', (e) => errors.push(e.message)); }
});
after(async () => { await browser?.close(); app.server.close(); });

const signIn = async (id) => { await page.goto(base + '/console.html'); await page.evaluate(() => sessionStorage.clear()); await page.goto(base + '/console.html'); await page.click(`.ucard[data-u=${id}]`); };
const fill = async (pairs) => { for (const [sel, v] of pairs) await page.fill(`#dlg ${sel}`, v); };

test('e2e · (c) urgent manager escalation: acknowledge, contact, decide, protect', { skip: !chromium && 'playwright not installed' }, async () => {
  await signIn('u-dm-1');
  await page.waitForSelector('.danger');
  await page.click('#ack'); await page.waitForSelector('[data-step=contact_reporter]');
  assert.match(await page.textContent('.statusbar'), /Under review/);
  await page.click('[data-step=contact_reporter][data-v=reached]'); await page.waitForTimeout(200);
  await page.click('[data-step=emergency_services][data-v=not_needed]'); await page.waitForTimeout(200);
  await page.click('[data-step=protect][data-v=restrict_rematch]'); await page.waitForTimeout(300);
  const t = await page.textContent('#detail');
  assert.match(t, /Execution · (completed|failed)/); assert.match(t, /simulated/);
});

test('e2e · (d) justified manager downgrade hands off to a human queue and keeps clocks', { skip: !chromium && 'playwright not installed' }, async () => {
  const id = (await page.textContent('.chead h1')).trim();
  const dueBefore = await page.textContent('.clock:last-child .v');
  await page.click('.more summary'); await page.click('#reassess');
  await page.selectOption('#dlg select[name=to]', 'L2');
  await page.selectOption('#dlg select[name=danger]', 'incorrectly_detected');
  await page.check('#dlg input[value=telematics]');
  await page.selectOption('#dlg select[name=policy]', 'SP-7');
  await page.selectOption('#dlg select[name=dest]', 'general-review');
  await fill([['textarea[name=reason]', 'too short']]); await page.click('#dlg-ok');
  await page.waitForFunction(() => document.querySelector('#dlg-err').textContent.length > 0);
  assert.match(await page.textContent('#dlg-err'), /reason/i);
  await fill([['textarea[name=reason]', 'Driver was returning a lost phone; rider confirmed on a call and telematics shows he left']]); await page.click('#dlg-ok');
  await page.waitForFunction(() => !document.querySelector('#dlg').open);
  const v = await (await page.request.get(`${base}/api/cases/${id}`, { headers: { authorization: `Bearer ${await page.evaluate(() => JSON.parse(sessionStorage.getItem('rn.session')).token)}` } })).json();
  assert.equal(v.severity.current, 'L2'); assert.equal(v.lane, 'agent'); assert.equal(v.handoff.status, 'pending'); assert.notEqual(v.workflow, 'resolved');
  assert.equal(v.severity.max_held, 'L4'); assert.ok(v.danger.alerts[0].acknowledged_at); assert.equal(v.severity.proposed, 'L4');
  assert.ok(dueBefore.includes(new Date(v.sla.due_at).toLocaleString('en-GB', { timeZone: 'UTC', month: 'short', day: '2-digit' }).split(',')[0].slice(0, 2)));
});

test('e2e · (a) upstream automation and an exception', { skip: !chromium && 'playwright not installed' }, async () => {
  await page.click('a[href="#overview"]'); await page.waitForSelector('#automode');
  await page.click('#automode'); await page.click('#dlg-ok'); await page.waitForFunction(() => /sent to review/.test(document.querySelector('#main').textContent), null, { timeout: 15000 });
  const text = await page.textContent('#main');
  assert.match(text, /completed/); assert.match(text, /sent to review/);
  const exc = app.wb.visible({ role: 'duty_manager', regions: ['EMEA', 'US&C', 'APAC', 'LatAm'] }).find((s) => s.automation.state === 'sent_to_review' && s.region === 'EMEA');
  await signIn('u-agent-emea'); await page.waitForSelector('.item');
  await page.goto(`${base}/console.html#work/${exc.case_id}`); await page.waitForSelector('.chead');
  assert.match(await page.textContent('#detail'), /Automation exception/);
});

test('e2e · (b) agent investigation: five questions, one primary action, distinct execution', { skip: !chromium && 'playwright not installed' }, async () => {
  for (const q of ['What happened?', 'What evidence is available?', 'What does policy imply?', 'What is uncertain or missing?', 'What should I do next?']) assert.ok((await page.textContent('#detail')).includes(q));
  if (await page.$('#p-take')) { await page.click('#p-take'); await page.waitForSelector('#p-approve'); }
  await page.click('#p-approve'); await page.waitForTimeout(400);
  const t = await page.textContent('#detail');
  assert.match(t, /Decision/); assert.match(t, /Execution · (completed|failed)/);
  // agents cannot open manager-lane cases
  await page.goto(`${base}/console.html#work/SC-0002`); await page.waitForTimeout(400);
  assert.match(await page.textContent('#detail'), /not authorised|Not available|not found/i);
});

test('e2e · (e) overview reconciles to the filtered population; no page errors', { skip: !chromium && 'playwright not installed' }, async () => {
  await signIn('u-dm-2'); await page.click('a[href="#overview"]'); await page.waitForSelector('.stats');
  await page.selectOption('[data-f=region]', 'LatAm'); await page.waitForTimeout(500);
  const pop = Number((await page.textContent('.stat .v')).replace(/,/g, ''));
  const bars = await page.$$eval('.card:first-child .bar span:last-child', (els) => els.map((e) => Number(e.textContent.replace(/,/g, ''))));
  assert.equal(bars.reduce((a, b) => a + b, 0), pop);
  assert.deepEqual(errors, []);
});
