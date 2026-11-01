// HTTP API for the Safety Workbench. Permissions are enforced HERE on every request; the
// browser only ever receives scoped, masked data.
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes } from 'node:crypto';
import { Workbench } from '../src/domain/workbench.js';
import { USERS, QUEUES, CAPABILITIES, EXEC_ACTIONS, POLICY_VERSION, SLA_MIN } from '../src/domain/catalog.js';
import { overview, filterOptions, applyFilters, listItem, caseView, exportRow, toCSV, FILTER_KEYS } from '../src/domain/views.js';
import { viewLevel } from '../src/domain/permissions.js';
import { slaStatus } from '../src/domain/sla.js';
import { POLICY } from '../src/policy.js';
import { JsonlLog } from './eventlog.mjs';
import { SimulatedProvider, AnthropicProvider } from './providers.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png' };
const REVEALABLE = new Set(['report_text', 'addresses', ...['reporter', 'reported_party'].flatMap((k) => ['name', 'phone', 'email', 'vehicle_plate'].map((f) => `${k}.${f}`))]);
const STATIC_DENY = /[/\\](server|node_modules|tests|data[/\\]runtime|validation[/\\]silver)|\.env/;

export function createApp({
  dataDir = join(ROOT, 'data', 'runtime'), replayNow = process.env.REPLAY_NOW || '2026-03-08T08:00:00Z', fixedNow = null,
  provider = null, automationMode = process.env.AUTOMATION_MODE || 'shadow', failPct, retentionDays = Number(process.env.RETENTION_DAYS || 365),
} = {}) {
  const cases = JSON.parse(readFileSync(join(ROOT, 'data', 'candidate_cases.json'), 'utf8'));
  const fixtures = JSON.parse(readFileSync(join(ROOT, 'data', 'precomputed_translations.json'), 'utf8'));
  // Replay clock: the dataset has naive local timestamps and no real responses. "Now" starts at
  // REPLAY_NOW and advances with real time so demo actions get realistic relative timestamps.
  const bootReal = Date.now();
  const replay0 = Date.parse(replayNow);
  const now = fixedNow ? () => fixedNow : () => replay0 + (Date.now() - bootReal);
  const ai = provider || (process.env.ANTHROPIC_API_KEY ? new AnthropicProvider({ model: process.env.AI_MODEL, effort: process.env.AI_EFFORT }) : new SimulatedProvider(fixtures));
  const local = new SimulatedProvider(fixtures);
  const log = new JsonlLog(join(dataDir, 'events.jsonl'), { retentionDays });
  const audit = new JsonlLog(join(dataDir, 'access.jsonl'), { retentionDays: Number(process.env.AUDIT_RETENTION_DAYS || 400) });
  const wb = new Workbench({ cases, log, audit, now, automationMode, failPct });
  const sessions = new Map(); // token -> { user, revealed: Map(case_id -> {field:true}) }

  const send = (res, code, body, type = 'application/json; charset=utf-8') => {
    res.writeHead(code, { 'content-type': type, 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
    res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
  };
  const body = async (req) => { let b = ''; for await (const ch of req) { b += ch; if (b.length > 64e3) throw Object.assign(new Error('Payload too large'), { code: 413 }); } return b ? JSON.parse(b) : {}; };
  const filtersFrom = (url) => Object.fromEntries(FILTER_KEYS.map((k) => [k, url.searchParams.get(k) || '']).filter(([, v]) => v));
  const view = (sess, s) => caseView(s, wb.raw.get(s.case_id), sess.user, now(), sess.revealed.get(s.case_id) || {});

  async function api(req, res, url) {
    const path = url.pathname;
    if (path === '/api/health') return send(res, 200, { ok: true, ai: ai.info(), automation_mode: wb.mode, replay_now: new Date(now()).toISOString(), cases: wb.states.size, signin: 'simulated' });
    if (path === '/api/users' && req.method === 'GET') return send(res, 200, Object.values(USERS).map(({ id, name, role, regions, capabilities }) => ({ id, name, role, regions, capabilities })));
    if (path === '/api/session' && req.method === 'POST') {
      const { user_id } = await body(req);
      const user = USERS[user_id];
      if (!user) return send(res, 400, { error: 'Unknown user' });
      const token = randomBytes(18).toString('hex');
      sessions.set(token, { user, revealed: new Map() });
      wb.auditLog(user, 'sign_in', null, { simulated: true });
      return send(res, 200, { token, user });
    }
    const sess = sessions.get((req.headers.authorization || '').replace(/^Bearer /, ''));
    if (!sess) return send(res, 401, { error: 'Sign in first.' });
    const user = sess.user;

    if (path === '/api/meta') return send(res, 200, { user, queues: QUEUES, capabilities: CAPABILITIES, exec_actions: EXEC_ACTIONS, policy: POLICY, policy_version: POLICY_VERSION, sla_min: SLA_MIN,
      users: Object.values(USERS).map(({ id, name, role }) => ({ id, name, role })), ai: ai.info(), automation_mode: wb.mode, replay_now: new Date(now()).toISOString() });
    if (path === '/api/overview') {
      const scope = wb.visible(user);
      wb.auditLog(user, 'view_overview', null, { scope: scope.length });
      return send(res, 200, { scope: scope.length, filters: filtersFrom(url), options: filterOptions(scope), replay_now: new Date(now()).toISOString(), automation_mode: wb.mode, ...overview(scope, filtersFrom(url), now()) });
    }
    if (path === '/api/cases' && req.method === 'GET') {
      const f = filtersFrom(url);
      let items = applyFilters(wb.visible(user), f);
      if (url.searchParams.get('mine') === '1') items = items.filter((s) => s.owner === user.id);
      if (url.searchParams.get('open') !== '0') items = items.filter((s) => s.workflow !== 'resolved');
      const t = now();
      const ranked = items.map((s) => ({ s, sla: slaStatus(s, t) }));
      ranked.sort((a, b) => (b.s.danger.alerts.some((x) => !x.acknowledged_at) - a.s.danger.alerts.some((x) => !x.acknowledged_at)) || (({ L4: 4, L3: 3, L2: 2, L1: 1 })[b.s.severity.current] - ({ L4: 4, L3: 3, L2: 2, L1: 1 })[a.s.severity.current]) || (Date.parse(a.sla.due_at) - Date.parse(b.sla.due_at)));
      const limit = Math.min(200, Number(url.searchParams.get('limit') || 60));
      const offset = Number(url.searchParams.get('offset') || 0);
      return send(res, 200, { total: ranked.length, items: ranked.slice(offset, offset + limit).map((x) => listItem(x.s, t)) });
    }
    const m = path.match(/^\/api\/cases\/(SC-\d{4})(\/[a-z/]+)?$/);
    if (m) {
      const s = wb.states.get(m[1]);
      if (!s || !viewLevel(user, s)) { wb.auditLog(user, 'denied_view', m[1], {}); return send(res, 404, { error: 'Case not found or not authorised.' }); }
      const sub = m[2] || '';
      if (sub === '' && req.method === 'GET') { wb.auditLog(user, 'view_case', s.case_id, {}); return send(res, 200, view(sess, s)); }
      if (sub === '/commands' && req.method === 'POST') {
        const { type, payload, idempotency_key } = await body(req);
        const r = wb.command(user, s.case_id, type, payload || {}, idempotency_key || null);
        return send(res, r.ok ? 200 : r.code || 422, r.ok ? { ...r, case: view(sess, s) } : r);
      }
      if (sub === '/reveal' && req.method === 'POST') {
        const { field, reason } = await body(req);
        if (!REVEALABLE.has(field)) return send(res, 400, { error: 'Unknown field' });
        if (viewLevel(user, s) !== 'full' || (user.role !== 'duty_manager' && s.owner !== user.id)) return send(res, 403, { error: 'Take the case before viewing personal data.' });
        if (!reason || reason.trim().length < 5) return send(res, 422, { error: 'A reason (5+ characters) is required.' });
        const r = sess.revealed.get(s.case_id) || {}; r[field] = true; sess.revealed.set(s.case_id, r);
        wb.auditLog(user, 'pii_reveal', s.case_id, { field, reason: reason.trim() });
        return send(res, 200, view(sess, s));
      }
      if (sub === '/ai/assess' && req.method === 'POST') {
        try { const p = await ai.triage(wb.raw.get(s.case_id)); wb.applyAssessment(s.case_id, p, `ai:${p.mode}`); wb.auditLog(user, 'ai_assess', s.case_id, { mode: p.mode }); return send(res, 200, view(sess, s)); }
        catch (e) { wb.aiFailed(s.case_id, e.message); return send(res, 502, { error: `AI unavailable: ${e.message}. The case keeps its current assessment; human review continues.`, case: view(sess, s) }); }
      }
      if (sub === '/ai/translate' && req.method === 'POST') {
        let t;
        try { t = await ai.translate(wb.raw.get(s.case_id)); } catch (e) { t = { status: 'failed', text: null, source: `Translation failed: ${e.message}` }; }
        if ((t.status === 'unavailable' || t.status === 'failed') && ai !== local) { const f = await local.translate(wb.raw.get(s.case_id)); if (f.status === 'fixture') t = f; }
        wb.auditLog(user, 'translate', s.case_id, { status: t.status });
        return send(res, 200, { ...t, text: t.text, note: t.status === 'unavailable' || t.status === 'failed' ? 'No translation. The case is NOT treated as low risk; it stays in human review.' : null });
      }
      return send(res, 404, { error: 'Unknown endpoint' });
    }
    if (path === '/api/policy/ask' && req.method === 'POST') {
      const { question } = await body(req);
      let a; try { a = await ai.policyQA(question); } catch (e) { a = { ...(await local.policyQA(question)), note: `Live AI failed (${e.message}); answered from local retrieval.` }; }
      wb.auditLog(user, 'policy_question', null, { covered: a.covered });
      return send(res, 200, a);
    }
    if (path === '/api/config/automation' && req.method === 'POST') {
      const { mode, idempotency_key } = await body(req);
      const r = wb.setAutomationMode(user, mode, idempotency_key);
      return send(res, r.ok ? 200 : r.code, r);
    }
    if (path === '/api/demo/signal' && req.method === 'POST') {
      if (user.role !== 'duty_manager') return send(res, 403, { error: 'Demo control: duty managers only.' });
      const { case_id } = await body(req);
      wb.auditLog(user, 'demo_signal', case_id, {});
      return send(res, 200, wb.ingestSignal(case_id, { signal: 'live_sos_new', label: 'DEMO: new live SOS pressed' }));
    }
    if (path === '/api/export') {
      if (user.role !== 'duty_manager') { wb.auditLog(user, 'denied_export', null, {}); return send(res, 403, { error: 'Exports are restricted to duty managers.' }); }
      const rows = applyFilters(wb.visible(user), filtersFrom(url)).map((s) => exportRow(s, now()));
      wb.auditLog(user, 'export', null, { rows: rows.length, format: url.searchParams.get('format') || 'json' });
      return url.searchParams.get('format') === 'csv' ? send(res, 200, toCSV(rows), 'text/csv; charset=utf-8') : send(res, 200, rows);
    }
    if (path === '/api/audit') {
      if (user.role !== 'duty_manager') return send(res, 403, { error: 'Duty managers only.' });
      return send(res, 200, audit.tail(400).reverse());
    }
    return send(res, 404, { error: 'Unknown endpoint' });
  }

  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x');
    try {
      if (url.pathname.startsWith('/api/')) return await api(req, res, url);
      let p = normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '');
      if (p === '/' || p.endsWith('/')) p += 'index.html';
      const file = join(ROOT, p);
      if (!file.startsWith(ROOT) || STATIC_DENY.test(file) || /candidate_cases\.json$/.test(file)) return send(res, 404, 'Not found', 'text/plain');
      if ((await stat(file)).isFile()) return send(res, 200, await readFile(file), TYPES[extname(file)] || 'application/octet-stream');
      send(res, 404, 'Not found', 'text/plain');
    } catch (e) {
      if (e.code === 'ENOENT') return send(res, 404, 'Not found', 'text/plain');
      send(res, e.code === 413 ? 413 : 500, { error: e.message });
    }
  });
  return { server, wb, now, ai };
}
