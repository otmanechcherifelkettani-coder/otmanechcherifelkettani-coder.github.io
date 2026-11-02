// Safety Workbench UI. Renders server responses only; the server decides what each user can see
// and do. Hash routes: #overview, #work, #work/SC-0001.

const $ = (s, el = document) => el.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const fmt = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { timeZone: 'UTC', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) + ' UTC' : '—');
const dur = (min) => (min == null ? '' : Math.abs(min) < 60 ? `${Math.abs(min)} min` : Math.abs(min) < 2880 ? `${Math.round(Math.abs(min) / 60)} h` : `${Math.round(Math.abs(min) / 1440)} d`);
const SEV_NAME = { L4: 'L4 Critical', L3: 'L3 High', L2: 'L2 Moderate', L1: 'L1 Low' };
const sev = (t, prov) => (t ? `<span class="sev ${t} ${prov ? 'prov' : ''}" title="${prov ? 'Provisional' : ''}">${SEV_NAME[t] || t}${prov ? ' · provisional' : ''}</span>` : '<span class="tag">—</span>');
const WF = { awaiting_triage: 'Awaiting triage', assigned: 'Assigned to queue', under_review: 'Under review', awaiting_information: 'Awaiting information', resolved: 'Resolved', reopened: 'Reopened' };
const SLA_TAG = { breached: 'red', approaching: 'amber', on_track: 'green', met: 'green', missed: 'red', closed_without_response: '' };
const slaTag = (sla) => `<span class="tag ${SLA_TAG[sla.status] || ''}">${sla.status.replace(/_/g, ' ')}${sla.overdue_min ? ` · ${dur(sla.overdue_min)} over` : sla.remaining_min != null ? ` · ${dur(sla.remaining_min)} left` : ''}</span>`;
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));

const S = { token: null, user: null, meta: null, route: 'overview', sel: null, list: [], listMode: 'mine', filters: {}, adv: false, view: null, translation: {}, busy: false };
try { const t = sessionStorage.getItem('rn.session'); if (t) Object.assign(S, JSON.parse(t)); } catch { /* storage unavailable */ }

function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('on'); clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove('on'), 3200); }

async function api(path, init = {}) {
  const r = await fetch(path, { ...init, headers: { 'content-type': 'application/json', ...(S.token ? { authorization: `Bearer ${S.token}` } : {}), ...(init.headers || {}) } });
  if (r.status === 401 && S.token) { signOut(); throw new Error('Session expired'); }
  const ct = r.headers.get('content-type') || '';
  const body = ct.includes('json') ? await r.json() : await r.text();
  return { ok: r.ok, status: r.status, body };
}

// ---------- dialog helper ----------
function dialog(title, html, onOk, okLabel = 'Confirm') {
  const d = $('#dlg'); $('#dlg-title').textContent = title; $('#dlg-body').innerHTML = html; $('#dlg-err').textContent = ''; $('#dlg-ok').textContent = okLabel;
  d.showModal();
  $('#dlg-form').onsubmit = async (e) => {
    if (e.submitter?.value !== 'ok') return;
    e.preventDefault();
    const err = await onOk(new FormData($('#dlg-form')));
    if (err) $('#dlg-err').textContent = err; else d.close();
  };
}

// ---------- boot ----------
async function boot() {
  const h = await (await fetch('api/health').catch(() => null))?.json?.().catch(() => null);
  if (!h) { $('#main').innerHTML = '<div class="empty"><h2>The workbench needs its server</h2><p>Run <code>npm start</code> and open http://localhost:8080/console.html. The static pages (case solution, deck) work without it.</p></div>'; return; }
  $('#clock').textContent = `replay clock ${fmt(h.replay_now)} (simulated)`;
  const m = $('#aimode'); m.textContent = h.ai.mode === 'live' ? `Live AI · ${h.ai.model}` : 'Simulated AI (no key)'; m.classList.toggle('live', h.ai.mode === 'live');
  $('#limits').onclick = showLimits;
  if (S.token) { const r = await api('api/meta').catch(() => null); if (r?.ok) { S.meta = r.body; S.user = r.body.user; } else S.token = null; }
  window.addEventListener('hashchange', route);
  route();
}
function save() { try { sessionStorage.setItem('rn.session', JSON.stringify({ token: S.token, user: S.user })); } catch { /* ignore */ } }
function signOut() { S.token = null; S.user = null; S.meta = null; S.filters = {}; S.adv = false; S.translation = {}; save(); location.hash = ''; renderSignIn(); }

function showLimits() {
  dialog('Limitations of this prototype', `<ul class="plain" style="font-size:14px">
    <li>RideNova, its policy (SP-1..SP-9) and all 5,000 cases are fictional and synthetic. Personal data is synthetic but handled as real.</li>
    <li>Sign-in is simulated: you pick a profile. The server enforces each profile’s scope, but this is not real authentication or production RBAC.</li>
    <li>Every action (messages, credits, warnings, suspensions) runs through a <b>simulated adapter</b>; nothing is sent. Emergency services are never contacted by the system — managers record what they did.</li>
    <li>Times use a replay clock. The data has no real response timestamps, so SLA figures are not historical performance.</li>
    <li>Without an API key, AI output is simulated by rules + a multilingual lexicon. Translations shown in demo mode are fixtures where available; otherwise none.</li>
    <li>Confidence scores are uncalibrated. Validation labels were AI-drafted and have not yet been adjudicated by the candidate.</li>
    <li>Records persist in a local append-only file. It is not tamper-proof audit storage. Redaction is pattern-based, not complete anonymisation.</li>
    <li>Upstream automation starts in shadow mode. A duty manager can enable it for the fictional SP-1 demo only.</li></ul>`, async () => null, 'Close');
}

function nav() {
  const work = S.user.role === 'duty_manager' ? 'Duty-manager workspace' : 'Agent workspace';
  $('#tabs').innerHTML = `<a href="#overview" ${S.route === 'overview' ? 'aria-current="page"' : ''}>Overview</a><a href="#work" ${S.route === 'work' ? 'aria-current="page"' : ''}>${work}</a>`;
  const w = $('#who'); w.hidden = false;
  w.textContent = `${S.user.name} · ${S.user.role === 'duty_manager' ? 'Duty manager' : S.user.capabilities.length > 1 ? 'Specialist agent' : 'Agent'} · switch (simulated)`;
  w.onclick = signOut;
}

function route() {
  if (!S.token) return renderSignIn();
  const [r, id] = (location.hash.slice(1) || 'overview').split('/');
  S.route = r === 'work' ? 'work' : 'overview';
  nav();
  if (S.route === 'overview') return renderOverview();
  if (id && id !== S.sel) S.sel = id;
  return renderWork();
}

// ---------- sign-in ----------
async function renderSignIn() {
  $('#tabs').innerHTML = ''; $('#who').hidden = true;
  const users = (await api('api/users')).body;
  const card = (u) => `<button class="ucard" data-u="${u.id}"><b>${esc(u.name)}</b><span>${u.role === 'duty_manager' ? 'Duty manager · all regions · critical & danger cases' : `${u.capabilities.length > 1 ? 'Specialist agent' : 'Agent'} · ${u.regions.join(', ')}`}</span><span>${u.role === 'duty_manager' ? '' : 'Capabilities: ' + u.capabilities.map((c) => c.replace(/_/g, ' ')).join(', ')}</span></button>`;
  $('#main').innerHTML = `<div class="signin"><div class="eyebrow">Simulated sign-in</div><h1>Choose a profile</h1>
    <p class="sub">Pick a fictional user to see the workbench as they would. The server enforces each profile’s markets, lanes and capabilities on every request; the browser only receives what that profile may see.</p>
    <h2 style="font-size:16px;margin-bottom:10px">Agents</h2><div class="ugrid">${users.filter((u) => u.role === 'agent').map(card).join('')}</div>
    <h2 style="font-size:16px;margin-bottom:10px">Duty managers</h2><div class="ugrid">${users.filter((u) => u.role === 'duty_manager').map(card).join('')}</div></div>`;
  $('#main').querySelectorAll('.ucard').forEach((b) => b.onclick = async () => {
    const r = await api('api/session', { method: 'POST', body: JSON.stringify({ user_id: b.dataset.u }) });
    S.token = r.body.token; S.user = r.body.user; S.meta = (await api('api/meta')).body; S.sel = null; S.listMode = 'mine'; S.filters = {}; S.adv = false; S.translation = {}; save();
    location.hash = S.user.role === 'duty_manager' ? 'work' : 'work'; route();
  });
}

// ---------- overview ----------
function scopeText(u) {
  if (u.role === 'duty_manager') return `${u.name} · duty manager · every region and lane`;
  const caps = u.capabilities.filter((c) => c !== 'general').map((c) => c.replace(/_/g, ' '));
  return `${u.name} · agent · ${u.regions.join(', ')} · agent-lane cases${caps.length ? ` incl. specialist queues (${caps.join(', ')})` : ' (general review only)'}. Duty-manager and automation cases are not in an agent’s scope`;
}
const FILTERS = [['region', 'Region'], ['country', 'Country'], ['product', 'Product'], ['language', 'Language'], ['reporter_persona', 'Reporter persona'], ['workflow', 'Workflow status']];
const ADV = [['owner', 'Owner'], ['queue', 'Queue'], ['escalation_reason', 'Escalation reason'], ['automation_outcome', 'Automation outcome'], ['policy_version', 'Policy version']];

async function renderOverview() {
  const qs = new URLSearchParams(Object.entries(S.filters).filter(([, v]) => v)).toString();
  $('#main').innerHTML = '<div class="loading">Loading overview…</div>';
  const r = await api('api/overview?' + qs);
  if (!r.ok) { $('#main').innerHTML = `<div class="empty">${esc(r.body.error)}</div>`; return; }
  const o = r.body; const f = S.filters; const n = o.population;
  const basis = f.severity_basis || 'current';
  const sel = (k, label, opts) => `<label>${label}<select class="select" data-f="${k}"><option value="">All</option>${(opts || []).map((v) => `<option ${f[k] === v ? 'selected' : ''} value="${esc(v)}">${esc(v.replace?.(/_/g, ' ') ?? v)}</option>`).join('')}</select></label>`;
  const bars = (obj, order, labels = {}) => order.map((k) => { const v = obj[k] || 0; return `<div class="bar"><span>${labels[k] || esc(k)}</span><div class="t" role="img" aria-label="${v} of ${n}"><div class="f" style="width:${n ? (100 * v) / n : 0}%"></div></div><span style="text-align:right">${v.toLocaleString()}</span></div>`; }).join('');
  const sevOrder = basis === 'reviewed' ? ['L4', 'L3', 'L2', 'L1', 'not_reviewed'] : ['L4', 'L3', 'L2', 'L1'];
  const slaRows = ['L4', 'L3', 'L2', 'L1'].map((t) => { const x = o.sla_by_tier[t]; return `<tr><td>${sev(t)}</td>${['breached', 'approaching', 'on_track', 'met', 'missed', 'closed_without_response'].map((k) => `<td class="num">${x[k]}</td>`).join('')}</tr>`; }).join('');
  const isDM = S.user.role === 'duty_manager';
  $('#main').innerHTML = `<div class="page">
    <h1>Where is operational attention needed?</h1>
    <div class="scope"><div><span class="k">Your scope</span><b>${o.scope.toLocaleString()}</b> of ${o.total.toLocaleString()} cases</div>
      <div class="small">${esc(scopeText(S.user))}. ${o.scope < o.total ? 'Other cases exist but this profile is not authorised to see them; switch profile to compare.' : 'This profile sees every case.'}</div></div>
    <p class="lede">Replay clock ${fmt(o.replay_now)}. Every breakdown below sums to the filtered population (${n.toLocaleString()}).</p>
    <div class="filters" role="search">
      <label>Date basis<select class="select" data-f="date_basis"><option value="received" ${f.date_basis !== 'decision' ? 'selected' : ''}>Received</option><option value="decision" ${f.date_basis === 'decision' ? 'selected' : ''}>Decision</option></select></label>
      <label>From<input class="input" type="date" data-f="date_from" value="${esc(f.date_from || '')}" min="2026-02-27" max="2026-03-09"></label>
      <label>To<input class="input" type="date" data-f="date_to" value="${esc(f.date_to || '')}" min="2026-02-27" max="2026-03-09"></label>
      ${FILTERS.map(([k, l]) => sel(k, l, o.options[k])).join('')}
      <label>Severity<select class="select" data-f="severity"><option value="">All</option>${['L4', 'L3', 'L2', 'L1'].map((t) => `<option ${f.severity === t ? 'selected' : ''}>${t}</option>`).join('')}</select></label>
      <label>Severity basis<select class="select" data-f="severity_basis"><option value="current" ${basis === 'current' ? 'selected' : ''}>Current operational</option><option value="proposed" ${basis === 'proposed' ? 'selected' : ''}>AI-proposed</option><option value="reviewed" ${basis === 'reviewed' ? 'selected' : ''}>Human-reviewed</option></select></label>
      <button class="btn btn-gray btn-sm" id="advbtn" aria-expanded="${S.adv}">${S.adv ? 'Fewer filters' : 'Advanced filters'}</button>
      <button class="btn btn-gray btn-sm" id="clear">Clear</button>
      <div class="adv ${S.adv ? 'on' : ''}">${ADV.map(([k, l]) => sel(k, l, o.options[k])).join('')}
        ${sel('evidence_gap', 'Evidence gap', ['any', 'missing_material'])}${sel('repeat_flag', 'Repeat-conduct flag', ['yes', 'no'])}${sel('confidence_band', 'Confidence band', ['low', 'medium', 'high'])}</div>
    </div>
    <div class="stats">
      <div class="stat"><div class="v">${n.toLocaleString()}</div><div class="k">Filtered population</div><div class="d">denominator for every chart</div></div>
      <div class="stat"><div class="v">${o.new_tickets.count.toLocaleString()}</div><div class="k">New tickets</div><div class="d">${esc(o.new_tickets.denominator)}</div></div>
      <div class="stat"><div class="v">${o.open_backlog.count.toLocaleString()}</div><div class="k">Open backlog</div><div class="d">${esc(o.open_backlog.denominator)}</div></div>
      <div class="stat"><div class="v" style="color:${o.alerts_unacknowledged ? 'var(--red)' : 'inherit'}">${o.alerts_unacknowledged}</div><div class="k">Unacknowledged critical alerts</div><div class="d">${o.alerts_total} alerts raised in total</div></div>
      <div class="stat"><div class="v">${o.provisional}</div><div class="k">Provisional / unclassified</div><div class="d">not understood or no recognised pattern</div></div>
    </div>
    <div class="grid2">
      <div class="card"><h3>Severity distribution</h3><div class="basis">Basis: <b>${{ current: 'current operational', proposed: 'AI-proposed', reviewed: 'human-reviewed' }[basis]}</b> severity</div>${bars(o.severity[basis], sevOrder, { L4: 'L4 Critical', L3: 'L3 High', L2: 'L2 Moderate', L1: 'L1 Low', not_reviewed: 'Not yet reviewed' })}</div>
      <div class="card"><h3>Handling lane</h3><div class="basis">Where each case is handled now (automation mode: <b>${esc(o.automation_mode)}</b>)</div>${bars(o.handling, ['manager', 'agent', 'automation'], { manager: 'Duty manager', agent: 'Agent review', automation: 'Automation' })}
        <div class="basis" style="margin-top:12px">Workflow status</div>${bars(o.workflow, Object.keys(WF), WF)}</div>
      <div class="card"><h3>First-response deadlines by tier</h3><div class="basis">Tier = highest tier the case has held (deadlines never loosen). Replay: the data contains no real responses, so this is <b>not</b> historical SLA performance.</div>
        <table class="t"><thead><tr><th>Tier</th><th>Breached</th><th>Approaching</th><th>On track</th><th>Met</th><th>Missed</th><th>Closed, no response</th></tr></thead><tbody>${slaRows}</tbody></table></div>
      <div class="card"><h3>Automation and exceptions</h3><div class="basis">Upstream automation never enters an agent’s queue. Outcomes come from the simulated adapter.</div>
        <table class="t"><tbody>${Object.entries(o.automation).map(([k, v]) => `<tr><td>${esc(k.replace(/_/g, ' '))}</td><td class="num">${v.toLocaleString()}</td></tr>`).join('')}
        <tr><td>Automation exceptions (sent to review)</td><td class="num">${o.exceptions.automation_exceptions}</td></tr><tr><td>Execution failures (any action)</td><td class="num">${o.exceptions.execution_failures}</td></tr><tr><td>Reopened</td><td class="num">${o.exceptions.reopened}</td></tr></tbody></table>
        ${isDM ? `<div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><button class="btn btn-sm ${o.automation_mode === 'enabled' ? 'btn-gray' : 'btn-black'}" id="automode">${o.automation_mode === 'enabled' ? 'Return automation to shadow mode' : 'Enable SP-1 automation (demo)'}</button>
          <a class="btn btn-gray btn-sm" href="#" id="csv">Export CSV</a><a class="btn btn-gray btn-sm" href="#" id="json">Export JSON</a></div>` : ''}</div>
    </div>
    <div class="card" style="margin-top:16px"><h3>Connected company systems</h3><div class="basis">Mock adapters: the workbench sits between these systems instead of replacing them. Nothing is sent to a real system.</div>
      <div class="sys">${Object.entries(S.meta.systems).map(([k, x]) => `<div><b>${esc(x.label)}</b><span class="tag">${esc(x.direction)}</span><span class="tag amber">mock</span><div class="small">${esc(x.role)}</div></div>`).join('')}</div>
      <table class="t" style="margin-top:10px"><tbody><tr><td>Tickets kept in sync (status, owner, severity, outcome)</td><td class="num">${o.integrations.tickets_synced.toLocaleString()}</td></tr>
      <tr><td>On-call pages triggered · acknowledged</td><td class="num">${o.integrations.pages_triggered} · ${o.integrations.pages_acknowledged}</td></tr>
      <tr><td>Messages sent (messaging service)</td><td class="num">${o.integrations.messaging}</td></tr><tr><td>Credits / fees (payments ledger)</td><td class="num">${o.integrations.payments}</td></tr>
      <tr><td>Blocks / suspensions (account enforcement)</td><td class="num">${o.integrations.enforcement}</td></tr><tr><td>Failed calls (sent back to a human)</td><td class="num">${o.integrations.failed_calls}</td></tr></tbody></table></div>
    ${isDM ? '<p class="recon" id="chain">Checking access-log integrity…</p>' : ''}
    <p class="recon">Evidence gaps: ${o.evidence_gaps.missing_material} missing material evidence · ${o.evidence_gaps.language_not_understood} not understood (language). Confidence bands (uncalibrated): ${Object.entries(o.confidence_bands).map(([k, v]) => `${k} ${v}`).join(' · ')}.</p>
  </div>`;
  if (isDM) api('api/audit/verify').then((x) => { const el = $('#chain'); if (!el) return; el.innerHTML = x.body.ok ? `Access log: hash chain <b>verified</b> (${x.body.entries.toLocaleString()} entries${x.body.purged_by_retention ? `, ${x.body.purged_by_retention} purged by retention` : ''}). Tamper-evident, not tamper-proof.` : `<b style="color:var(--red)">Access log integrity check FAILED</b> at entry ${x.body.broken_at}: ${esc(x.body.reason)}`; });
  $('#main').querySelectorAll('[data-f]').forEach((el) => el.onchange = () => { S.filters[el.dataset.f] = el.value; renderOverview(); });
  $('#advbtn').onclick = () => { S.adv = !S.adv; renderOverview(); };
  $('#clear').onclick = () => { S.filters = {}; renderOverview(); };
  $('#automode') && ($('#automode').onclick = () => {
    const to = o.automation_mode === 'enabled' ? 'shadow' : 'enabled';
    dialog(to === 'enabled' ? 'Enable SP-1 automation for the demo?' : 'Return to shadow mode?', to === 'enabled'
      ? '<p style="font-size:14px">Eligible fictional SP-1 cases that no human has touched will be processed upstream by the <b>simulated</b> adapter. Some will fail on purpose and come back as exceptions for human review. Nothing real is sent.</p>'
      : '<p style="font-size:14px">New eligible cases will be routed to agents again, with eligibility recorded. Already-processed cases are not undone.</p>', async () => {
      const x = await api('api/config/automation', { method: 'POST', body: JSON.stringify({ mode: to, idempotency_key: uuid() }) });
      if (!x.ok) return x.body.error; toast(to === 'enabled' ? `Automation enabled: ${x.body.moved_to_automation} cases processed upstream (simulated)` : 'Automation back in shadow mode'); renderOverview(); return null;
    });
  });
  const dl = async (fmt2) => { const x = await api(`api/export?format=${fmt2}&${qs}`); if (!x.ok) return toast(x.body.error);
    const blob = new Blob([fmt2 === 'csv' ? x.body : JSON.stringify(x.body, null, 1)], { type: fmt2 === 'csv' ? 'text/csv' : 'application/json' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `ridenova_export.${fmt2}` }); a.click(); toast('Export downloaded (no personal data; logged)'); };
  $('#csv') && ($('#csv').onclick = (e) => { e.preventDefault(); dl('csv'); });
  $('#json') && ($('#json').onclick = (e) => { e.preventDefault(); dl('json'); });
}

// ---------- workspaces ----------
async function loadList() {
  const isDM = S.user.role === 'duty_manager';
  const p = new URLSearchParams({ limit: 150 });
  if (isDM) p.set('lane', S.listMode === 'all' ? '' : 'manager');
  if (S.listMode === 'mine') p.set('mine', '1');
  if (S.listQ) p.set('q', S.listQ);
  for (const [k, v] of [...p]) if (!v) p.delete(k);
  const r = await api('api/cases?' + p);
  S.list = r.body.items || []; S.listTotal = r.body.total || 0;
}

async function renderWork() {
  const isDM = S.user.role === 'duty_manager';
  if (!$('.split')) {
    $('#main').innerHTML = `<div class="split"><section class="list" aria-label="Case list"><div class="list-head">
      <h2>${isDM ? 'Critical & danger cases' : 'My work'}</h2>
      <div class="seg" role="group" aria-label="List">${isDM ? '<button data-m="queue">Duty queue</button><button data-m="mine">Owned by me</button>' : '<button data-m="mine">My cases</button><button data-m="queue">My queues</button>'}</div>
      <input class="input" id="lq" placeholder="Search case ID, trip ID, city…" aria-label="Search cases">
      <div class="small" id="lcount"></div></div><div class="items" id="items"></div></section>
      <section class="detail" id="detail" aria-live="polite"><div class="empty">Select a case</div></section></div>`;
    $('#lq').oninput = (e) => { S.listQ = e.target.value.trim(); clearTimeout(renderWork.t); renderWork.t = setTimeout(async () => { await loadList(); drawList(); }, 250); };
    $('.seg').querySelectorAll('button').forEach((b) => b.onclick = async () => { S.listMode = b.dataset.m; await loadList(); drawList(); });
    document.addEventListener('keydown', listKeys);
  }
  if (isDM && S.listMode === 'mine' && !S.sel) S.listMode = 'queue';
  await loadList();
  if (!isDM && S.listMode === 'mine' && !S.list.length) { S.listMode = 'queue'; await loadList(); }
  drawList();
  if (!S.sel && S.list[0]) S.sel = S.list[0].case_id;
  if (S.sel) loadCase(S.sel);
}

function listKeys(e) {
  if (S.route !== 'work' || e.target.matches('input,textarea,select') || $('#dlg').open) return;
  if (e.key !== 'j' && e.key !== 'k') return;
  const i = S.list.findIndex((x) => x.case_id === S.sel);
  const n = S.list[Math.max(0, Math.min(S.list.length - 1, i + (e.key === 'j' ? 1 : -1)))];
  if (n) location.hash = `work/${n.case_id}`;
}

function drawList() {
  $('.seg').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.m === S.listMode)));
  $('#lcount').textContent = `${S.listTotal.toLocaleString()} open case${S.listTotal === 1 ? '' : 's'}${S.listTotal > S.list.length ? ` · showing ${S.list.length}` : ''} · severity, then deadline`;
  $('#items').innerHTML = S.list.length ? S.list.map((i) => `<button class="item" data-id="${i.case_id}" aria-current="${i.case_id === S.sel}">
      ${sev(i.severity)}
      <span style="min-width:0"><span class="l1">${i.case_id}${i.provisional ? '<span class="tag amber">provisional</span>' : ''}${i.unacked ? '<span class="tag red">unacknowledged</span>' : ''}${i.handoff === 'pending' ? '<span class="tag blue">handoff</span>' : ''}</span>
      <span class="l2">${esc(i.summary)}</span>
      <span class="l3"><span>${esc(i.city)}, ${i.country} · ${i.language}</span><span>${i.owner_name ? 'Owner ' + esc(i.owner_name) : 'Unowned'}</span>${slaTag(i.sla)}</span></span></button>`).join('')
    : `<div class="empty">${S.listMode === 'mine' ? 'Nothing assigned to you. Switch to your queues.' : 'No open cases in your scope.'}</div>`;
  $('#items').querySelectorAll('.item').forEach((b) => b.onclick = () => { location.hash = `work/${b.dataset.id}`; });
}

async function loadCase(id) {
  S.sel = id;
  document.querySelectorAll('.item').forEach((b) => b.setAttribute('aria-current', String(b.dataset.id === id)));
  const r = await api(`api/cases/${id}`);
  if (!r.ok) { $('#detail').innerHTML = `<div class="empty">${esc(r.body.error || 'Not available')}</div>`; return; }
  S.view = r.body; drawCase();
}

async function cmd(type, payload = {}) {
  if (S.busy) return; S.busy = true;
  const r = await api(`api/cases/${S.sel}/commands`, { method: 'POST', body: JSON.stringify({ type, payload, idempotency_key: uuid() }) });
  S.busy = false;
  if (!r.ok) { toast(r.body.error || 'Not saved'); return r.body.error || 'Not saved'; }
  S.view = r.body.case; drawCase(); await loadList(); drawList();
  toast('Saved'); return null;
}

const textHtml = (v) => esc(v.report.text).replace(/\[([A-Z_]+)\]/g, '<span class="tok">$1</span>');

function drawCase() {
  const v = S.view;
  if (v.limited) {
    $('#detail').innerHTML = `<div class="detail-inner"><div class="chead"><div><h1>${v.case_id}</h1><div class="meta">You handed this case off. You can see its status only.</div></div></div>
      <div class="statusbar"><div><span class="k">Severity</span>${sev(v.severity)}</div><div><span class="k">Lane</span>${esc(v.lane)}</div><div><span class="k">Queue</span>${esc(v.queue)}</div><div><span class="k">Status</span>${WF[v.workflow]}</div>
      <div><span class="k">Handoff</span><span class="tag ${v.handoff.status === 'accepted' ? 'green' : 'amber'}">${esc(v.handoff.status)}${v.handoff.accepted_by ? ' by ' + esc(v.handoff.accepted_by) : ''}</span></div><div><span class="k">Owner</span>${esc(v.owner_name || 'Unowned')}</div></div></div>`;
    return;
  }
  return S.user.role === 'duty_manager' && v.lane === 'manager' ? drawManagerCase(v) : drawAgentCase(v);
}

function header(v) {
  return `<div class="chead"><div><h1>${v.case_id}</h1><div class="meta">${esc(v.city)}, ${esc(v.country_name)} · ${esc(v.region)} · ${esc(v.product)} · reporter ${esc(v.reporter_persona)} → reported ${esc(v.reported_party_role)} · trip ${esc(v.trip_id)}${v.incident_id ? ` · incident ${esc(v.incident_id)}` : ''}</div></div>
      <div class="ticket" title="${esc(v.integrations.ticket.system)}: status, owner, severity and outcome are written back on every change"><span class="small">${esc(v.integrations.ticket.system)}</span><b>${esc(v.integrations.ticket.ref)}</b><span class="tag">${esc(v.integrations.ticket.status)}</span></div></div>
    <div class="statusbar">
      <div><span class="k">Current</span>${sev(v.severity.current, v.severity.provisional)}</div>
      <div><span class="k">AI proposed</span>${sev(v.severity.proposed)}</div>
      <div><span class="k">Reviewed</span>${v.severity.reviewed ? sev(v.severity.reviewed) : '<span class="tag">not yet</span>'}</div>
      <div><span class="k">Status</span><b>${WF[v.workflow]}</b></div>
      <div><span class="k">Owner</span><b>${esc(v.owner_name || 'Unowned')}</b></div>
      <div><span class="k">Queue</span>${esc(v.queue_label)}</div>
      <div><span class="k">First response</span>${slaTag(v.sla)} <span class="small">due ${fmt(v.sla.due_at)}</span></div>
    </div>`;
}

function sourcesHtml(v) {
  return v.sources.map((s) => `<details class="src"><summary>${esc(s.name)} <span class="tag ${s.kind === 'allegation' ? 'red' : s.kind === 'system' ? 'blue' : s.kind === 'history' ? '' : s.kind === 'pii' ? 'green' : 'amber'}">${{ allegation: 'allegation', system: 'system observation', history: 'historical', evidence: 'submitted evidence', pii: 'personal data (masked)' }[s.kind]}</span>
    <span class="tag ${s.status === 'ok' ? 'green' : s.status === 'error' ? 'red' : 'amber'}">${s.status}</span>${s.missing.length ? `<span class="small">missing: ${esc(s.missing.join(', '))}</span>` : ''}</summary>
    ${s.id === 'identity' ? partiesHtml(v) : s.facts.map((f) => `<div class="fact"><span class="l">${esc(f.label)}</span><span>${esc(f.value)}</span></div>`).join('')}
    <div class="fact"><span class="l">Retrieved</span><span>${fmt(s.retrieved_at)} · ${esc(s.version)}</span></div></details>`).join('');
}
function partiesHtml(v) {
  const canReveal = S.user.role === 'duty_manager' || v.owner === S.user.id;
  const row = (who, label, p) => !p ? `<div class="fact"><span class="l">${label}</span><span>Not available</span></div>` :
    Object.entries(p).map(([k, val]) => `<div class="fact"><span class="l">${label} · ${k.replace('_', ' ')}</span><span>${esc(val)} ${canReveal && /•/.test(val) ? `<button class="linkbtn" data-reveal="${who}.${k}">reveal</button>` : ''}</span></div>`).join('');
  return row('reporter', 'Reporter', v.parties.reporter) + row('reported_party', 'Reported', v.parties.reported_party) +
    (v.parties.addresses ? `<div class="fact"><span class="l">Pickup → drop-off</span><span>${esc(v.parties.addresses)} ${canReveal && /•/.test(v.parties.addresses) ? '<button class="linkbtn" data-reveal="addresses">reveal</button>' : ''}</span></div>` : '') +
    (canReveal ? '' : '<div class="small" style="padding-left:18px">Take the case to view personal data (reason required, logged).</div>');
}

function translationHtml(v) {
  const live = S.meta.ai?.mode === 'live';
  const t = S.translation[v.case_id] || v.report.translation;
  const btn = (v.language !== 'en' || v.report.translation) && live ? `<button class="btn btn-gray btn-sm" id="tr">${S.translation[v.case_id] ? 'Translate again (live AI)' : 'Translate with live AI'}</button>` : '';
  if (!t) return { btn, html: '' };
  const lab = { live: 'English · live AI translation', stored: 'English translation · prepared in advance, not live AI', fixture: 'English translation · prepared in advance, not live AI', not_needed: 'Original is English', unavailable: 'No English translation', failed: 'Translation failed' }[t.status];
  return { btn, html: `<div class="trans"><div class="lab">${lab}</div>${t.text ? esc(t.text) : `<span class="small">${esc(t.note || '')}</span>`}<div class="small">${esc(t.source)}</div></div>` };
}

function policyHtml(v) {
  const p = v.policy;
  const uncited = p.applicable.filter((a) => !p.conditions.some((c) => c.policy === a.id));
  return `${p.applicable.length ? p.conditions.map((c) => `<div class="cond"><span class="tag dark" title="${esc(p.applicable.find((a) => a.id === c.policy)?.text || '')}">${c.policy}</span><span>${esc(c.condition)}</span><span class="tag">${esc(c.basis)} · ${esc(c.source)}</span></div>`).join('')
    + uncited.map((a) => `<div class="cond"><span class="tag dark" title="${esc(a.text)}">${a.id}</span><span>${esc(a.title)} — cited by the AI proposal; no supporting condition extracted from the evidence. Verify before relying on it.</span><span class="tag amber">AI citation</span></div>`).join('')
    : '<div class="tag amber">Not covered: no clause is supported by the available understanding</div>'}
    ${p.mandatory_human_checks.length ? `<div style="margin-top:10px"><b style="font-size:13px">Mandatory human checks</b><ul class="plain">${p.mandatory_human_checks.map((c) => `<li>${esc(c.policy)} — ${esc(c.check)}</li>`).join('')}</ul></div>` : ''}
    ${p.gap ? `<div style="margin-top:8px"><span class="tag amber">Policy gap</span> <span class="small">${esc(p.gap)}</span></div>` : ''}
    <div class="small" style="margin-top:8px">${esc(p.version)}</div>`;
}

function uncertaintyHtml(v) {
  const items = [...v.policy.conflicts.map((x) => ['Conflict', x]), ...v.policy.missing.map((x) => ['Missing', x]), ...(v.ai?.uncertainty || []).map((x) => ['AI uncertainty', x.replace(/_/g, ' ')])];
  return `<div class="statusbar" style="margin:0 0 10px"><div><span class="k">Confidence</span><b>${Math.round(v.confidence * 100)}%</b> <span class="tag">${v.confidence_band}</span> <span class="small">uncalibrated</span></div>
    <div><span class="k">Evidence</span><span class="tag ${v.evidence_completeness === 'complete' ? 'green' : 'red'}">${esc(v.evidence_completeness.replace(/_/g, ' '))}</span></div>
    <div><span class="k">Understanding</span><span class="tag ${v.understanding.supported ? 'green' : 'red'}">${v.understanding.supported ? 'language supported' : `“${esc(v.language)}” not understood`}</span></div></div>
    ${items.length ? `<ul class="plain">${items.map(([k, x]) => `<li><b>${k}:</b> ${esc(x)}</li>`).join('')}</ul>` : '<div class="small">No conflicts or gaps detected. Absence of a flag is not proof.</div>'}
    ${v.model_input?.injection_removed ? `<div style="margin-top:8px"><span class="tag red">Injection</span> <span class="small">${v.model_input.injection_removed} instruction(s) aimed at the triage system were removed from what any model sees. The rules still read the original text.</span></div>` : ''}
    ${v.severity.current === 'L1' && v.lane === 'agent' ? `<div style="margin-top:8px"><b style="font-size:13px">Automation eligibility</b> ${v.automation.live_eligibility.eligible ? `<span class="tag green">eligible${v.automation.state === 'shadow_eligible' ? ' · shadow mode' : ''}</span>` : v.automation.live_eligibility.reasons.map((r) => `<span class="tag ${r === 'text_only_needs_live_ai_confirmation' ? 'amber' : ''}">${esc(r === 'text_only_needs_live_ai_confirmation' ? 'second key: only the reporter’s words support SP-1, so a live model must agree (or you confirm)' : r.replace(/_/g, ' '))}</span>`).join(' ')}</div>` : ''}
    ${v.links.candidates.length ? `<div style="margin-top:8px"><b style="font-size:13px">Candidate links</b> ${v.links.candidates.map((l) => `<span class="tag blue">${l.case_id} · ${esc(l.basis)} · ${l.status}</span>`).join(' ')} <span class="small">Same IDs are a candidate link, not proof of a duplicate.</span></div>` : ''}`;
}

function execHtml(v) {
  if (!v.decisions.length && !v.executions.length && !v.reassessments.length) return '';
  return `<div class="exec">${v.reassessments.map((r) => `<div><span class="tag dark">Reassessment</span>${r.from} → ${r.to} · danger ${esc(r.danger_assessment.replace(/_/g, ' '))} · ${esc(r.policy_ref)} · ${esc(r.by_name)} · ${fmt(r.at)}<span class="small">“${esc(r.reason)}”</span></div>`).join('')}
    ${v.decisions.map((d) => `<div><span class="tag dark">Decision</span>${esc(d.decision.replace(/_/g, ' '))}${d.action ? ` · ${esc(v.meta_exec?.[d.action] || d.action.replace(/_/g, ' '))}` : ''} · ${esc(d.by_name)} · ${fmt(d.at)}${d.reason ? `<span class="small">“${esc(d.reason)}”</span>` : ''}</div>`).join('')}
    ${v.executions.map((x) => `<div><span class="tag ${x.status === 'completed' ? 'green' : x.status === 'failed' ? 'red' : 'amber'}">Execution · ${x.status}</span>${esc(x.label)} <span class="tag">→ ${esc(x.target)}</span>${x.receipt ? `<span class="small">${esc(x.receipt)}</span>` : ''}${x.error ? `<span class="small">${esc(x.error)}</span>` : ''}</div>`).join('')}
    ${v.resolution ? `<div><span class="tag green">Outcome</span>${esc(v.resolution.outcome.replace(/_/g, ' '))} · ${fmt(v.resolution.at)}</div>` : ''}</div>`;
}

function historyHtml(v) {
  return `<details class="src"><summary>History (${v.history.length} events, versioned)</summary><ul class="timeline">${v.history.slice().reverse().map((h) => `<li><span>${fmt(h.at)}</span><span><b>${esc(h.type)}</b> · ${esc(h.actor_name)}${h.summary ? ` — ${esc(h.summary)}` : ''}</span></li>`).join('')}</ul></details>`;
}

// Agent workspace: five questions, one primary action.
function drawAgentCase(v) {
  const tr = translationHtml(v);
  const owned = v.owner === S.user.id;
  const canAct = v.lane === 'agent' && v.workflow !== 'resolved' && S.user.role === 'agent';
  const lastExec = v.executions[v.executions.length - 1];
  let primary = '';
  if (canAct && !owned && !v.owner) primary = `<button class="btn primary" id="p-take">Take case${v.handoff.status === 'pending' ? ' (accept handoff)' : ''}</button>`;
  else if (canAct && owned && v.workflow !== 'awaiting_information' && (!v.decisions.length || lastExec?.status === 'failed')) primary = `<button class="btn primary" id="p-approve">${lastExec?.status === 'failed' ? 'Retry: ' : 'Approve: '}${esc(v.recommendation.exec_labels[0])}</button>`;
  else if (canAct && owned) primary = '<button class="btn primary" id="p-resolve">Resolve with reason</button>';
  const recBox = `<div class="rec"><div class="small" style="color:var(--g400)">Recommended next step · AI groundwork, you decide</div><div class="next">${esc(v.recommendation.next_step)}</div>
    <div class="meta2"><span class="tag">Actor: ${esc(v.recommendation.actor.replace('specialist:', 'specialist · ').replace(/_/g, ' '))}</span><span class="tag">Urgency: ${esc(v.recommendation.urgency)}</span><span class="tag">${v.recommendation.approval_required ? 'Needs your approval' : 'No extra approval'}</span><span class="tag">Brief action: ${esc(v.recommendation.proposed_action)}</span></div>
    ${primary || `<div class="small" style="color:var(--g300)">${v.workflow === 'resolved' ? 'Resolved.' : v.owner && !owned ? `Owned by ${esc(v.owner_name)}.` : v.lane !== 'agent' ? 'Not in an agent lane.' : 'Waiting on the reporter. The first-response clock keeps running.'}</div>`}
    ${canAct ? `<details class="more"><summary>Other actions</summary><div class="acts">
      <button class="btn btn-sm" data-a="info">Request more information</button><button class="btn btn-sm" data-a="alt">Choose a different action</button>
      <button class="btn btn-sm" data-a="spec">Escalate to specialist</button><button class="btn btn-sm" data-a="urgent">Raise urgent concern to duty manager</button>
      ${v.links.candidates.some((l) => l.status === 'candidate') ? '<button class="btn btn-sm" data-a="link">Decide candidate link</button>' : ''}${v.decisions.length ? '<button class="btn btn-sm" data-a="resolve">Resolve</button>' : ''}</div></details>` : ''}</div>${execHtml(v)}`;
  $('#detail').innerHTML = `<div class="detail-inner">${header(v)}
    ${v.flags.includes('automation_exception') ? '<div class="q"><div class="b"><span class="tag red">Automation exception</span> Upstream automation failed for this case; it was sent to human review. Nothing was resolved.</div></div>' : ''}
    ${v.handoff.status === 'pending' ? `<div class="q"><div class="b"><span class="tag blue">Handoff pending</span> From ${esc(v.handoff.from_name || 'system')}: “${esc(v.handoff.reason || '')}”. Taking the case accepts the handoff.</div></div>` : ''}
    <section class="q"><header><span class="n">1</span><h2>What happened?</h2><div class="r">${tr.btn}</div></header><div class="b">
      <div class="summary">${esc(v.ai.summary)}</div><div class="small" style="margin:4px 0 10px">AI interpretation (${esc(v.ai.mode)}). Not established fact.</div>
      <div class="stmt"><span class="k">Reported allegation<br><span class="small">${esc(v.language)} · ${esc(v.channel)}</span></span><div><div class="report">${textHtml(v)}</div>${tr.html}</div></div>
      <div class="stmt"><span class="k">AI rationale</span><span>${esc(v.ai.rationale)}</span></div></div></section>
    <section class="q"><header><span class="n">2</span><h2>What evidence is available?</h2></header><div class="b">${sourcesHtml(v)}</div></section>
    <section class="q"><header><span class="n">3</span><h2>What does policy imply?</h2></header><div class="b">${policyHtml(v)}</div></section>
    <section class="q"><header><span class="n">4</span><h2>What is uncertain or missing?</h2></header><div class="b">${uncertaintyHtml(v)}</div></section>
    <section class="q"><header><span class="n">5</span><h2>What should I do next?</h2></header><div class="b">${recBox}</div></section>
    <section class="q"><div class="b">${historyHtml(v)}</div></section></div>`;
  bindCommon(v);
  $('#p-take') && ($('#p-take').onclick = () => cmd('take'));
  $('#p-approve') && ($('#p-approve').onclick = () => cmd('approve'));
  $('#p-resolve') && ($('#p-resolve').onclick = () => resolveDialog(false));
  $('#detail').querySelectorAll('[data-a]').forEach((b) => b.onclick = () => agentAction(b.dataset.a, v));
}

function agentAction(a, v) {
  const reason = '<label>Reason<textarea class="input" name="reason" required></textarea></label>';
  if (a === 'info') return dialog('Request more information', `<p class="small">Sends a (simulated) message to the reporter. The first-response clock is not paused while you wait.</p>${reason}`, (fd) => cmd('request_info', { reason: fd.get('reason') }), 'Send request');
  if (a === 'alt') return dialog('Choose a different action', `<label>Action<select class="select" name="action">${Object.entries(S.meta.exec_actions).filter(([k]) => !['restrict_rematch', 'suspend_reported_party'].includes(k)).map(([k, x]) => `<option value="${k}">${esc(x.label)}</option>`).join('')}</select></label>${reason}`, (fd) => cmd('choose_action', { action: fd.get('action'), reason: fd.get('reason') }), 'Approve action');
  if (a === 'spec') return dialog('Escalate to specialist review', `<p class="small">Routes to the L3 queue with the matching capability. You keep a status view of the handoff.</p>${reason}`, (fd) => cmd('escalate', { to: 'specialist', reason: fd.get('reason') }), 'Escalate');
  if (a === 'urgent') return dialog('Raise an urgent concern to the duty manager', `<p class="small">Creates an alert and moves the case to the duty-manager lane immediately.</p>${reason}`, (fd) => cmd('escalate', { to: 'manager', reason: fd.get('reason') }), 'Raise alert');
  if (a === 'link') { const l = v.links.candidates.find((x) => x.status === 'candidate'); return dialog(`Candidate link to ${l.case_id}`, `<p class="small">Basis: ${esc(l.basis)}. Confirming links the records; it does not merge evidence or close either case.</p><label>Decision<select class="select" name="status"><option value="confirmed">Same incident — confirm link</option><option value="rejected">Different incident — reject</option></select></label>`, (fd) => cmd('link', { case_id: l.case_id, status: fd.get('status') }), 'Save'); }
  if (a === 'resolve') return resolveDialog(false);
}

function resolveDialog(manager) {
  dialog(manager ? 'Close the case' : 'Resolve case', `${manager ? `<label>Danger now<select class="select" name="danger"><option value="no_longer_present">No longer present</option><option value="incorrectly_detected">Incorrectly detected</option><option value="handed_to_authorities">Handed to authorities</option></select></label>` : ''}
    ${manager ? `<label>Outcome<select class="select" name="outcome"><option value="reporter_safe">Reporter confirmed safe</option><option value="handed_to_authorities">Handed to authorities</option><option value="action_taken_against_party">Action taken against reported party</option><option value="no_safety_issue_found">No safety issue found</option></select></label>` : '<label>Outcome<input class="input" name="outcome" value="resolved"></label>'}<label>Reason (what happened and what was done)<textarea class="input" name="reason"></textarea></label>`,
    (fd) => cmd('resolve', { outcome: fd.get('outcome'), reason: fd.get('reason'), danger_status: fd.get('danger') || undefined }), manager ? 'Close the case' : 'Resolve');
}

// Duty-manager workspace: danger first, timing, ownership, next steps, controlled reassessment.
function drawManagerCase(v) {
  const open = v.danger.alerts.filter((a) => !a.acknowledged_at);
  const owned = v.owner === S.user.id;
  const step = (k) => [...v.steps].reverse().find((x) => x.step === k);
  const clock = (k, val, bad) => `<div class="clock ${bad ? 'bad' : ''}"><div class="k">${k}</div><div class="v">${val}</div></div>`;
  const stepRow = (n, key, title, opts, note) => { const s = step(key); return `<div class="step ${s ? 'done' : ''}"><span class="sn">${s ? '✓' : n}</span><div><b>${title}</b>${s ? `<div class="small">${esc(s.value.replace(/_/g, ' '))} · ${esc(s.by_name)} · ${fmt(s.at)}</div>` : ''}
    ${owned && v.workflow !== 'resolved' ? `<div class="opts">${opts.map(([val, l]) => `<button class="btn btn-sm ${s?.value === val ? 'btn-black' : 'btn-gray'}" data-step="${key}" data-v="${val}">${l}</button>`).join('')}</div>` : ''}${note ? `<div class="small">${note}</div>` : ''}</div></div>`; };
  const tr = translationHtml(v);
  $('#detail').innerHTML = `<div class="detail-inner">${header(v)}
    <div class="danger"><h2>${open.length ? 'Unacknowledged danger alert' : 'Danger case'} — why this is here</h2><ul>${v.danger.signals.map((s) => `<li>${esc(s.label)} <span style="opacity:.8">(${esc(s.kind)} · ${esc(s.source)} · ${fmt(s.detected_at)})</span></li>`).join('') || `<li>${esc(v.escalation_reason || 'L4')}</li>`}</ul>
      <div style="margin-top:8px;font-size:13px;opacity:.9">Danger status: <b>${esc(v.danger.status.replace(/_/g, ' '))}</b>. Automation cannot close, downgrade or resolve this case.</div>
      ${v.integrations.pages.map((pg) => `<div class="page-rec">${esc(pg.system)} · ${esc(pg.ref)} → ${esc(pg.rotation)} · <b>${pg.status}</b>${pg.acknowledged_at ? ` ${fmt(pg.acknowledged_at)}` : ''}</div>`).join('')}</div>
    <div class="clocks">${clock('Received', fmt(v.clocks.received_at))}${clock('Alert created', fmt(v.clocks.alert_created_at))}${clock('Acknowledged', v.clocks.alert_acknowledged_at ? fmt(v.clocks.alert_acknowledged_at) : 'Not yet', !v.clocks.alert_acknowledged_at)}
      ${clock('First response', v.clocks.first_response_at ? fmt(v.clocks.first_response_at) : 'None yet', !v.clocks.first_response_at && v.sla.status === 'breached')}${clock('Response due', `${fmt(v.sla.due_at)}${v.sla.status === 'breached' || v.sla.status === 'missed' ? ' · past due on the replay clock' : ''}`, v.sla.status === 'breached' || v.sla.status === 'missed')}</div>
    <section class="q"><header><h2>${open.length ? 'Take ownership' : `Accountable owner: ${esc(v.owner_name || 'none')}`}</h2></header><div class="b">
      ${open.length ? `<p style="font-size:14px;margin-bottom:10px">Acknowledging makes you the accountable owner. It is <b>not</b> a response to the reporter and does not stop the clock.</p><button class="btn btn-red" id="ack">Acknowledge and own</button>`
        : owned ? `<div class="small">Next steps from policy (SP-7). Emergency services are recorded by you; this system notifies no one.</div>
          <div class="steps">${stepRow(1, 'contact_reporter', 'Contact the reporter', [['reached', 'Reached'], ['no_answer', 'No answer'], ['no_channel', 'No contact channel']])}
          ${stepRow(2, 'emergency_services', 'Emergency services', [['contacted', 'Contacted (by me)'], ['not_needed', 'Not needed'], ['declined_by_reporter', 'Declined by reporter']])}
          ${stepRow(3, 'protect', 'Protect the reporter', [['restrict_rematch', 'Block re-matching'], ['suspend_reported_party', 'Suspend reported party'], ['none_needed', 'None needed']], 'Blocking and suspension go to Account enforcement (mock).')}
          ${(() => { const done = ['contact_reporter', 'emergency_services', 'protect'].filter((k) => step(k)).length; const contact = step('contact_reporter');
            const blocker = !contact ? 'Contact the reporter (step 1) before closing.' : contact.value === 'no_answer' ? 'Reporter not reached yet. Keep trying before closing.' : v.executions.some((x) => ['queued', 'running'].includes(x.status)) ? 'An action is still executing.' : '';
            return v.workflow === 'resolved' ? `<div class="step done"><span class="sn">✓</span><div><b>Case closed</b><div class="small">${esc((v.resolution?.outcome || '').replace(/_/g, ' '))} · ${fmt(v.resolution?.at)}</div></div></div>`
            : `<div class="step"><span class="sn">4</span><div><b>Close the case</b><div class="small">${blocker || (done < 3 ? `${done} of 3 steps recorded. You can close without the others if they do not apply; say why in the reason.` : 'All steps recorded. Confirm the danger status and the outcome. The ticket is marked solved and the protections stay in place.')}</div>
              <div class="opts"><button class="btn btn-sm ${done === 3 && !blocker ? 'btn-black' : 'btn-gray'}" id="resolve" ${blocker ? 'disabled' : ''}>Close the case…</button></div></div></div>`; })()}</div>
          <details class="more" style="margin-top:12px"><summary style="color:var(--g600)">Not a danger case after all? Reassess or hand off</summary><div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
            <button class="btn btn-gray btn-sm" id="reassess">Reassess severity (downgrade to a queue)</button><button class="btn btn-gray btn-sm" id="reassign">Reassign to another duty manager</button>
            <button class="btn btn-gray btn-sm" id="demosig" title="Demo control">Demo: inject a new SOS signal</button></div></details>`
        : `<div class="small">Owned by ${esc(v.owner_name || 'nobody')}. Only the owner acts; reassignment is recorded.</div>`}
      ${execHtml(v)}</div></section>
    <section class="q"><header><h2>Recommended next step</h2></header><div class="b"><div class="summary" style="font-size:15px">${esc(v.recommendation.next_step)}</div>
      ${v.policy.missing.length || v.policy.conflicts.length ? `<div style="margin-top:8px"><b style="font-size:13px">Critical evidence gaps</b><ul class="plain">${[...v.policy.missing, ...v.policy.conflicts].map((x) => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}</div></section>
    <section class="q"><header><h2>What happened</h2><div class="r">${tr.btn}</div></header><div class="b"><div class="summary" style="font-size:15px">${esc(v.ai.summary)}</div><div class="small">AI interpretation (${esc(v.ai.mode)}); AI proposed ${esc(v.severity.proposed)}.</div>
      <div class="stmt"><span class="k">Reported allegation</span><div><div class="report">${textHtml(v)}</div>${tr.html}</div></div>
      <details class="src"><summary>Evidence sources</summary>${sourcesHtml(v)}</details><details class="src"><summary>Policy assessment</summary>${policyHtml(v)}</details></div></section>
    <section class="q"><div class="b">${historyHtml(v)}</div></section></div>`;
  bindCommon(v);
  $('#ack') && ($('#ack').onclick = () => cmd('acknowledge'));
  $('#detail').querySelectorAll('[data-step]').forEach((b) => b.onclick = () => cmd('step', { step: b.dataset.step, value: b.dataset.v }));
  $('#resolve') && ($('#resolve').onclick = () => resolveDialog(true));
  $('#reassign') && ($('#reassign').onclick = () => dialog('Reassign to another duty manager', `<label>To<select class="select" name="to">${S.meta.users.filter((u) => u.role === 'duty_manager' && u.id !== S.user.id).map((u) => `<option value="${u.id}">${esc(u.name)}</option>`).join('')}</select></label><label>Reason<textarea class="input" name="reason"></textarea></label>`,
    (fd) => cmd('escalate', { to_user: fd.get('to'), reason: fd.get('reason') }), 'Reassign'));
  $('#demosig') && ($('#demosig').onclick = async () => { const r = await api('api/demo/signal', { method: 'POST', body: JSON.stringify({ case_id: v.case_id }) }); toast(r.ok ? 'Demo: new SOS ingested' : r.body.error); loadCase(v.case_id); });
  $('#reassess') && ($('#reassess').onclick = () => reassessDialog(v));
}

function reassessDialog(v) {
  const queues = Object.entries(S.meta.queues).filter(([k]) => k !== 'automation' && k !== 'duty-managers');
  dialog(`Reassess ${v.case_id}`, `<p class="small">Original AI proposal (${v.severity.proposed}), danger signals, alerts, acknowledgements and clocks are preserved. A downgrade hands the case to a human queue; it never closes it or releases it to automation.</p>
    <label>Current severity<input class="input" value="${v.severity.current}" disabled></label>
    <label>New severity<select class="select" name="to">${['L4', 'L3', 'L2', 'L1'].filter((t) => t !== v.severity.current).map((t) => `<option>${t}</option>`).join('')}</select></label>
    <label>Is danger…<select class="select" name="danger"><option value="no_longer_present">No longer present</option><option value="incorrectly_detected">Incorrectly detected</option><option value="ongoing">Ongoing (stays L4)</option></select></label>
    <label>Supporting evidence<div class="checks">${v.sources.map((s) => `<label><input type="checkbox" name="ev" value="${s.id}"> ${esc(s.name)}</label>`).join('')}</div></label>
    <label>Applicable policy<select class="select" name="policy">${S.meta.policy.map((p) => `<option value="${p.id}">${p.id} — ${esc(p.title)}</option>`).join('')}</select></label>
    <label>Destination queue (L1/L2 → general review; L3 → specialist)<select class="select" name="dest">${queues.map(([k, q]) => `<option value="${k}">${esc(q.label)}</option>`).join('')}</select></label>
    <label>Reason (what changed and how you know)<textarea class="input" name="reason"></textarea></label>`,
    (fd) => cmd('reassess', { to: fd.get('to'), danger_assessment: fd.get('danger'), evidence_refs: fd.getAll('ev'), policy_ref: fd.get('policy'), destination_queue: fd.get('dest'), reason: fd.get('reason') }), 'Record reassessment');
}

function bindCommon(v) {
  $('#tr') && ($('#tr').onclick = async () => { const r = await api(`api/cases/${v.case_id}/ai/translate`, { method: 'POST' }); S.translation[v.case_id] = r.body; drawCase(); });
  $('#detail').querySelectorAll('[data-reveal]').forEach((b) => b.onclick = (e) => { e.preventDefault(); dialog('View personal data', `<p class="small">Your reason is written to the access log.</p><label>Reason<textarea class="input" name="reason"></textarea></label>`, async (fd) => {
    const r = await api(`api/cases/${v.case_id}/reveal`, { method: 'POST', body: JSON.stringify({ field: b.dataset.reveal, reason: fd.get('reason') }) });
    if (!r.ok) return r.body.error; S.view = r.body; drawCase(); return null; }, 'Reveal and log'); });
}

boot();
