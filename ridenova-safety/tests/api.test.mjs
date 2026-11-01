// API-level acceptance tests: permissions are enforced by the server, records persist, provider
// failure leaves review usable, exports are protected.
import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../server/app.mjs';
import { FailingProvider } from '../server/providers.mjs';
import { tmp, cases } from './helpers.mjs';

const servers = [];
async function start(opts = {}) {
  const app = createApp({ fixedNow: Date.parse('2026-03-08T08:00:00Z'), ...opts });
  await new Promise((r) => app.server.listen(0, r));
  servers.push(app.server);
  const base = `http://127.0.0.1:${app.server.address().port}`;
  const as = async (user_id) => {
    const { token } = await (await fetch(base + '/api/session', { method: 'POST', body: JSON.stringify({ user_id }) })).json();
    const call = async (path, init = {}) => { const r = await fetch(base + path, { ...init, headers: { authorization: `Bearer ${token}`, ...(init.headers || {}) } }); const t = await r.text(); let j; try { j = JSON.parse(t); } catch { j = t; } return { status: r.status, body: j }; };
    call.cmd = (id, type, payload = {}, key) => call(`/api/cases/${id}/commands`, { method: 'POST', body: JSON.stringify({ type, payload, idempotency_key: key }) });
    return call;
  };
  return { app, base, as };
}
after(() => servers.forEach((s) => s.close()));
const SOS = cases.find((c) => /SOS emergency button pressed/.test(c.safety_toolkit_log || '')).case_id;

test('1 · API serves all 5,000 cases; raw dataset file is not downloadable', async () => {
  const { base, as } = await start({ dataDir: tmp() });
  assert.equal((await (await fetch(base + '/api/health')).json()).cases, 5000);
  assert.equal((await fetch(base + '/data/candidate_cases.json')).status, 404);
  assert.equal((await fetch(base + '/api/overview')).status, 401);
  const dm = await as('u-dm-1');
  assert.equal((await dm('/api/overview')).body.population, 5000);
});

test('5/6 · server enforces scope: agents cannot read or act on unauthorised cases', async () => {
  const { as } = await start({ dataDir: tmp() });
  const emea = await as('u-agent-emea');
  const list = (await emea('/api/cases?limit=200')).body;
  assert.ok(list.items.every((i) => i.lane === 'agent'));
  const us = cases.find((c) => c.region_group === 'US&C').case_id;
  assert.equal((await emea(`/api/cases/${us}`)).status, 404);
  assert.equal((await emea(`/api/cases/${SOS}`)).status, 404);
  assert.equal((await emea.cmd(SOS, 'acknowledge')).status, 404);
  assert.equal((await emea('/api/overview')).body.population < 5000, true); // aggregates are scoped too
  const gen = await as('u-agent-amer');
  assert.equal((await gen('/api/cases/SC-0104')).status, 404); // L3 violence needs capability
  const spec = await as('u-spec-threats');
  assert.equal((await spec('/api/cases/SC-0104')).status, 200);
});

test('13 · provider failure leaves human review usable', async () => {
  const { as } = await start({ dataDir: tmp(), provider: new FailingProvider() });
  const spec = await as('u-spec-threats');
  const r = await spec('/api/cases/SC-0104/ai/assess', { method: 'POST' });
  assert.equal(r.status, 502); assert.match(r.body.error, /human review continues/);
  assert.equal(r.body.case.severity.current, 'L3');
  const t = await spec('/api/cases/SC-0104/ai/translate', { method: 'POST' });
  assert.notEqual(t.body.status, 'live');
  assert.equal((await spec.cmd('SC-0104', 'take')).status, 200);
  assert.equal((await spec('/api/policy/ask', { method: 'POST', body: JSON.stringify({ question: 'Is a USD 40 cleaning fee property damage?' }) })).status, 200);
});

test('14 · unsupported/failed translation returns no text and a not-low-risk note', async () => {
  const { as } = await start({ dataDir: tmp() });
  const dm = await as('u-dm-1');
  const sw = cases.find((c) => c.language === 'sw' && c.region_group).case_id;
  const t = await dm(`/api/cases/${sw}/ai/translate`, { method: 'POST' });
  assert.equal(t.body.status, 'unavailable'); assert.equal(t.body.text, null); assert.match(t.body.note, /NOT treated as low risk/);
  const v = (await dm(`/api/cases/${sw}`)).body;
  assert.notEqual(v.severity.current, 'L1');
});

test('17 · records survive refresh and server restart', async () => {
  const dir = tmp();
  const a = await start({ dataDir: dir });
  const dm = await a.as('u-dm-1');
  assert.equal((await dm.cmd(SOS, 'acknowledge')).status, 200);
  assert.equal((await dm.cmd(SOS, 'step', { step: 'contact_reporter', value: 'reached' })).status, 200);
  const b = await start({ dataDir: dir });
  const dm2 = await b.as('u-dm-1');
  const v = (await dm2(`/api/cases/${SOS}`)).body;
  assert.ok(v.clocks.alert_acknowledged_at); assert.ok(v.clocks.first_response_at); assert.equal(v.owner, 'u-dm-1');
  assert.ok(v.history.some((h) => h.type === 'response.step'));
});

test('18/19 · exports: manager-only, minimum columns, no PII; reveal is owner-only and logged', async () => {
  const { as } = await start({ dataDir: tmp() });
  const agent = await as('u-agent-emea'); const dm = await as('u-dm-1');
  assert.equal((await agent('/api/export?format=csv')).status, 403);
  const csv = (await dm('/api/export?format=csv&region=EMEA')).body;
  assert.ok(csv.startsWith('case_id,predicted_tier,predicted_action,confidence,flags,rationale,human_decision,human_reason,decided_at'));
  for (const c of cases.filter((x) => x.region_group === 'EMEA').slice(0, 100)) assert.ok(!csv.includes(c.pii.reporter.email));
  const id = (await agent('/api/cases?limit=1')).body.items[0].case_id;
  assert.equal((await agent(`/api/cases/${id}/reveal`, { method: 'POST', body: JSON.stringify({ field: 'reporter.phone', reason: 'calling back' }) })).status, 403);
  await agent.cmd(id, 'take');
  const r = await agent(`/api/cases/${id}/reveal`, { method: 'POST', body: JSON.stringify({ field: 'reporter.phone', reason: 'calling back' }) });
  assert.equal(r.status, 200); assert.equal(r.body.parties.reporter.phone, cases.find((c) => c.case_id === id).pii.reporter.phone);
  assert.ok((await dm('/api/audit')).body.some((e) => e.event === 'pii_reveal' && e.case_id === id));
});

test('19 · idempotency over HTTP', async () => {
  const { as } = await start({ dataDir: tmp() });
  const agent = await as('u-agent-emea');
  const id = (await agent('/api/cases?limit=1&severity=L2')).body.items[0].case_id;
  await agent.cmd(id, 'approve', {}, 'idem-x'); await agent.cmd(id, 'approve', {}, 'idem-x');
  const v = (await agent(`/api/cases/${id}`)).body;
  assert.equal(v.decisions.length, 1); assert.equal(v.executions.length, 1);
});
