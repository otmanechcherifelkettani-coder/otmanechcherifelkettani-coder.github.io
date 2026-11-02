# Decisions and assumptions

## Principle
Automate the groundwork, not the accountability. Severity, danger, handling lane, workflow status, ownership and permissions are separate concepts with separate fields (see README).

## Smallest coherent change set (what was rebuilt vs reused)
- **Reused:** the multilingual lexicon, signal extraction, simulated provider, deterministic floors (`guardrails.js`), policy data, PII masking and redaction, policy Q&A, the timezone map, and the silver reference labeller.
- **Rebuilt:** case state (now event-sourced), routing (three lanes), the server-side API with scoped views, execution tracking, and the UI (sign-in, Overview, Agent workspace, Duty-manager workspace).
- **Removed:** the browser-only pipeline (`app.js`, `store.js`, `triage.js`). It sent all data to the browser and mixed severity with lane and status.

## Routing precedence
1. **Duty manager (Lane A):** current severity is L4, *or any* danger signal (structured, text or AI).
   - Structured checks (live SOS, the reported party's GPS near the reporter's home after the trip, a report filed mid-trip with the vehicle stopped) run at receipt, *before* AI preparation.
   - A hostile or wrong AI proposal cannot lower the lane (test D4).
2. **Automation (Lane B):** every gate must pass. The gates are:
   - L1, with an explicit SP-1 category (minor conduct, rating-only threat);
   - complete material evidence;
   - a supported language;
   - no protected allegation, active or past danger, repeat-conduct history, policy gap, injection, conflict or candidate link;
   - no safety-feature use;
   - confidence ≥ 0.75;
   - no prior human reassessment or failed automation (each needs an explicit release);
   - **second key:** if only the reporter's words support SP-1 (no system observation such as an ETA slip, route tolerance or a no-damage photo), a *live* model must independently agree it is L1. Otherwise a human confirms with one click. This affects 771 of the 3,227 L1 cases.

   **Default: shadow mode.** Eligibility is recorded but cases go to agents. Duty managers can enable it for the fictional SP-1 demo.
3. **Agent (Lane C):** everything else. L3 needs a capability: violence and sexual misconduct; threats and exposure; or safety incidents. Low confidence or missing evidence blocks automation but does not make a case a manager emergency.

## Controlled reassessment (manager)
- Requires: an acknowledged alert, being the accountable owner, a new tier, a danger assessment (ongoing / no longer present / incorrectly detected), at least one cited evidence source, a policy clause, a reason of 20+ characters, and a human destination queue matched to the tier.
- "Ongoing" danger cannot leave L4.
- **Preserved:** the AI proposal and its history, danger signals, every alert and acknowledgement, prior decisions, the receipt time and the deadline. `max_held` never decreases, so breaches stay breaches.
- **Outcome:** the severity becomes the human-reviewed value and the case is handed off (pending acceptance) to a human queue. It is never resolved and never released to automation (`release_required`).
- **Second approval:** a hook exists (`requiresSecondApproval`). It returns false because no fictional policy clause requires one.

## SLA and clocks
- Deadline = receipt + SLA of the **highest tier ever held**. Escalation tightens it, a downgrade never loosens it, and a late escalation can be breached immediately.
- Linked follow-ups take the earliest applicable deadline in their link group.
- Awaiting information does **not** pause the clock; the policy allows no pause.
- The clock stops at the first **substantive** response: a reporter-facing action that actually executed, or a manager recording "reporter reached". An acknowledgement is not a response.
- Tracked separately: receipt, alert created, alert acknowledged, assigned, first response, decided, executed, resolved.
- **Replay clock:** the data has naive local timestamps (converted per city to UTC, `src/tz.js`) and no response history. "Now" starts at `REPLAY_NOW` (default 2026-03-08 08:00 UTC, after the last submission) and advances in real time. No historical SLA performance is claimed.

## Permissions (enforced server-side)
- **Agent:** sees agent-lane cases in its regions whose required capability it holds, plus cases it owns.
  - For cases it handed off, it sees **status only**.
  - It acts only on unowned or own agent-lane cases.
  - It reveals personal data only on cases it owns, with a logged reason. No export.
- **Duty manager:** sees all regions; acts on manager-lane cases; reopens resolved cases; changes the automation mode; exports. Reveals personal data with a logged reason.
- Sign-in is simulated (a profile picker that issues a session token). The browser receives only scoped, masked data. The raw dataset file is not served.

## Policy interpretation and gaps (unchanged, need a policy-owner ruling)
- SP-9 lifting L3 → L4 (38 cases).
- Service animals (treated under SP-5).
- Unregistered passenger, and account takeover (L3).
- Safety-feature use with no alleged act (L2, not SP-1-eligible).
- Rating-only threats (L1).
- Not understood → provisional L2 for human review, never L1.

## Data and evidence
- Each nested block is treated as a separate mocked source with id, status, version and retrieval time, recorded at the replay receipt time.
- A reporter's number of past reports is **never** counter-evidence. That earlier signal was removed.

## Ported from the alternative build
Four ideas were taken from a separately built version of this exercise and re-implemented here with tests (`tests/ports.test.mjs`):
1. **Hash-chained access log** (`server/eventlog.mjs`, `/api/audit/verify`). It is tamper-evident; retention purges only a prefix and records the anchor the chain resumes from.
2. **Retention by tier** after resolution: L1 180 d, L2 365 d, L3/L4 730 d (env `RETENTION_L*_DAYS`); access log 3 years (`ACCESS_LOG_RETENTION_DAYS`). Expired work records become a `record.purged` tombstone, so the case never re-enters a queue.
3. **Injection removed from model input** (`src/sanitize.js`). Delimited directives and directive clauses are replaced by "⟪instruction removed⟫" unless the clause also carries harm, danger or violence language. The rules and floors still read the original text.
4. **Second key for text-only SP-1 automation** (`routing.automationEligibility`), as described above.
