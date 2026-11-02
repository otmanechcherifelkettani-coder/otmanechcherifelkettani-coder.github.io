# RideNova Safety Workbench

A role-based investigation console for the fictional RideNova safety case study.

> **Automate the groundwork, not the accountability.**

It ingests and structures the evidence, proposes severity, assesses the fictional policy (SP-1..SP-9), and routes each case to one of three lanes: duty manager, eligible upstream automation, or a qualified agent. It gives that person a summary and a concrete next step, and records the decision, the (simulated) execution, the outcome and the history.

*Everything here is synthetic: the company, the data, the policy, sign-in and every executed action. This is not a production or real-company application.*

## Run it

Requires Node ≥ 20.

```bash
cd ridenova-safety
npm install                 # Anthropic SDK, used only if you set a key
npm test                    # 44 unit + API acceptance tests
npm run test:e2e            # 5 real-browser workflow tests (needs Playwright + Chromium)
npm start                   # http://localhost:8080/console.html  (simulated AI, automation in shadow mode)
```

Optional settings:
- `ANTHROPIC_API_KEY=… npm start` enables live AI for re-assessment, translation and policy Q&A.
- `npm run evaluate` re-runs validation over all 5,000 cases.
- Other settings (`REPLAY_NOW`, `AUTOMATION_MODE`, `AI_MODEL`, `SIM_FAIL_PCT`, `RETENTION_L1_DAYS`…`RETENTION_L4_DAYS`, `ACCESS_LOG_RETENTION_DAYS`) are listed in `server/server.mjs`.

Records persist in `data/runtime/*.jsonl` (gitignored). Delete that folder to reset the demo.

The workbench **needs its server**, because permissions and masking are enforced there. The case-solution page (`index.html`) and the executive deck (`deck.html`) are static.

## Operating model

| Concept | Field(s) — kept separate |
|---|---|
| Severity | `severity.proposed` (AI) · `severity.current` (operational) · `severity.reviewed` (human) · `severity.max_held` (drives the deadline) |
| Danger | `danger.status` (none / detected / ongoing / no_longer_present / incorrectly_detected) · `danger.signals[]` · `danger.alerts[]` (each with its own acknowledgement) |
| Handling | `lane` (manager / automation / agent) · `queue` · `owner` · `workflow` (awaiting triage → assigned → under review → awaiting information → resolved; reopened) |
| Assessment | `confidence` (uncalibrated) · `evidence_completeness` · `understanding` (language supported?) · `policy` (version, conditions, mandatory checks, conflicts, missing, gap) |
| Work | `recommendation` → `decisions[]` → `executions[]` (queued / running / completed / failed) → `resolution` |
| Automation | `automation.state` (not applicable / shadow-eligible / eligible / queued / running / completed / failed / sent to review / reopened) + every exclusion reason |
| Time | receipt · alert created · alert acknowledged · assigned · first response · decided · executed · resolved |
| Links | `incident_id` + candidate links. Same reporter and trip is a *candidate*, never an automatic merge. |

Every change is an event. State is the fold of the event list, and the full history is shown on each case.

**Also:**
- The access log is hash-chained (tamper-evident) and verified on the Overview.
- Work records are retained by tier after resolution.
- Instructions aimed at the triage system are removed before any model sees the text.
- Text-only SP-1 cases need a live model's agreement before automation (the "second key").

**Routing precedence:**
1. **Lane A, duty manager:** current severity is L4, *or any* danger signal, whatever the AI proposed.
2. **Lane B, automation:** explicit SP-1 eligibility *and* every exclusion clear. It is off (shadow) by default.
3. **Lane C, agent:** everything else. L3 goes to a specialist queue that needs a matching capability.

## Screens

- **Overview:** "Where is operational attention needed?" It opens with *your scope* (for example, Mei Tanaka, an APAC general agent, sees 803 of 5,000 cases; duty managers see all 5,000). Default filters (received or decision date, region, country, product, language, reporter persona, severity with its basis, workflow) plus advanced filters. Every breakdown sums to the filtered population.
- **Agent workspace:** five questions (what happened, evidence, policy, uncertainty, next step) and one primary action. Secondary actions and deeper evidence open on demand.
- **Duty-manager workspace:** the danger reason first, with the on-call page it triggered. Then the timing strip, ownership, and four numbered steps: contact the reporter, emergency services, protection, and **close the case** (danger status, outcome, reason). Reassessment and handoff sit behind “Not a danger case after all?”.
- **English by default:** every non-English report shows a stored English translation under the original, labelled as prepared in advance (not live AI).
- **Company systems:** each case shows its support-ticket reference and each action its target system (messaging, payments, account enforcement). These are mock adapters; see `src/domain/integrations.js`.

## Docs

- [`docs/REQUIREMENTS_CHECKLIST.md`](docs/REQUIREMENTS_CHECKLIST.md): each requirement mapped to code and tests, with status.
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md): five-part demo (automation and an exception, agent investigation, manager escalation, justified downgrade, overview reconciliation).
- [`docs/DECISIONS.md`](docs/DECISIONS.md): routing, SLA, permissions, replay clock, policy interpretation.
- [`docs/VALIDATION.md`](docs/VALIDATION.md): measured results and what they do **not** prove.
- [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md): explicit remaining limitations.
- [`docs/AI_LOG.md`](docs/AI_LOG.md): how AI was used.
- `docs/RideNova_Workbench_MiniPRD.pptx`: editable 10-slide mini-PRD.

## Layout

```
server/      app.mjs (HTTP API, sessions, scopes) · providers.mjs (AI interface: simulated / Anthropic / failing) · eventlog.mjs (JSONL)
src/domain/  catalog · case (state + reducer) · assess (evidence, policy, recommendation) · routing (lanes) · sla · permissions · execution (simulated adapter) · workbench (commands) · views (read models, overview, export)
src/         signals · lexicon · simulated · guardrails · policy · pii · policyqa · tz · ai (output validation)
src/ui/      workbench.js (three screens)        tests/  domain · api · pii_ai · e2e
```
