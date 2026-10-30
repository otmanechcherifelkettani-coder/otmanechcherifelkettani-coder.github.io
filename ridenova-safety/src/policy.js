// RideNova fictional safety policy (from the brief) as structured, citable data.

export const TIERS = {
  L4: { rank: 4, name: 'Critical', slaMin: 15, desc: 'Danger now' },
  L3: { rank: 3, name: 'High', slaMin: 240, desc: 'Credible threat or risk' },
  L2: { rank: 2, name: 'Moderate', slaMin: 1440, desc: 'Rule violation, repeat pattern or property damage' },
  L1: { rank: 1, name: 'Low', slaMin: 2880, desc: 'No danger' },
};
export const TIER_ORDER = ['L1', 'L2', 'L3', 'L4'];
export const rank = (t) => TIERS[t]?.rank ?? 0;
export const maxTier = (a, b) => (rank(a) >= rank(b) ? a : b);
export const raiseTier = (t, by = 1) => TIER_ORDER[Math.min(3, TIER_ORDER.indexOf(t) + by)];

export const ACTIONS = ['AUTO_RESOLVE_L1', 'ROUTE_L2_REVIEW', 'ROUTE_L3_REVIEW', 'ESCALATE_L4_IMMEDIATE', 'REQUEST_MORE_INFO', 'MERGE_DUPLICATE'];
export const defaultAction = (tier) => ({ L1: 'AUTO_RESOLVE_L1', L2: 'ROUTE_L2_REVIEW', L3: 'ROUTE_L3_REVIEW', L4: 'ESCALATE_L4_IMMEDIATE' })[tier];

export const POLICY = [
  { id: 'SP-1', title: 'Minor complaints', tier: 'L1',
    text: 'Minor conduct, lateness or route complaints with no safety signal and no repeat pattern can be closed with a message, credit or no-violation note: L1.',
    keywords: ['minor', 'rude', 'late', 'lateness', 'route', 'detour', 'fare', 'price', 'credit', 'close', 'closed', 'auto', 'resolve', 'conduct', 'music', 'temperature', 'ac', 'refund', 'message', 'no-violation'] },
  { id: 'SP-2', title: 'Property damage and smoking', tier: 'L2',
    text: 'Property damage over USD 50, or smoking/vaping after a request to stop: L2.',
    keywords: ['damage', 'property', 'stain', 'spill', 'cleaning', 'usd', '50', 'smoking', 'smoke', 'vaping', 'vape', 'cigarette', 'fee', 'quote'] },
  { id: 'SP-3', title: 'Driving and collisions', tier: 'L2/L3',
    text: 'Speeding or harsh driving confirmed by telematics: L2. A collision with possible injury: L3.',
    keywords: ['speeding', 'speed', 'harsh', 'braking', 'brake', 'telematics', 'collision', 'crash', 'accident', 'injury', 'injured', 'driving', 'phone', 'lane'] },
  { id: 'SP-4', title: 'Off-app payment or personal contact', tier: 'L2/L3',
    text: 'Asking for off-app payment or personal contact: L2. If combined with a threat or unsafe action: L3.',
    keywords: ['cash', 'payment', 'off-app', 'pay', 'money', 'number', 'phone', 'contact', 'personal', 'instagram', 'whatsapp', 'date', 'extra'] },
  { id: 'SP-5', title: 'Discriminatory remarks', tier: 'L2/L3',
    text: 'One non-threatening discriminatory remark: L2. Repeated remarks or remarks combined with threats: L3.',
    keywords: ['discriminatory', 'discrimination', 'racist', 'racism', 'remark', 'slur', 'accent', 'religion', 'gender', 'homophobic'] },
  { id: 'SP-6', title: 'Threats, unwanted advances and location exposure', tier: 'L3',
    text: 'Credible threats, unwanted advances with aggravating factors—such as repeat conduct, a vulnerable situation or continuing after refusal—and post-trip contact revealing the reporter’s location: L3.',
    keywords: ['threat', 'threaten', 'advance', 'advances', 'flirt', 'unwanted', 'refusal', 'location', 'home', 'address', 'post-trip', 'after', 'trip', 'contact', 'vulnerable', 'repeat'] },
  { id: 'SP-7', title: 'Danger signals', tier: 'L4',
    text: 'Examples include live SOS, medical emergency, ongoing or imminent danger, stalking in progress, minors in danger, a weapon or law-enforcement involvement. This list is not exhaustive. A human duty manager must be alerted immediately. Automation may assist but must never close, downgrade or resolve these cases.',
    keywords: ['sos', 'emergency', 'medical', 'danger', 'imminent', 'stalking', 'minor', 'minors', 'child', 'weapon', 'gun', 'knife', 'police', 'law', 'enforcement', 'duty', 'manager', 'alert', 'unconscious'] },
  { id: 'SP-8', title: 'Violence or sexual misconduct', tier: '—',
    text: 'An allegation of violence or sexual misconduct must never be closed without human review, regardless of counter-evidence.',
    keywords: ['violence', 'violent', 'assault', 'sexual', 'misconduct', 'touch', 'touched', 'hit', 'attack', 'counter-evidence', 'review', 'grope'] },
  { id: 'SP-9', title: 'Previous conduct', tier: '+1',
    text: 'A prior flag for the same behavior within the last 12 months raises the tier by at least one level when the new report is credible.',
    keywords: ['prior', 'previous', 'history', 'flag', 'repeat', 'months', '12', 'raise', 'same', 'behavior', 'behaviour', 'again'] },
];
export const policyById = Object.fromEntries(POLICY.map((p) => [p.id, p]));
