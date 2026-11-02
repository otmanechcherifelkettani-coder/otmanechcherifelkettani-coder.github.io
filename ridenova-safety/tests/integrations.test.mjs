// Stored English translations, scope totals and the mock company-system adapters.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createApp } from '../server/app.mjs';
import { tmp, cases } from './helpers.mjs';
import { ACTION_TARGET, ticketRef } from '../src/domain/integrations.js';
import { EXEC_ACTIONS } from '../src/domain/catalog.js';

const servers = [];
async function start() {
  const app = createApp({ dataDir: tmp(), fixedNow: Date.parse('2026-03-08T08:00:00Z') });
  await new Promise((r) => app.server.listen(0, r));
  servers.push(app.server);
  const base = `http://127.0.0.1:${app.server.address().port}`;
  return async (user_id) => {
    const { token } = await (await fetch(base + '/api/session', { method: 'POST', body: JSON.stringify({ user_id }) })).json();
    const call = async (path, init = {}) => { const r = await fetch(base + path, { ...init, headers: { authorization: `Bearer ${token}` } }); return { status: r.status, body: await r.json() }; };
    call.cmd = (id, type, payload = {}) => call(`/api/cases/${id}/commands`, { method: 'POST', body: JSON.stringify({ type, payload, idempotency_key: `${id}-${type}-${Math.random()}` }) });
    return call;
  };
}
after(() => servers.forEach((s) => s.close()));

const stored = JSON.parse(readFileSync(new URL('../data/precomputed_translations.json', import.meta.url), 'utf8'));

test('T1 · every non-English case has a stored English translation, honestly labelled', () => {
  const nonEn = cases.filter((c) => c.language !== 'en');
  assert.ok(nonEn.length > 2900);
  for (const c of nonEn) {
    const t = stored[c.case_id];
    assert.ok(t && t.en && t.en.trim().length > 0, `missing translation for ${c.case_id}`);
    assert.match(t.by, /prepared in advance/i);
    assert.match(t.by, /not live/i);
    assert.doesNotMatch(t.by, /reviewed by the candidate/i);
  }
  assert.ok(cases.filter((c) => c.language === 'en' && stored[c.case_id]).length <= 1); // SC-1314: tagged en, written in Spanish
});

test('T2 · case view shows the stored translation by default, redacted like the original', async () => {
  const as = await start();
  const dm = await as('u-dm-1');
  // A non-English case whose translation contains a known personal value (reporter or reported-party name).
  const hit = cases.find((c) => c.language !== 'en' && stored[c.case_id] && [c.pii?.reporter?.name, c.pii?.reported_party?.name].some((n) => n && stored[c.case_id].en.includes(n)));
  const any = hit || cases.find((c) => c.language !== 'en');
  const v = (await dm(`/api/cases/${any.case_id}`)).body;
  assert.equal(v.report.translation.status, 'stored');
  assert.ok(v.report.translation.text.length > 0);
  if (hit) for (const n of [hit.pii?.reporter?.name, hit.pii?.reported_party?.name].filter(Boolean)) assert.ok(!v.report.translation.text.includes(n), 'name leaked through translation');
  const en = cases.find((c) => c.language === 'en');
  assert.equal((await dm(`/api/cases/${en.case_id}`)).body.report.translation, null);
});

test('T3 · overview reports the profile scope against the total', async () => {
  const as = await start();
  const mei = await as('u-agent-apac');
  const o = (await mei('/api/overview')).body;
  assert.equal(o.total, 5000);
  assert.ok(o.scope < o.total && o.scope === o.population);
  const dm = await as('u-dm-2');
  const od = (await dm('/api/overview')).body;
  assert.equal(od.scope, 5000);
  assert.equal(od.integrations.tickets_synced, 5000);
  assert.ok(od.integrations.pages_triggered >= od.alerts_unacknowledged);
});

test('T4 · each case carries a ticket reference, pages mirror alerts, actions name their target system', async () => {
  for (const a of Object.keys(EXEC_ACTIONS)) assert.ok(ACTION_TARGET[a], a);
  const as = await start();
  const dm = await as('u-dm-2');
  const list = (await dm('/api/cases?limit=50')).body.items;
  const l4 = list.find((i) => i.lane === 'manager');
  let v = (await dm(`/api/cases/${l4.case_id}`)).body;
  assert.equal(v.integrations.ticket.ref, ticketRef(l4.case_id));
  assert.equal(v.integrations.pages.length, v.danger.alerts.length);
  assert.ok(v.integrations.pages.every((p) => p.status === 'triggered'));
  v = (await dm.cmd(l4.case_id, 'acknowledge')).body.case;
  assert.ok(v.integrations.pages.every((p) => p.status === 'acknowledged'));
  assert.equal(v.integrations.ticket.status, 'Open · assigned');
  // Closing is refused before the reporter is contacted, then allowed once the step is recorded.
  const reason = 'Reporter reached by phone and confirmed safe at home.';
  assert.equal((await dm.cmd(l4.case_id, 'resolve', { outcome: 'reporter_safe', reason, danger_status: 'no_longer_present' })).status, 422);
  await dm.cmd(l4.case_id, 'step', { step: 'contact_reporter', value: 'reached' });
  v = (await dm.cmd(l4.case_id, 'step', { step: 'protect', value: 'restrict_rematch' })).body.case;
  const x = v.executions.find((e) => e.action === 'restrict_rematch');
  assert.match(x.target, /Account enforcement \(mock\)/);
  if (x.status === 'completed') {
    v = (await dm.cmd(l4.case_id, 'resolve', { outcome: 'reporter_safe', reason, danger_status: 'no_longer_present' })).body.case;
    assert.equal(v.workflow, 'resolved');
    assert.equal(v.integrations.ticket.status, 'Solved');
  }
});
