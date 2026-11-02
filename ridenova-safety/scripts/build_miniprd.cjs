// Builds docs/RideNova_Workbench_MiniPRD.pptx (10 slides, editable).
//   NODE_PATH=<dir with pptxgenjs> node scripts/build_miniprd.cjs [applyThemePath]
// Every number on these slides comes from `npm run evaluate`, `npm test` or the brief.
const pptxgen = require('pptxgenjs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'docs', 'RideNova_Workbench_MiniPRD.pptx');
const THEME = {
  name: 'RideNova Workbench', headFontFace: 'Arial', bodyFontFace: 'Arial',
  colors: { dk1: '000000', lt1: 'FFFFFF', dk2: '333333', lt2: 'F3F3F3', accent1: 'E11900', accent2: 'FF6937', accent3: 'FFC043', accent4: '05944F', accent5: '276EF1', accent6: '7356BF', hlink: '276EF1', folHlink: '7356BF' },
};
const HEX = { black: '000000', white: 'FFFFFF', g50: 'F6F6F6', g100: 'EEEEEE', g300: 'CBCBCB', g500: '757575', g600: '545454', red: 'E11900', orange: 'FF6937', amber: 'FFC043', green: '05944F', blue: '276EF1' };
const TAG = {
  Implemented: ['E6F2EC', '03703C'], Simulated: ['FFF3D6', '8A5A00'], Measured: ['E8EEFC', '1E54B7'], Estimate: ['FDEBD9', '9A4A00'], Target: ['EFE9FB', '5A3FA6'], Open: ['FDE7E3', 'A3130A'], Brief: ['EEEEEE', '333333'],
};

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5
pres.title = 'RideNova Safety Workbench — mini-PRD';
pres.author = 'Otman Kettani';
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

function layout(name, dark) {
  pres.defineSlideMaster({
    title: name,
    background: { color: dark ? C.text1 : C.background1 },
    objects: [
      { placeholder: { options: { name: 'kicker', type: 'body', x: 0.5, y: 0.3, w: 12.3, h: 0.35, fontSize: 11, bold: true, color: dark ? C.background2 : C.text2, charSpacing: 2, margin: 0 }, text: '' } },
      { placeholder: { options: { name: 'title', type: 'title', x: 0.5, y: 0.65, w: 12.3, h: 1.0, fontSize: 28, bold: true, color: dark ? C.background1 : C.text1, valign: 'top', align: 'left', margin: 0 }, text: '' } },
      { text: { text: 'RideNova Safety Workbench · mini-PRD · fictional case study (synthetic data, fictional SP-1..SP-9)', options: { x: 0.5, y: 7.08, w: 10, h: 0.25, fontSize: 9, color: dark ? C.background2 : '757575', margin: 0, isTextBox: true } } },
    ],
    slideNumber: { x: 12.4, y: 7.05, w: 0.45, h: 0.3, fontSize: 9, color: dark ? 'CBCBCB' : '757575', align: 'right' },
  });
}
layout('CONTENT', false);
layout('DARK', true);

let n = 0;
function slide(master, section, kicker, title, notes) {
  if (section) pres.addSection({ title: section });
  const s = pres.addSlide({ masterName: master, sectionTitle: section || slide.lastSection });
  if (section) slide.lastSection = section;
  s.addText(kicker.toUpperCase(), { placeholder: 'kicker' });
  s.addText(title, { placeholder: 'title' });
  if (notes) s.addNotes(notes);
  n++;
  return s;
}
const box = (s, x, y, w, h, fill, opts = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: opts.line || fill, width: opts.lineW || 0.75 }, rectRadius: 0.08, objectName: opts.name });
const text = (s, t, x, y, w, h, o = {}) => s.addText(t, { x, y, w, h, fontSize: 14, color: C.text1, margin: 0, valign: 'top', isTextBox: true, ...o });
function tag(s, label, x, y, kind = label) {
  const [bg, fg] = TAG[kind];
  const w = 0.12 + label.length * 0.075;
  box(s, x, y, w, 0.26, bg);
  text(s, label, x, y, w, 0.26, { fontSize: 10, bold: true, color: fg, align: 'center', valign: 'middle' });
  return w;
}
function card(s, x, y, w, h, title, lines, o = {}) {
  box(s, x, y, w, h, o.fill || HEX.g50, { name: o.name });
  text(s, title, x + 0.18, y + 0.14, w - 0.36, 0.35, { fontSize: 15, bold: true, color: o.fg || C.text1 });
  if (lines?.length) text(s, lines.map((l, i) => ({ text: l, options: { bullet: o.plain ? false : { indent: 12 }, breakLine: i < lines.length - 1, paraSpaceAfter: 4 } })), x + 0.18, y + 0.52, w - 0.36, h - 0.62, { fontSize: o.size || 13, color: o.fg || C.text2 });
}
function legend(s, kinds, y = 6.72) { let x = 12.83; for (const k of [...kinds].reverse()) { const w = 0.12 + k.length * 0.075; x -= w; tag(s, k, x, y); x -= 0.1; } }
function circleNum(s, num, x, y, fill = HEX.black, fg = HEX.white) { s.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: fill }, line: { color: fill } }); text(s, String(num), x, y, 0.42, 0.42, { fontSize: 13, bold: true, color: fg, align: 'center', valign: 'middle' }); }
function arrow(s, x1, y1, x2, y2, color = HEX.g500) { s.addShape(pres.shapes.LINE, { x: x1, y: y1, w: x2 - x1, h: y2 - y1, line: { color, width: 1.5, endArrowType: 'triangle' } }); }

// 1 ─────────────────────────────────────────────────────────────
{
  const s = slide('DARK', 'Why', '1 · Problem, thesis and outcomes', 'Automate the groundwork, not the accountability',
    'Problem from the brief: 55% of handling time is spent finding information across fragmented tools, 35 languages, and mixed-severity queues. Thesis: a role-based console that structures evidence, proposes and routes, and records what humans decided and what actually executed. Outcomes on the right are proposed targets, not results.');
  const stats = [['55%', 'of handling time spent finding information'], ['74 · 35', 'countries · languages, incl. mixed-language'], ['2%', 'critical (L4) cases in the same queues as AC complaints']];
  stats.forEach(([v, l], i) => { text(s, v, 0.5, 1.95 + i * 1.45, 3.4, 0.7, { fontSize: 40, bold: true, color: C.background1 }); text(s, l, 0.5, 2.62 + i * 1.45, 3.4, 0.5, { fontSize: 13, color: 'CBCBCB' }); });
  tag(s, 'Brief', 0.5, 6.25);
  const steps = ['Ingest & structure evidence', 'Propose severity & assess policy', 'Route: automation or the right human', 'Smart summary + concrete next step', 'Record decision, execution, outcome', 'Operational overview'];
  text(s, 'Product thesis', 4.3, 1.85, 4.4, 0.35, { fontSize: 15, bold: true, color: C.background1 });
  steps.forEach((t, i) => { circleNum(s, i + 1, 4.3, 2.3 + i * 0.66, HEX.white, HEX.black); text(s, t, 4.85, 2.33 + i * 0.66, 3.9, 0.4, { fontSize: 14, color: C.background1, valign: 'middle' }); });
  text(s, 'Intended outcomes', 9.1, 1.85, 3.8, 0.35, { fontSize: 15, bold: true, color: C.background1 });
  const outs = [['< 5 min', 'L4 time to acknowledgement (p95)', 'Target'], ['0', 'L3+ cases found in the automation lane by QA', 'Target'], ['≈ −42%', 'reviewer hours per 1,000 cases', 'Estimate'], ['100%', 'active cases with an accountable queue or owner', 'Implemented']];
  outs.forEach(([v, l, k], i) => { box(s, 9.1, 2.3 + i * 1.08, 3.75, 0.95, HEX.g800 || '1F1F1F'); text(s, v, 9.28, 2.38 + i * 1.08, 1.6, 0.5, { fontSize: 22, bold: true, color: C.background1 }); text(s, l, 9.28, 2.82 + i * 1.08, 3.4, 0.35, { fontSize: 12, color: 'CBCBCB' }); tag(s, k, 11.6, 2.43 + i * 1.08); });
}

// 2 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', 'Design', '2 · Users, access profiles and decision rights', 'Two profiles with different decision rights; automation is a lane, not a user',
    'Agents work assigned or permitted queues in their markets; L3 needs a specialist capability. Duty managers own danger cases, acknowledge, reassess and resolve. Sign-in is simulated, but the server enforces every scope; the browser never receives data a profile may not see.');
  const H = ['Decision right', 'Agent (general)', 'Agent (specialist)', 'Duty manager'];
  const rows = [
    ['See cases', 'Own markets, L1/L2 agent lane', '+ L3 queues for held capability', 'All markets; danger and L4'],
    ['Approve action / request info', '✓ (agent lane)', '✓ (incl. L3)', '— (uses manager steps)'],
    ['Escalate', 'To specialist or duty manager', 'To duty manager', 'Reassign to another manager'],
    ['Acknowledge alert & own', '—', '—', '✓'],
    ['Reassess / downgrade danger case', '—', '—', '✓ controlled workflow'],
    ['View personal data', 'Owned cases, reason logged', 'Owned cases, reason logged', 'Reason logged'],
    ['Export · automation mode', '—', '—', '✓ (logged)'],
  ];
  const opt = (b, fill) => ({ fontSize: 12, bold: b, color: b ? 'FFFFFF' : '000000', fill: { color: fill }, margin: [4, 6, 4, 6], valign: 'middle' });
  s.addTable([H.map((h) => ({ text: h, options: opt(true, '000000') })), ...rows.map((r, i) => r.map((c, j) => ({ text: c, options: { ...opt(false, i % 2 ? 'FFFFFF' : 'F6F6F6'), bold: j === 0 } })))], { x: 0.5, y: 1.85, w: 8.6, colW: [2.5, 2.0, 2.0, 2.1], border: { type: 'solid', color: 'EEEEEE', pt: 0.75 }, rowH: 0.52 });
  card(s, 9.45, 1.85, 3.4, 2.15, 'Automation lane', ['Upstream service, never a work queue', 'Cannot touch danger, protected or uncertain cases', 'Every attempt, failure and exception recorded'], { size: 12 });
  card(s, 9.45, 4.15, 3.4, 2.35, 'Enforcement', ['Permissions checked on the server for every read and command', 'Role selector is a labelled simulation, not proof of RBAC', 'Agents see status-only for cases they handed off'], { size: 12 });
  legend(s, ['Implemented', 'Simulated']);
}

// 3 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', null, '3 · Three processing lanes and routing precedence', 'Danger always wins, automation must earn eligibility, and everything else goes to a qualified human',
    'Routing is evaluated in order. Structured danger checks run at receipt, before AI. L1 alone never makes a case eligible. Counts are measured on the 5,000 cases in shadow mode.');
  box(s, 0.5, 2.0, 2.2, 1.1, HEX.black); text(s, 'Intake\n(ticket created)', 0.5, 2.0, 2.2, 1.1, { color: C.background1, bold: true, align: 'center', valign: 'middle', fontSize: 14 });
  text(s, 'Structured danger checks run immediately: SOS, GPS at home, live stop', 0.5, 3.25, 2.2, 1.0, { fontSize: 11, color: '545454' });
  const lanes = [
    ['A', 'Duty manager', 'L4 OR any danger signal, whatever the AI proposed', 'Alert + explicit ownership; no auto close / downgrade', '138', 'FDE7E3', 'A3130A'],
    ['B', 'Eligible automation', 'Explicit SP-1 + complete evidence + supported language + no exclusion', 'Upstream; states eligible → completed / failed → review', '0 now · 2,456 shadow-eligible', 'E6F2EC', '03703C'],
    ['C', 'Agent review', 'Everything else; L3 → specialist capability queue', 'Smart summary, next step, one primary action', '4,862', 'EEEEEE', '000000'],
  ];
  lanes.forEach(([k, name, entry, beh, count, bg, fg], i) => {
    const y = 1.85 + i * 1.6;
    arrow(s, 2.75, 2.55, 3.3, y + 0.65);
    box(s, 3.3, y, 9.55, 1.4, bg);
    circleNum(s, k, 3.48, y + 0.2, fg, 'FFFFFF');
    text(s, name, 4.05, y + 0.18, 3.0, 0.4, { fontSize: 16, bold: true, color: fg });
    text(s, `Entry: ${entry}`, 4.05, y + 0.6, 4.6, 0.75, { fontSize: 12, color: '333333' });
    text(s, beh, 8.75, y + 0.18, 2.4, 1.1, { fontSize: 12, color: '333333' });
    text(s, count, 11.2, y + 0.18, 1.5, 0.9, { fontSize: count.length > 6 ? 13 : 24, bold: true, color: fg, align: 'right' });
  });
  text(s, 'Exclusions from B: protected allegation · danger (now or past) · repeat-conduct history · policy gap · injection · conflict · candidate link · safety-feature use · confidence < 0.75 · human reassessment · text-only SP-1 without live-AI agreement (second key)', 0.5, 6.55, 10.6, 0.45, { fontSize: 11, color: '545454' });
  legend(s, ['Measured'], 6.72);
}

// 4 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', null, '4 · Overview: filters, distributions, operational controls', 'One overview answers “where is attention needed?”, and every number reconciles to its filtered population',
    'Severity is always labelled by basis: AI-proposed, current operational, or human-reviewed. New tickets and open backlog use different denominators. Replay clock: the data has no real responses, so SLA counts are not historical performance.');
  const kpis = [['5,000', 'Filtered population'], ['610', 'New tickets (last 24h, replay)'], ['5,000', 'Open backlog'], ['138', 'Unacknowledged critical alerts'], ['432', 'Provisional / not understood']];
  kpis.forEach(([v, l], i) => { box(s, 0.5 + i * 2.5, 1.85, 2.35, 1.0, HEX.g50); text(s, v, 0.68 + i * 2.5, 1.93, 2.0, 0.5, { fontSize: 24, bold: true }); text(s, l, 0.68 + i * 2.5, 2.42, 2.1, 0.4, { fontSize: 11, color: '545454' }); });
  s.addChart(pres.charts.BAR, [{ name: 'AI-proposed', labels: ['L4', 'L3', 'L2', 'L1'], values: [138, 355, 961, 3546] }, { name: 'Current operational', labels: ['L4', 'L3', 'L2', 'L1'], values: [138, 387, 1248, 3227] }], {
    x: 0.5, y: 3.05, w: 6.2, h: 3.5, barDir: 'col', barGrouping: 'clustered', chartColors: ['CBCBCB', '000000'], showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 10, dataLabelColor: '333333',
    showLegend: true, legendPos: 'b', legendFontSize: 11, legendFontFace: '+mn-lt', showTitle: true, title: 'Severity by basis (n = 5,000, shadow mode)', titleFontSize: 13, titleFontFace: '+mn-lt', titleColor: '000000',
    catAxisLabelColor: '545454', valAxisLabelColor: '757575', catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, catAxisLabelFontFace: '+mn-lt', valAxisLabelFontFace: '+mn-lt', dataLabelFontFace: '+mn-lt', valGridLine: { color: 'EEEEEE', size: 0.5 }, catGridLine: { style: 'none' },
  });
  card(s, 7.0, 3.05, 2.85, 3.5, 'Default filters', ['Date range: received or decision', 'Region / country', 'Product', 'Language', 'Reporter persona', 'Severity + basis', 'Workflow status'], { size: 12 });
  card(s, 10.0, 3.05, 2.85, 3.5, 'Advanced (on demand)', ['Owner · queue', 'Escalation reason', 'Evidence gaps', 'Repeat-conduct flag', 'Confidence band', 'Automation outcome', 'Policy version'], { size: 12 });
  legend(s, ['Implemented', 'Measured']);
}

// 5 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', null, '5 · Agent workspace and investigation journey', 'The agent screen answers five questions, then offers one primary action',
    'Each section is source-linked: allegation, system observation, history, AI interpretation. The primary action changes with state: take the case, approve the recommended action, retry after a failed execution, or resolve. Other actions sit behind progressive disclosure.');
  const qs = [['What happened?', 'AI summary labelled as interpretation; original report (redacted) + labelled translation'], ['What evidence is available?', '7 sources with status, version, retrieval time and gaps'], ['What does policy imply?', 'Clause → condition → source; mandatory human checks; gaps'], ['What is uncertain or missing?', 'Confidence (uncalibrated) apart from evidence completeness and understanding'], ['What should I do next?', 'Concrete step, actor, urgency, approval, destination']];
  qs.forEach(([q, d], i) => { const y = 1.9 + i * 0.93; circleNum(s, i + 1, 0.5, y + 0.12); text(s, q, 1.1, y, 3.6, 0.4, { fontSize: 15, bold: true }); text(s, d, 1.1, y + 0.38, 6.4, 0.45, { fontSize: 12, color: '545454' }); });
  box(s, 8.0, 1.9, 4.85, 2.55, HEX.black);
  text(s, 'Recommended next step', 8.2, 2.05, 4.4, 0.3, { fontSize: 11, color: 'CBCBCB' });
  text(s, 'Verify the cleaning quote and charge the cleaning fee to the rider (SP-2).', 8.2, 2.35, 4.45, 0.8, { fontSize: 15, bold: true, color: C.background1 });
  box(s, 8.2, 3.3, 3.6, 0.5, HEX.white); text(s, 'Approve: charge cleaning fee', 8.2, 3.3, 3.6, 0.5, { fontSize: 13, bold: true, align: 'center', valign: 'middle' });
  text(s, '▸ Other actions: request info · different action · escalate · urgent concern · link · resolve', 8.2, 3.9, 4.5, 0.45, { fontSize: 11, color: 'CBCBCB' });
  card(s, 8.0, 4.6, 4.85, 1.9, 'After the click, three separate records', ['Decision: approve recommendation · who · when', 'Execution: queued → running → completed / failed (simulated)', 'Outcome: resolved only after confirmed execution'], { size: 12 });
  legend(s, ['Implemented', 'Simulated']);
}

// 6 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', null, '6 · Duty-manager workspace and controlled reassessment', 'Managers see why it is dangerous, who owns it and what to do now, and can correct a false alarm without erasing it',
    'Acknowledgement is ownership, not a response. Emergency services are recorded by the manager; the system notifies no one. A downgrade requires evidence, policy and reason, keeps every alert and the original deadline, and hands off to a human queue. New danger after a downgrade creates a fresh alert.');
  const clocks = ['Received', 'Alert created', 'Acknowledged', 'First response', 'Response due'];
  clocks.forEach((c, i) => { box(s, 0.5 + i * 1.6, 1.9, 1.48, 0.75, i === 4 ? 'FDE7E3' : HEX.g50); text(s, c, 0.6 + i * 1.6, 2.0, 1.3, 0.55, { fontSize: 12, bold: true, align: 'center', valign: 'middle', color: i === 4 ? 'A3130A' : '000000' }); });
  text(s, 'Five separate timestamps; acknowledging does not stop the 15-minute clock', 0.5, 2.75, 7.9, 0.35, { fontSize: 11, color: '545454' });
  const steps = ['Acknowledge & own', 'Contact reporter: reached / no answer / no channel', 'Emergency services: contacted (by manager) / not needed / declined', 'Protect: block re-matching / suspend (simulated) / none', 'Resolve: danger status + reason, or reassess'];
  steps.forEach((t, i) => { circleNum(s, i + 1, 0.5, 3.25 + i * 0.66, i === 0 ? HEX.red : HEX.black); text(s, t, 1.1, 3.27 + i * 0.66, 6.9, 0.4, { fontSize: 13, valign: 'middle' }); });
  card(s, 8.6, 1.9, 4.25, 2.45, 'Reassessment requires', ['Owner + acknowledged alert', 'Proposed severity + danger: ongoing / no longer present / incorrectly detected', 'Cited evidence source(s) + policy clause', 'Reason (20+ chars) + human destination queue'], { size: 12 });
  card(s, 8.6, 4.5, 4.25, 2.0, 'And always preserves', ['AI proposal, danger signals, alerts, acks', 'Receipt time and deadline (max tier held)', 'Never closes; never releases to automation', 'New danger → fresh escalation'], { size: 12, fill: 'E6F2EC' });
  legend(s, ['Implemented', 'Simulated']);
}

// 7 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', 'Build', '7 · Ingestion, structured evidence and AI capabilities', 'Danger checks never wait for AI; AI output is validated before anyone sees it',
    'Seven mocked source systems are normalised with provenance. Structured danger checks run at receipt in parallel with AI preparation. The provider interface has three implementations: simulated (demo), Anthropic (live, not run in this environment), and a failing provider used in tests.');
  const src = ['Ticketing (allegation)', 'Trip system', 'Case history', 'Safety toolkit', 'Telematics', 'Evidence store', 'Identity vault (PII)'];
  src.forEach((t, i) => { box(s, 0.5, 1.85 + i * 0.66, 2.5, 0.54, i === 0 ? 'FDE7E3' : i === 6 ? 'E6F2EC' : 'E8EEFC'); text(s, t, 0.6, 1.85 + i * 0.66, 2.3, 0.54, { fontSize: 12, valign: 'middle' }); });
  arrow(s, 3.05, 4.0, 3.5, 4.0);
  card(s, 3.5, 1.85, 2.6, 4.45, 'Normalise', ['Source id, version, retrieval time', 'Status: ok / partial / error', 'Missing fields + conflicts', 'Candidate links (same reporter + trip)'], { size: 12 });
  arrow(s, 6.15, 3.0, 6.55, 2.55); arrow(s, 6.15, 4.6, 6.55, 4.9);
  box(s, 6.55, 1.85, 3.0, 1.4, 'FDE7E3'); text(s, 'Structured danger checks', 6.7, 1.95, 2.7, 0.35, { fontSize: 14, bold: true, color: 'A3130A' }); text(s, 'At receipt, no AI: SOS · GPS near home after trip · live stop → alert + route A', 6.7, 2.32, 2.75, 0.9, { fontSize: 12 });
  card(s, 6.55, 3.4, 3.0, 2.9, 'AI preparation', ['Smart summary', 'Translation (labelled live / fixture / none)', 'Triage: tier, confidence, uncertainty', 'Policy: conditions, checks, “not covered”', 'Recommendation: step, actor, urgency'], { size: 12 });
  arrow(s, 9.6, 4.0, 10.0, 4.0);
  card(s, 10.0, 1.85, 2.85, 4.45, 'Validate, then floor', ['Schema + allowed values; invalid → safest (L3 review)', 'Citations must be SP-1..9', 'Injection text removed before any model sees it; rules read the original', 'Deterministic floors: SP-7, SP-8, SP-6, injection', 'Unsupported language → provisional L2, never L1', 'Outage → keep last assessment; humans continue'], { size: 12, fill: 'F6F6F6' });
  legend(s, ['Implemented', 'Simulated', 'Open'], 6.72);
  text(s, 'Open: live Claude path implemented but not run or benchmarked here', 0.5, 6.62, 8, 0.35, { fontSize: 11, color: 'A3130A' });
}

// 8 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', null, '8 · Safety, privacy, automation and execution controls', 'Controls are code and tests, not prompts, and nothing claims to have happened unless it executed',
    'Four groups of controls. Execution goes through a clearly labelled simulated adapter; about 5% of actions fail deterministically so the exception path is exercised. Redaction is pattern-based, not anonymisation; local JSONL is durable but not tamper-proof.');
  card(s, 0.5, 1.85, 6.05, 2.25, 'Safety', ['SP-7 danger → manager lane + alert, whatever the AI says', 'SP-8 violence / sexual → human review despite counter-evidence', 'SP-9 same-behaviour history → +1 tier', 'Report text is data: injection flagged → specialist', 'A reporter’s report count is never counter-evidence'], { size: 12 });
  card(s, 6.8, 1.85, 6.05, 2.25, 'Privacy', ['Server-side scopes; browser never gets raw PII to hide', 'Masked by default; reveal needs ownership + logged reason', 'Redaction + injection removal + pseudonymous IDs before external AI', 'Hash-chained access log (tamper-evident) · exports: managers only, no PII', 'Retention by tier: L1 180 d · L2 365 d · L3/L4 730 d · log 3 yrs'], { size: 12 });
  card(s, 0.5, 4.25, 6.05, 2.3, 'Automation', ['Shadow by default; demo switch for fictional SP-1 only', 'Second key: text-only SP-1 needs a live model to agree; else one-click human confirm', 'States: eligible → queued → running → completed / failed → sent to review → reopened', 'Failure or reopen requires explicit release before re-automation'], { size: 12 });
  card(s, 6.8, 4.25, 6.05, 2.3, 'Execution', ['Recommendation → decision → execution → confirmed outcome', 'Idempotency keys on every command; execution keys per decision', 'Draft ≠ sent · approved escalation ≠ acknowledged handoff · attempt ≠ resolved'], { size: 12 });
  legend(s, ['Implemented', 'Simulated']);
}

// 9 ─────────────────────────────────────────────────────────────
{
  const s = slide('CONTENT', 'Evidence', '9 · SLAs, quality measures and acceptance evidence', 'Measured routing safety is strong; accuracy is not yet independently validated',
    'Measured on the prototype with the simulated provider. Silver labels are scenario-level and AI-assisted; the 30 reference labels were drafted by AI and await the candidate’s adjudication, so no independent validation is claimed. Over-triage rose because unsupported languages now go to humans.');
  const rows = [
    ['L4 cases routed to duty manager', '138 / 138', 'Measured'], ['L3+ recall (silver)', '519 / 523 (misses → human L2)', 'Measured'], ['Automated cases whose label isn’t L1', '0 (demo automation on)', 'Measured'],
    ['Over-triage vs silver', '404 (mostly not-understood languages)', 'Measured'], ['Acceptance tests', '40/40 unit+API · 5/5 browser', 'Measured'], ['AI-drafted reference set (30)', '29/30, not independent', 'Open'],
  ];
  rows.forEach(([k, v, t], i) => { const y = 1.9 + i * 0.6; box(s, 0.5, y, 7.4, 0.5, i % 2 ? HEX.white : HEX.g50); text(s, k, 0.65, y, 3.4, 0.5, { fontSize: 13, valign: 'middle' }); text(s, v, 4.0, y, 2.8, 0.5, { fontSize: 13, bold: true, valign: 'middle' }); tag(s, t, 6.85, y + 0.12); });
  text(s, 'Tests prove coded rules behave as specified, not policy completeness or production safety.', 0.5, 5.6, 7.4, 0.5, { fontSize: 12, color: '545454' });
  card(s, 8.2, 1.9, 4.65, 2.4, 'SLA rules', ['Deadline = receipt + SLA of highest tier ever held', 'Escalation tightens; downgrade never loosens', 'No pause while awaiting information', 'Stops at first substantive response, not acknowledgement'], { size: 12 });
  card(s, 8.2, 4.45, 4.65, 2.05, 'Proposed quality measures', ['L4 ack < 5 min p95 · SLA ≥ 98%', 'Override rate < 10% (tracked)', 'QA: 0 L3+ in auto lane; per-language precision'], { size: 12, fill: 'EFE9FB' });
  legend(s, ['Measured', 'Target', 'Open']);
}

// 10 ────────────────────────────────────────────────────────────
{
  const s = slide('DARK', 'Plan', '10 · MVP priorities, rollout, dependencies and open decisions', 'Shadow first, assist next, automate only where measurement earns it',
    'Phases are proposals. Dependencies sit mostly outside engineering. Five decisions are needed from leadership and the policy owner before live AI or automation.');
  const ph = [['Phase 0 · 4 wks', 'Foundations', 'Source APIs, SSO roles, DPIA, vendor DPA, policy rulings, measured baselines'], ['Phase 1 · 4 wks', 'Shadow, 2 markets', 'Console alongside old tools; AI proposes, nobody acts; double-label QA'], ['Phase 2 · 6 wks', 'Assist', 'Console primary; L4 paging live; humans decide everything'], ['Phase 3', 'Automate SP-1', 'Per market × language × category once precision ≥ 99.5% for 2 weeks']];
  ph.forEach(([a, b, c], i) => { const x = 0.5 + i * 3.1; box(s, x, 1.95, 2.95, 1.95, '1F1F1F'); text(s, a, x + 0.18, 2.05, 2.6, 0.3, { fontSize: 11, color: 'CBCBCB' }); text(s, b, x + 0.18, 2.35, 2.6, 0.4, { fontSize: 16, bold: true, color: C.background1 }); text(s, c, x + 0.18, 2.8, 2.6, 1.05, { fontSize: 12, color: 'EEEEEE' }); if (i < 3) arrow(s, x + 2.97, 2.9, x + 3.08, 2.9, 'CBCBCB'); });
  card(s, 0.5, 4.15, 5.9, 2.4, 'Dependencies', ['Platform/data: read APIs for ticketing, trip, telematics, toolkit, history', 'Security: SSO + capability groups; audit store', 'Privacy/legal: DPIA, residency, retention schedule, vendor DPA', 'Safety ops: on-call paging, QA reviewers per language'], { size: 12, fill: '1F1F1F', fg: 'FFFFFF' });
  box(s, 6.6, 4.15, 6.25, 2.4, HEX.white);
  text(s, 'Open decisions', 6.8, 4.27, 5.8, 0.35, { fontSize: 15, bold: true });
  text(s, ['Approve Phase 0–1 and a 2-market shadow pilot', 'Build control layer, buy model (vendor criteria)', 'Policy rulings: SP-9 into L4, service animals, unregistered passenger, account takeover', 'Automation bar (≥ 99.5% precision) and QA owner', 'Privacy sign-off path for live AI'].map((t, i, a) => ({ text: t, options: { bullet: { type: 'number' }, breakLine: i < a.length - 1, paraSpaceAfter: 3 } })), 6.8, 4.65, 5.85, 1.85, { fontSize: 12, color: '000000' });
  text(s, 'Proposed plan. This mini-PRD does not replace the executive presentation required by the brief.', 0.5, 6.68, 9, 0.3, { fontSize: 10, color: 'CBCBCB' });
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  const themePath = process.argv[2];
  if (themePath) { const { applyTheme } = require(themePath); await applyTheme(OUT, THEME); }
  console.log('wrote', OUT, n, 'slides');
})();
