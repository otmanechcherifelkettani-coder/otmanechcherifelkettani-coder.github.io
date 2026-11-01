// Static domain catalogue: queues, capabilities, simulated users, actions, SLAs.
// Everything here is FICTIONAL and exists for the RideNova exercise only.

export const POLICY_VERSION = 'RN-SP-2026.03 (fictional brief, SP-1..SP-9)';

export const SLA_MIN = { L1: 2880, L2: 1440, L3: 240, L4: 15 };
export const TIER_RANK = { L1: 1, L2: 2, L3: 3, L4: 4 };
export const TIERS = ['L1', 'L2', 'L3', 'L4'];
export const rank = (t) => TIER_RANK[t] || 0;
export const maxTier = (a, b) => (rank(a) >= rank(b) ? a : b);

// Languages where the demo lexicon has meaningful coverage. Others are "not understood" by the
// simulated provider: never a low-risk default, never automation.
export const SUPPORTED_LANGUAGES = new Set(['en', 'es', 'fr', 'pt', 'ar', 'de', 'ja', 'zh-Hant', 'tr', 'hi', 'it', 'nl', 'pl', 'ko']);

// Capabilities required for specialist (L3) work. Invented for the exercise; the brief defines none.
export const CAPABILITIES = {
  general: 'General safety review (L1/L2)',
  threats_exposure: 'Threats, stalking & location exposure',
  violence_sexual: 'Violence & sexual misconduct',
  safety_incidents: 'Collisions, unsafe situations & account integrity',
};

export const QUEUES = {
  'duty-managers': { label: 'Duty managers', lane: 'manager', capability: null },
  'l3-violence-sexual': { label: 'L3 · Violence & sexual misconduct', lane: 'agent', capability: 'violence_sexual' },
  'l3-threats-exposure': { label: 'L3 · Threats & exposure', lane: 'agent', capability: 'threats_exposure' },
  'l3-safety-incidents': { label: 'L3 · Safety incidents', lane: 'agent', capability: 'safety_incidents' },
  'general-review': { label: 'General review (L1/L2)', lane: 'agent', capability: 'general' },
  automation: { label: 'Upstream automation', lane: 'automation', capability: null },
};

export const CATEGORY_CAPABILITY = {
  violence: 'violence_sexual',
  threat: 'threats_exposure', post_trip_contact: 'threats_exposure', personal_contact: 'threats_exposure', stalking: 'threats_exposure',
  collision: 'safety_incidents', unsafe_drop: 'safety_incidents', vulnerable: 'safety_incidents', impersonation: 'safety_incidents',
};
export const capabilityQueue = (cap) => Object.entries(QUEUES).find(([, q]) => q.capability === cap)?.[0] || 'general-review';

// Simulated directory. Sign-in is simulated; the SERVER enforces these scopes on every request.
export const USERS = {
  'u-agent-emea': { id: 'u-agent-emea', name: 'Alex Moreau', role: 'agent', regions: ['EMEA'], capabilities: ['general'] },
  'u-agent-amer': { id: 'u-agent-amer', name: 'Sam Rivera', role: 'agent', regions: ['US&C', 'LatAm'], capabilities: ['general'] },
  'u-agent-apac': { id: 'u-agent-apac', name: 'Mei Tanaka', role: 'agent', regions: ['APAC'], capabilities: ['general'] },
  'u-spec-threats': { id: 'u-spec-threats', name: 'Priya Shah', role: 'agent', regions: ['EMEA', 'US&C', 'APAC', 'LatAm'], capabilities: ['general', 'threats_exposure', 'violence_sexual'] },
  'u-spec-incidents': { id: 'u-spec-incidents', name: 'Diego Alves', role: 'agent', regions: ['EMEA', 'US&C', 'APAC', 'LatAm'], capabilities: ['general', 'safety_incidents'] },
  'u-dm-1': { id: 'u-dm-1', name: 'Jordan Lee', role: 'duty_manager', regions: ['EMEA', 'US&C', 'APAC', 'LatAm'], capabilities: Object.keys(CAPABILITIES) },
  'u-dm-2': { id: 'u-dm-2', name: 'Nadia Karim', role: 'duty_manager', regions: ['EMEA', 'US&C', 'APAC', 'LatAm'], capabilities: Object.keys(CAPABILITIES) },
};

// Executable actions (all executed by a SIMULATED adapter — nothing real is sent or changed).
export const EXEC_ACTIONS = {
  send_feedback_note: { label: 'Send feedback / no-violation note to reporter', reporter_facing: true, resolves: true },
  issue_goodwill_credit: { label: 'Issue goodwill credit + note', reporter_facing: true, resolves: true },
  warn_reported_party: { label: 'Send policy warning to reported party + note to reporter', reporter_facing: true, resolves: true },
  charge_cleaning_fee: { label: 'Charge cleaning fee to rider + confirm to driver', reporter_facing: true, resolves: true },
  request_more_info: { label: 'Ask reporter for more information', reporter_facing: true, resolves: false },
  safety_followup: { label: 'Safety follow-up message to reporter', reporter_facing: true, resolves: false },
  restrict_rematch: { label: 'Block re-matching between the parties', reporter_facing: false, resolves: false },
  suspend_reported_party: { label: 'Temporarily suspend reported party pending investigation', reporter_facing: false, resolves: false },
};
