// RideNova Safety Console — UI. Vanilla ES modules, no build step.
import { triageAll, finalize, queueCompare, buildDuplicateIndex } from './triage.js';
import { detectProvider } from './ai.js';
import { unifiedFacts, SOURCES } from './signals.js';
import { redactText, displayParty, ROLES } from './pii.js';
import { Store, toCSV } from './store.js';
import { policyById, TIERS, ACTIONS } from './policy.js';
import { CATEGORY_GLOSS } from './simulated.js';

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const fmtUtc = (iso) => { const d = new Date(iso); return d.toLocaleString('en-GB', { timeZone: 'UTC', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) + ' UTC'; };
const LANE_LABEL = { all: 'All', critical: 'Critical', priority: 'Priority', standard: 'Standard', auto: 'Auto-resolved', decided: 'Decided' };
const KIND_CLASS = { allegation: 'k-allegation', system: 'k-system', history: 'k-history', evidence: 'k-evidence', ai: 'k-ai', pii: 'k-pii', rule: 'k-rule' };
const KIND_LABEL = { allegation: 'Reported allegation', system: 'System signal', history: 'Historical', evidence: 'Submitted evidence', ai: 'AI interpretation', pii: 'Personal data', rule: 'Deterministic rule' };

const S = {
  cases: [], byId: new Map(), rec: new Map(), live: new Map(), parentOf: new Map(), provider: null, store: new Store(),
  role: 'specialist', lane: 'all', q: '', f: { region: '', country: '', language: '', tier: '' }, page: 1, sel: null,
  revealed: {}, translations: {}, precomputed: {}, results: null, view: 'queue', choice: 'approve',
};
const record = (id) => S.live.get(id) || S.rec.get(id);

function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.remove('on'), 2600); }

async function init() {
  const [cases, pre, results] = await Promise.all([
    fetch('data/candidate_cases.json').then((r) => r.json()),
    fetch('data/precomputed_translations.json').then((r) => r.json()).catch(() => ({})),
    fetch('validation/results.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]);
  S.cases = cases; S.byId = new Map(cases.map((c) => [c.case_id, c])); S.precomputed = pre; S.results = results;
  S.parentOf = buildDuplicateIndex(cases);
  const t0 = performance.now();
  S.rec = triageAll(cases);
  S.triageMs = Math.round(performance.now() - t0);
  S.provider = await detectProvider(pre);
  const info = S.provider.info();
  const m = $('#mode');
  m.classList.toggle('live', info.mode === 'live');
  m.querySelector('span').textContent = info.mode === 'live' ? `Live AI · ${info.model}` : 'Demo · simulated AI (no key)';
  m.title = info.mode === 'live' ? 'Live AI available. Initial triage is simulated; run live AI per case.' : 'No AI key. All AI output is SIMULATED by a deterministic rules+lexicon stand-in.';
  buildFilters(); bind(); renderAlerts(); renderQueue();
  const first = [...S.rec.values()].sort(queueCompare)[0];
  select(first.case_id);
  S.store.log(S.role, 'session_start', null, { mode: info.mode, cases: cases.length });
  $('#loader').remove();
}

function buildFilters() {
  const opts = (key, label) => ['', ...new Set(S.cases.map((c) => c[key]))].sort().map((v) => `<option value="${esc(v)}">${v ? esc(v) : label}</option>`).join('');
  $('#f-region').innerHTML = opts('region_group', 'Region');
  $('#f-country').innerHTML = ['', ...new Set(S.cases.map((c) => c.country))].sort().map((v) => `<option value="${v}">${v ? `${v} · ${esc(S.cases.find((c) => c.country === v).country_name)}` : 'Country'}</option>`).join('');
  $('#f-language').innerHTML = opts('language', 'Language');
  $('#f-tier').innerHTML = '<option value="">Tier</option>' + ['L4', 'L3', 'L2', 'L1'].map((t) => `<option>${t}</option>`).join('');
  $('#qa-samples').innerHTML = ['Does a USD 40 cleaning fee count as property damage?', 'Driver has a prior flag for the same thing — what changes?', 'Can a driver refuse a service animal?', 'Rider asked for my number and threatened me', 'What is the refund for airport tolls?']
    .map((q) => `<button class="chip" style="border:0;cursor:pointer" data-q="${esc(q)}">${esc(q)}</button>`).join('');
}

function bind() {
  $('#q').addEventListener('input', (e) => { S.q = e.target.value.trim().toLowerCase(); S.page = 1; renderQueue(); });
  for (const k of ['region', 'country', 'language', 'tier']) $(`#f-${k}`).addEventListener('change', (e) => { S.f[k] = e.target.value; S.page = 1; renderQueue(); });
  $('#role').addEventListener('change', (e) => { S.role = e.target.value; S.revealed = {}; S.store.log(S.role, 'role_switch'); renderQueue(); if (S.sel) renderDetail(); renderAlerts(); toast(ROLES[S.role].label + ' — ' + ROLES[S.role].note); });
  document.querySelectorAll('.tab').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
  $('#btn-critical').addEventListener('click', () => { setView('queue'); S.lane = 'critical'; S.page = 1; renderQueue(); });
  $('#btn-policy').addEventListener('click', () => $('#drawer').classList.add('on'));
  $('#drawer-close').addEventListener('click', () => $('#drawer').classList.remove('on'));
  $('#qa-go').addEventListener('click', askPolicy);
  $('#qa-samples').addEventListener('click', (e) => { const q = e.target.dataset.q; if (q) { $('#qa-in').value = q; askPolicy(); } });
  $('#btn-csv').addEventListener('click', () => exportRows('csv'));
  $('#btn-json').addEventListener('click', () => exportRows('json'));
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input,textarea,select') || S.view !== 'queue') return;
    if (e.key === 'j' || e.key === 'k') { const ids = filtered().map((r) => r.case_id); const i = ids.indexOf(S.sel); const n = ids[Math.max(0, Math.min(ids.length - 1, i + (e.key === 'j' ? 1 : -1)))]; if (n) select(n); }
  });
}

function setView(v) {
  S.view = v;
  document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b.dataset.view === v));
  $('#v-queue').hidden = v !== 'queue'; $('#v-overview').hidden = v !== 'overview'; $('#v-audit').hidden = v !== 'audit';
  if (v === 'overview') renderOverview();
  if (v === 'audit') renderAudit();
}

function filtered(laneOverride) {
  const lane = laneOverride ?? S.lane;
  const q = S.q;
  const out = [];
  for (const c of S.cases) {
    const r = record(c.case_id);
    if (S.f.region && c.region_group !== S.f.region) continue;
    if (S.f.country && c.country !== S.f.country) continue;
    if (S.f.language && c.language !== S.f.language) continue;
    if (S.f.tier && r.predicted_tier !== S.f.tier) continue;
    const decided = !!S.store.state.decisions[c.case_id];
    if (lane === 'decided' ? !decided : lane !== 'all' && (r.lane !== lane || decided)) continue;
    if (q && !(c.case_id.toLowerCase().includes(q) || c.report_text.toLowerCase().includes(q) || c.city.toLowerCase().includes(q) || c.country_name.toLowerCase().includes(q) || (r.ai.category || '').includes(q) || r.flags.join(' ').includes(q))) continue;
    out.push(r);
  }
  return out.sort(queueCompare);
}

function renderQueue() {
  const counts = {};
  for (const l of Object.keys(LANE_LABEL)) counts[l] = filtered(l).length;
  $('#lanes').innerHTML = Object.entries(LANE_LABEL).map(([k, v]) => `<button class="lane ${S.lane === k ? 'active' : ''}" data-lane="${k}">${v}<b>${counts[k]}</b></button>`).join('');
  $('#lanes').querySelectorAll('.lane').forEach((b) => b.addEventListener('click', () => { S.lane = b.dataset.lane; S.page = 1; renderQueue(); }));
  const list = filtered();
  const show = list.slice(0, S.page * 80);
  $('#qcount').textContent = `${list.length.toLocaleString()} cases`;
  $('#qlist').innerHTML = show.map((r) => {
    const c = S.byId.get(r.case_id);
    const d = S.store.state.decisions[r.case_id];
    const st = d ? `✓ ${d.human_decision}` : r.auto_resolved ? 'auto' : r.alert ? '<span style="color:var(--red)">● alert</span>' : '';
    const icons = (r.flags.includes('injection_detected') ? ' ⚑' : '') + (r.flags.includes('conflicting_signals') ? ' ⇄' : '') + (r.flags.includes('duplicate') ? ' ⧉' : '') + (S.live.has(r.case_id) ? ' ✦' : '');
    return `<div class="qitem ${S.sel === r.case_id ? 'sel' : ''}" data-id="${r.case_id}">
      <span class="tier ${r.predicted_tier}">${r.predicted_tier}</span>
      <div><div class="t1">${r.case_id}<span style="color:var(--g500);font-weight:500">${icons}</span></div>
        <div class="t2">${esc(CATEGORY_GLOSS[r.ai.category] || r.ai.summary)}</div>
        <div class="t3">${esc(c.city)}, ${c.country} · ${c.language} · due ${fmtUtc(r.deadline_utc)}</div></div>
      <div class="st">${st}</div></div>`;
  }).join('') + (list.length > show.length ? `<button class="btn btn-gray btn-sm more" id="more">Show more (${(list.length - show.length).toLocaleString()})</button>` : '') + (list.length ? '' : '<div class="empty">No cases match</div>');
  $('#qlist').querySelectorAll('.qitem').forEach((el) => el.addEventListener('click', () => select(el.dataset.id)));
  $('#more')?.addEventListener('click', () => { S.page++; renderQueue(); });
}

function renderAlerts() {
  const open = [...S.rec.values()].filter((r) => r.alert && !S.store.state.decisions[r.case_id] && !S.store.state.audit.some((e) => e.event === 'alert_ack' && e.case_id === r.case_id));
  $('#alertbar').classList.toggle('on', open.length > 0);
  $('#v-queue').classList.toggle('alerting', open.length > 0);
  $('#alerttext').textContent = `${open.length} critical (L4) cases — duty manager alerted, awaiting human acknowledgement. Automation will not close, downgrade or resolve these.`;
}

function select(id) {
  S.sel = id; S.choice = 'approve'; S.revealed = {};
  S.store.log(S.role, 'open_case', id);
  document.querySelectorAll('.qitem').forEach((el) => el.classList.toggle('sel', el.dataset.id === id));
  renderDetail();
  $('#detail').scrollTop = 0;
}

function textForRole(c) {
  if (S.revealed.text) return esc(c.report_text);
  return esc(redactText(c.report_text, c)).replace(/\[([A-Z_]+)\]/g, '<span class="tok">$1</span>');
}

function srcBadge(sourceKey) {
  const s = SOURCES[sourceKey];
  return `<span class="src ${KIND_CLASS[s.kind]}" title="${esc(KIND_LABEL[s.kind])} — ${esc(s.hint)}">${esc(s.name)}</span>`;
}

function renderDetail() {
  const c = S.byId.get(S.sel); const r = record(S.sel); if (!c) return;
  const d = S.store.state.decisions[c.case_id];
  const role = ROLES[S.role];
  const facts = unifiedFacts(c);
  const group = (k) => facts.filter((f) => f.source === k).map((f) => `<div class="fact"><span class="l">${esc(f.label)}</span><span>${esc(f.value)}</span></div>`).join('');
  const parties = c.pii ? [['Reporter', c.pii.reporter, 'reporter', c.reporter_role], ['Reported party', c.pii.reported_party, 'reported', c.reported_party_role]] : [];
  const canReveal = role.reveal && r.predicted_tier !== 'L1';
  const partyBox = ([label, p, key, roleName]) => {
    if (!p) return `<div class="box"><b>${label}</b><div><span class="muted">Not available (missing record)</span></div></div>`;
    const shown = displayParty(p, S.role, S.revealed[key] || {});
    const row = (f, l) => shown[f] === undefined ? '' : `<div><span class="muted">${l}</span><span>${esc(shown[f])} ${canReveal && !(S.revealed[key] || {})[f] ? `<button class="reveal" data-p="${key}" data-f="${f}">reveal</button>` : ''}</span></div>`;
    return `<div class="box"><b>${label}</b> <span class="muted">(${esc(roleName)})</span>${row('name', 'Name')}${row('phone', 'Phone')}${row('email', 'Email')}${row('vehicle_plate', 'Plate')}</div>`;
  };
  const tr = S.translations[c.case_id];
  const ai = r.ai;
  const live = ai.mode === 'live';
  const canDecide = S.role !== 'auditor' && (TIERS[r.predicted_tier].rank <= TIERS[role.maxTier].rank);

  $('#detail').innerHTML = `<div class="detail-inner">
    <div class="dhead">
      <span class="tier bigtier ${r.predicted_tier}">${r.predicted_tier}</span>
      <div><h1>${c.case_id}</h1>
        <div class="sub">${esc(TIERS[r.predicted_tier].name)} · ${esc(r.predicted_action)} · ${esc(c.city)}, ${esc(c.country_name)} · ${esc(c.region_group)} · submitted ${esc(c.submitted_at.replace('T', ' '))} local (${fmtUtc(r.submitted_utc)})<br>
        First response due <b>${fmtUtc(r.deadline_utc)}</b> (SLA ${TIERS[r.predicted_tier].slaMin >= 60 ? TIERS[r.predicted_tier].slaMin / 60 + 'h' : TIERS[r.predicted_tier].slaMin + ' min'}) · lane <b>${r.lane}</b>${r.parent_case ? ` · follow-up of <a href="#" data-goto="${r.parent_case}">${r.parent_case}</a>` : ''}</div></div>
      <div class="right"><button class="btn btn-gray btn-sm" id="prev">↑ Prev</button><button class="btn btn-gray btn-sm" id="next">Next ↓</button></div>
    </div>
    ${r.alert ? `<div class="banner red"><span class="pulse"></span><div class="grow"><strong>Duty manager alerted — SP-7 danger signal</strong>Locked: automation cannot close, downgrade or resolve. Contact the reporter now; consider emergency services.</div>${S.role === 'duty' ? '<button class="btn btn-white btn-sm" id="ack">Acknowledge</button>' : '<span class="chip" style="background:rgba(255,255,255,.2);color:#fff">Duty manager only</span>'}</div>` : ''}
    ${r.flags.includes('injection_detected') ? '<div class="banner amber"><b>⚑</b><div class="grow"><strong>Prompt injection detected in report text</strong>The text contains instructions aimed at the triage system. They were treated as data and ignored; the case is routed to a specialist.</div></div>' : ''}
    ${r.auto_resolved ? `<div class="banner gray"><b>✓</b><div class="grow"><strong>Auto-resolved under SP-1${r.qa_sample ? ' · selected for 5% QA sample' : ''}</strong>Every gate passed: L1, confidence ≥ 0.75, no safety, history, injection or missing-data flags. A reviewer can still override.</div></div>` : ''}
    <div class="grid2">
      <div class="stack">
        <div class="panel"><div class="ph">${srcBadge('ticket')}<h3>Report</h3><div class="r"><span class="chip">${esc(c.language)}</span><span class="chip">${esc(c.channel)}</span>
          ${c.language !== 'en' || tr ? '' : ''}<button class="btn btn-gray btn-sm" id="translate">${tr ? 'Re-translate' : 'Translate'}</button>
          ${role.reveal && !S.revealed.text ? '<button class="btn btn-gray btn-sm" id="reveal-text">Unmask</button>' : ''}</div></div>
          <div class="pb"><div class="report">${textForRole(c)}</div>
          ${tr ? `<div class="translation"><div class="lab">${tr.mode === 'live' ? 'Live AI translation' : tr.mode === 'precomputed' ? 'Precomputed translation' : tr.mode === 'none' ? 'Original' : 'Simulated — not a translation'}</div>${esc(tr.text)}<div class="muted" style="font-size:12px;margin-top:6px">${esc(tr.source)}</div></div>` : ''}
          <div class="muted" style="font-size:12px;margin-top:12px">Unverified allegation from the reporter. Personal details are masked${role.reveal ? '; unmasking is logged with a reason' : ''}.</div></div></div>
        <div class="panel"><div class="ph"><h3>Unified sources</h3><div class="r"><span class="muted" style="font-size:12px">Each fact keeps its source system</span></div></div><div class="pb">
          <div class="srcrow">${srcBadge('telematics')}<b>Telematics</b></div>${group('telematics')}
          <div class="srcrow">${srcBadge('toolkit')}<b>Safety toolkit</b></div>${group('toolkit')}
          <div class="srcrow">${srcBadge('evidence')}<b>Attachments</b></div>${group('evidence')}
          <div class="srcrow">${srcBadge('trip')}<b>Trip</b></div>${group('trip')}
          <div class="srcrow">${srcBadge('history')}<b>Case history</b></div>${group('history')}
          <div class="srcrow">${srcBadge('ticket')}<b>Ticket metadata</b></div>${group('ticket')}
        </div></div>
        <div class="panel"><div class="ph">${srcBadge('identity')}<h3>Parties</h3><div class="r"><span class="muted" style="font-size:12px">${esc(role.note)}</span></div></div>
          <div class="pb"><div class="party">${parties.map(partyBox).join('')}</div>
          ${c.pii ? `<div class="fact" style="margin-top:8px"><span class="l">Pickup / drop-off</span><span>${S.role === 'auditor' ? 'hidden' : esc(S.revealed.addr ? `${c.pii.pickup_address} → ${c.pii.dropoff_address}` : `${maskAddr(c.pii.pickup_address)} → ${maskAddr(c.pii.dropoff_address)}`)} ${canReveal && !S.revealed.addr && c.pii.pickup_address ? '<button class="reveal" data-p="addr">reveal</button>' : ''}</span></div>` : ''}</div></div>
      </div>
      <div class="stack">
        <div class="panel"><div class="ph">${srcBadge('ai')}<h3>Proposal</h3><div class="r"><span class="chip" style="${live ? 'background:#e6f2ec;color:#03703c' : 'background:#fff3d6;color:#8a5a00'}">${live ? 'LIVE · ' + esc(ai.model) : 'SIMULATED · no AI key'}</span>
          ${S.provider.info().mode === 'live' ? `<button class="btn btn-black btn-sm" id="runlive">${live ? 'Re-run' : 'Run live AI'}</button>` : ''}</div></div>
          <div class="pb"><div class="ai-sum">${esc(ai.summary)}</div>
          <div class="proposal">
            <div class="cell"><div class="l">AI proposed</div><div class="v"><span class="tier ${ai.tier}">${ai.tier}</span></div><div class="muted" style="font-size:11px;margin-top:4px">${esc(ai.action)}</div></div>
            <div class="cell"><div class="l">After guardrails</div><div class="v"><span class="tier ${r.predicted_tier}">${r.predicted_tier}</span></div><div class="muted" style="font-size:11px;margin-top:4px">${esc(r.predicted_action)}</div></div>
            <div class="cell"><div class="l">Confidence</div><div class="v">${Math.round(r.confidence * 100)}%</div><div class="meter"><i style="width:${r.confidence * 100}%"></i></div></div>
          </div>
          <div class="rationale">${esc(ai.rationale)}</div>
          <div class="chips">${r.policy_refs.map((p) => `<span class="chip cite" title="${esc(policyById[p]?.text)}">${p}</span>`).join('')}${r.flags.map((f) => `<span class="chip flag ${['safety_feature_used', 'prior_flags', 'duplicate', 'auto_resolve_blocked'].includes(f) ? 'info' : ''}">${esc(f.replace(/_/g, ' '))}</span>`).join('')}</div>
          ${r.guardrail_changes.length ? `<div class="changes"><div class="srcrow" style="margin:4px 0 0">${srcBadge('rules')}<b>Guardrail adjustments</b></div>${r.guardrail_changes.map((g) => `<div class="change"><code>${esc(g.rule)}</code><span>${esc(g.from)} → <b>${esc(g.to)}</b> — ${esc(g.why)}</span></div>`).join('')}</div>` : ''}
          </div></div>
        <div class="panel decision"><div class="ph"><h3>Human decision</h3><div class="r"><span class="muted" style="font-size:12px">as ${esc(role.label)}</span></div></div><div class="pb">
          ${d ? `<div class="decided"><b>${esc(d.human_decision.toUpperCase())}</b> → ${esc(d.final_tier)} / ${esc(d.final_action)} · ${esc(d.decided_by_role)} · ${fmtUtc(d.decided_at)}<br><span class="muted">“${esc(d.human_reason)}”</span></div>` : ''}
          ${canDecide ? `
          <div class="opts">
            <button class="opt ${S.choice === 'approve' ? 'on' : ''}" data-c="approve"><b>Approve</b><span>Accept ${r.predicted_tier} · ${r.predicted_action.replace(/_/g, ' ').toLowerCase()}</span></button>
            <button class="opt ${S.choice === 'override' ? 'on' : ''}" data-c="override"><b>Override</b><span>Change tier / action</span></button>
            <button class="opt ${S.choice === 'escalate' ? 'on' : ''}" data-c="escalate"><b>Escalate</b><span>Raise to ${TIERS[r.predicted_tier].rank >= 3 ? 'L4 duty manager' : 'L3 specialist'}</span></button>
          </div>
          <div class="ovr ${S.choice === 'override' ? 'on' : ''}">
            <select id="o-tier" class="field">${['L1', 'L2', 'L3', 'L4'].map((t) => `<option ${t === r.predicted_tier ? 'selected' : ''}>${t}</option>`).join('')}</select>
            <select id="o-action" class="field">${ACTIONS.map((a) => `<option ${a === r.predicted_action ? 'selected' : ''}>${a}</option>`).join('')}</select>
          </div>
          <textarea id="reason" placeholder="Reason (required) — what you checked and why"></textarea>
          <div class="err" id="derr"></div>
          <button class="btn btn-black" id="submit">Record decision</button>`
          : `<div class="muted" style="font-size:14px">${S.role === 'auditor' ? 'Auditors review decisions but cannot make them.' : `${esc(role.label)} cannot decide ${r.predicted_tier} cases. Switch role to Specialist or Duty manager.`}</div>`}
        </div></div>
        <div class="panel"><div class="pb"><details class="json"><summary>Structured record (exported fields, no PII)</summary><pre>${esc(JSON.stringify({ ...S.store.row(r), guardrail_changes: r.guardrail_changes, ai: { ...r.ai, translation: undefined } }, null, 2))}</pre></details></div></div>
      </div>
    </div></div>`;

  const ids = () => filtered().map((x) => x.case_id);
  $('#prev').onclick = () => { const a = ids(); const i = a.indexOf(S.sel); if (i > 0) select(a[i - 1]); };
  $('#next').onclick = () => { const a = ids(); const i = a.indexOf(S.sel); if (i < a.length - 1) select(a[i + 1]); };
  $('#detail').querySelectorAll('[data-goto]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); select(a.dataset.goto); }));
  $('#translate').onclick = async () => {
    $('#translate').disabled = true;
    try { S.translations[c.case_id] = await S.provider.translate(c); S.store.log(S.role, 'translate', c.case_id, { mode: S.translations[c.case_id].mode }); }
    catch (e) { toast('Translation failed: ' + e.message); }
    renderDetail();
  };
  $('#reveal-text') && ($('#reveal-text').onclick = () => reveal('text'));
  $('#detail').querySelectorAll('.reveal').forEach((b) => b.addEventListener('click', () => reveal(b.dataset.p, b.dataset.f)));
  $('#ack') && ($('#ack').onclick = () => { S.store.log(S.role, 'alert_ack', c.case_id); renderAlerts(); toast('Alert acknowledged and logged'); });
  $('#runlive') && ($('#runlive').onclick = runLive);
  $('#detail').querySelectorAll('.opt').forEach((b) => b.addEventListener('click', () => { S.choice = b.dataset.c; renderDetail(); }));
  $('#submit') && ($('#submit').onclick = () => {
    const res = S.store.decide(r, { decision: S.choice, tier: $('#o-tier')?.value, action: $('#o-action')?.value, reason: $('#reason').value }, S.role);
    if (!res.ok) { $('#derr').textContent = res.error; return; }
    toast(`Decision recorded: ${res.decision.final_tier} / ${res.decision.final_action}`);
    renderAlerts(); renderQueue(); renderDetail();
  });
}

const maskAddr = (a) => (a ? '•••, ' + a.split(',').slice(-1)[0].replace('(fictional)', '').trim() : '—');

function reveal(part, field) {
  const reason = prompt('Reason for viewing personal data (logged):');
  if (!reason || reason.trim().length < 5) { toast('A reason is required to view personal data'); return; }
  if (part === 'text' || part === 'addr') S.revealed[part] = true;
  else S.revealed[part] = { ...(S.revealed[part] || {}), [field]: true };
  S.store.log(S.role, 'pii_reveal', S.sel, { part, field: field || null, reason: reason.trim() });
  renderDetail();
}

async function runLive() {
  const c = S.byId.get(S.sel);
  const btn = $('#runlive'); btn.disabled = true; btn.textContent = 'Running…';
  try {
    const proposal = await S.provider.triage(c);
    const pid = S.parentOf.get(c.case_id);
    const rec = finalize(c, proposal, { parent: pid ? { case_id: pid, tier: record(pid).predicted_tier } : null });
    S.live.set(c.case_id, rec);
    if (proposal.translation) S.translations[c.case_id] = { mode: 'live', text: proposal.translation, source: `Claude (${proposal.model}) — redacted input` };
    S.store.log(S.role, 'ai_call', c.case_id, { task: 'triage', model: proposal.model, ai_tier: proposal.tier, final_tier: rec.predicted_tier });
    toast('Live AI groundwork complete — guardrails applied');
  } catch (e) { toast('Live AI unavailable: ' + e.message + ' — keeping simulated output'); }
  renderQueue(); renderDetail();
}

async function askPolicy() {
  const q = $('#qa-in').value.trim(); if (!q) return;
  $('#qa-out').innerHTML = '<div class="qa-ans">Thinking…</div>';
  const a = await S.provider.policyQA(q).catch((e) => ({ covered: false, answer: 'Error: ' + e.message, citations: [], mode: 'error' }));
  S.store.log(S.role, 'policy_question', S.sel, { covered: a.covered, citations: a.citations, mode: a.mode });
  $('#qa-out').innerHTML = `<div class="qa-ans ${a.covered ? '' : 'nc'}"><div class="chips" style="margin:0 0 10px">${a.covered ? a.citations.map((c) => `<span class="chip cite">${c}</span>`).join('') : '<span class="chip flag">Not covered</span>'}<span class="chip">${esc(a.mode)}</span></div>${esc(a.answer)}</div>`;
}

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = Object.assign(document.createElement('a'), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function exportRows(fmt) {
  const rows = filtered(S.view === 'queue' ? S.lane : 'all').map((r) => S.store.row(r));
  S.store.log(S.role, 'export', null, { format: fmt, rows: rows.length, filters: { ...S.f, lane: S.lane, q: S.q } });
  if (fmt === 'csv') download(`ridenova_cases_${rows.length}.csv`, toCSV(rows), 'text/csv');
  else download(`ridenova_cases_${rows.length}.json`, JSON.stringify(rows, null, 1), 'application/json');
  toast(`Exported ${rows.length.toLocaleString()} records (no personal data)`);
}

function renderOverview() {
  const all = [...S.rec.values()];
  const n = all.length;
  const by = (f) => all.reduce((m, r) => ((m[f(r)] = (m[f(r)] || 0) + 1), m), {});
  const tiers = by((r) => r.predicted_tier), lanes = by((r) => r.lane);
  const flags = all.flatMap((r) => r.flags).reduce((m, f) => ((m[f] = (m[f] || 0) + 1), m), {});
  const pct = (a) => ((100 * a) / n).toFixed(1) + '%';
  const human = n - (lanes.auto || 0);
  const res = S.results;
  const sil = res?.silver, gold = res?.gold;
  const regions = ['EMEA', 'US&C', 'APAC', 'LatAm'];
  const rt = (reg, t) => all.filter((r) => r.region === reg && r.predicted_tier === t).length;
  $('#v-overview').innerHTML = `
    <div class="eyebrow">Overview · ${n.toLocaleString()} cases · 1–7 Mar 2026 sample (×20 = weekly)</div>
    <h1 style="font-size:40px;margin-top:8px">Where the week’s work goes</h1>
    <p class="muted" style="margin-top:8px;max-width:760px">All figures below are <b>measured</b> by running this prototype’s simulated provider + guardrails over the full file in your browser (${S.triageMs} ms). Weekly figures multiply by 20. They are prototype outputs, not production results.</p>
    <div class="kpis">
      <div class="kpi"><div class="v">${(lanes.critical || 0).toLocaleString()}</div><div class="l">L4 critical — duty manager alerted (${pct(lanes.critical || 0)})</div><span class="chip tag-measured">Measured · ${(20 * (lanes.critical || 0)).toLocaleString()}/wk</span></div>
      <div class="kpi"><div class="v">${(lanes.priority || 0).toLocaleString()}</div><div class="l">L3 specialist review (${pct(lanes.priority || 0)})</div><span class="chip tag-measured">Measured · ${(20 * (lanes.priority || 0)).toLocaleString()}/wk</span></div>
      <div class="kpi"><div class="v">${(lanes.standard || 0).toLocaleString()}</div><div class="l">Standard human queue (L1/L2)</div><span class="chip tag-measured">Measured · ${(20 * (lanes.standard || 0)).toLocaleString()}/wk</span></div>
      <div class="kpi"><div class="v">${pct(lanes.auto || 0)}</div><div class="l">Auto-resolvable under SP-1 (all L1, 5% QA sampled)</div><span class="chip tag-measured">Measured · ${(lanes.auto || 0).toLocaleString()} cases</span></div>
      <div class="kpi"><div class="v">${(20 * human).toLocaleString()}</div><div class="l">Cases needing a human per week (vs 100,000)</div><span class="chip tag-estimate">Estimate (×20)</span></div>
    </div>
    <div class="two">
      <div class="panel"><div class="ph"><h3>Tier mix</h3></div><div class="pb"><div class="bars">${['L4', 'L3', 'L2', 'L1'].map((t) => `<div class="bar"><span class="tier ${t}">${t}</span><div class="track"><div class="fill" style="width:${(100 * (tiers[t] || 0)) / n}%;background:var(--${t.toLowerCase()})"></div></div><span>${(tiers[t] || 0).toLocaleString()} · ${pct(tiers[t] || 0)}</span></div>`).join('')}</div>
        <p class="muted" style="font-size:12px;margin-top:12px">Brief’s illustrative mix: 2% / 8% / 20% / 70%. L4 is higher here (2.8%) mainly because SP-9 lifts post-trip location exposure with a prior flag from L3 to L4 — a policy reading leadership should confirm.</p></div></div>
      <div class="panel"><div class="ph"><h3>Region × tier</h3></div><div class="pb"><table class="t"><tr><th>Region</th><th>L4</th><th>L3</th><th>L2</th><th>L1</th></tr>${regions.map((g) => `<tr><td><b>${g}</b></td>${['L4', 'L3', 'L2', 'L1'].map((t) => `<td>${rt(g, t)}</td>`).join('')}</tr>`).join('')}</table></div></div>
      <div class="panel"><div class="ph"><h3>Flags raised</h3></div><div class="pb"><table class="t">${Object.entries(flags).sort((a, b) => b[1] - a[1]).map(([f, v]) => `<tr><td>${esc(f.replace(/_/g, ' '))}</td><td style="text-align:right"><b>${v}</b></td></tr>`).join('')}</table></div></div>
      <div class="panel"><div class="ph"><h3>Validation</h3><div class="r"><span class="chip tag-measured">Measured</span></div></div><div class="pb">
        ${sil ? `<table class="t">
          <tr><td>Silver reference (all 5,000; scenario-level labels)</td><td><b>${((100 * sil.tier_exact) / sil.n).toFixed(1)}%</b> tier match</td></tr>
          <tr><td>L4 recall</td><td><b>${sil.l4_recall[0]}/${sil.l4_recall[1]}</b></td></tr>
          <tr><td>L3+ recall</td><td><b>${sil.l3plus_recall[0]}/${sil.l3plus_recall[1]}</b></td></tr>
          <tr><td>Under-triaged (lower than label)</td><td><b>${sil.under}</b> — all routed to a human, none auto-closed</td></tr>
          <tr><td>Over-triaged (sent to human unnecessarily)</td><td><b>${sil.over}</b></td></tr>
          <tr><td>Unsafe auto-resolutions</td><td><b>${sil.unsafe_auto}</b></td></tr>
          ${gold ? `<tr><td>Gold set (30 hand-labelled)</td><td><b>${gold.tier_exact}/${gold.n}</b> tier · <b>${gold.action_exact}/${gold.n}</b> action</td></tr>` : ''}
        </table><p class="muted" style="font-size:12px;margin-top:10px">Caveat: the lexicon was tuned on this same file, so these are in-sample numbers. Expect lower accuracy on new data; that is why auto-resolution is gated and starts in shadow mode.</p>` : '<p class="muted">Run <code>npm run evaluate</code> to generate validation/results.json.</p>'}
      </div></div>
    </div>`;
}

function renderAudit() {
  const ev = [...S.store.state.audit].reverse().slice(0, 500);
  $('#v-audit').innerHTML = `<div class="eyebrow">Access log · stored locally · retention ${400} days</div>
    <h1 style="font-size:40px;margin:8px 0 8px">Who saw and did what</h1>
    <p class="muted" style="max-width:760px;margin-bottom:18px">Every case open, personal-data reveal (with reason), translation, AI call, decision, alert acknowledgement and export is logged. Content is never logged — only metadata.</p>
    <button class="btn btn-gray btn-sm" id="audit-export" style="margin-bottom:12px">Export log (JSON)</button>
    <div class="panel"><div class="pb" style="padding:0"><table class="t"><tr><th>Time (UTC)</th><th>Role</th><th>Event</th><th>Case</th><th>Detail</th></tr>
    ${ev.map((e) => `<tr><td class="mono">${esc(e.ts.replace('T', ' ').slice(0, 19))}</td><td>${esc(e.role)}</td><td><b>${esc(e.event)}</b></td><td>${esc(e.case_id || '')}</td><td class="mono" style="font-size:11px">${esc(JSON.stringify(e.detail))}</td></tr>`).join('')}</table></div></div>`;
  $('#audit-export').onclick = () => download('ridenova_access_log.json', JSON.stringify(S.store.state.audit, null, 1), 'application/json');
}

init().catch((e) => { document.body.innerHTML = `<div style="padding:40px;font-family:Inter,sans-serif"><h2>Could not load</h2><p>${esc(e.message)}</p><p>Serve the folder over HTTP (npm start or python3 -m http.server), not file://.</p></div>`; });
