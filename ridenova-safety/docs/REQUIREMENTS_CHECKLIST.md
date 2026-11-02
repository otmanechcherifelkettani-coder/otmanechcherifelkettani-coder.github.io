# Requirement-to-evidence checklist

Status key: **Implemented** (works, tested) · **Simulated** (works against a labelled simulation) · **Partial** · **Not done**.
Test IDs: `D` = tests/domain.test.mjs, `A` = tests/api.test.mjs, `P` = tests/pii_ai.test.mjs, `E` = tests/e2e/workflows.e2e.mjs.
Last run: 40/40 unit and API tests and 5/5 browser tests passing. `T` = tests/ports.test.mjs.

## Original brief (authoritative)

| Requirement | Status | Evidence |
|---|---|---|
| Unify ticket, trip/party, safety-feature, telematics, history and policy sources; label each fact's source | Implemented | `assess.evidenceSources`, case view “What evidence is available?”; D16 |
| AI summarises, translates, proposes tier and action with confidence and rationale | Simulated (demo) / Implemented (live path, not run) | `server/providers.mjs`; D4, A13 |
| Policy Q&A with citations or “Not covered” | Implemented | `src/policyqa.js`, `/api/policy/ask`; P4 |
| Approve, override (choose action) or escalate with a reason, on the same screen | Implemented | Agent workspace; D15, E(b) |
| L1 auto-resolution follows policy; AI never closes L3/L4; danger → immediate alert, never auto-closed or downgraded | Implemented | `routing.js`; D4, D7, D10b |
| SP-8: violence or sexual allegations need human review despite counter-evidence | Implemented | D “policy · SP-8” |
| Masking, role-based access, redaction before external AI, retention, access logging | Implemented (prototype grade): hash-chained access log, retention by tier | T1, T1b, T2,  `views.caseView`, `/reveal`, `eventlog` retention; A18/19, P1–2, D19b |
| Different paths for low and critical cases; all 5,000 load; queue by severity then deadline; region/country/language filters; on-demand translation | Implemented | D1, D2, A1, E(e) |
| Structured records, search, CSV/JSON export with the minimum columns | Implemented | `views.exportRow`; D18, A18 |
| README (~5 commands), working AI integration, key-free demo, no secrets, tests, replaceable provider | Implemented (live path unrun) | README; `providers.mjs` |
| Validation on 20–30 self-labelled cases | **Partial**: 30 AI-drafted reference labels; candidate adjudication pending | `validation/reference_labels_ai_drafted.json`, `candidate_adjudication.json` |
| Executive deck (~10 slides + annex) | Implemented (separate from the mini-PRD) | `deck.html` |

## Operating-model spec

| § | Requirement | Status | Evidence |
|---|---|---|---|
| 3 | Separate fields for severity (proposed, current, reviewed), confidence and calibration, evidence completeness, danger, lane, workflow, queue and owner, policy version, proposed action, decision, execution, timestamps | Implemented | `src/domain/case.js` |
| 3 | History of values preserved | Implemented | Event history on every case; `ai_history` |
| 3 | New AI assessment never overwrites a human decision | Implemented | D “AI re-assessment never…” |
| 3 | New danger after a downgrade → fresh escalation | Implemented | D10b, E(d) optional step |
| 3 | Case, incident and trip IDs distinct; repeated IDs are candidate links | Implemented | D16 |
| 4 | Lane A: L4 or any danger, regardless of AI | Implemented | D4 |
| 4 | Lane B: explicit eligibility; upstream; recorded states; L1 ≠ eligible; shadow by default | Implemented / Simulated execution | D7, D8, E(a) |
| 4 | Lane C: qualified agent; L3 needs capability; low confidence blocks automation without forcing a manager emergency | Implemented | D5/6, A5/6 |
| 5 | Agent and duty-manager profiles; backend enforcement; selector labelled simulated | Implemented | `permissions.js`; A5/6; sign-in screen |
| 6 | Controlled manager reassessment: severities, danger assessment, evidence, policy, reason, identity, time, destination; preserves alerts, clocks and history; never closes or automates; second approval only if policy requires | Implemented (second-approval hook returns false: the fictional policy requires none) | D9, D10/11, E(d) |
| 7 | Overview with distinct denominators, distributions by basis, provisional, handling split, unacknowledged alerts, SLA by tier, automation failures, exceptions and reopened; default and advanced filters | Implemented | `views.overview`; D2, D3, E(e) |
| 7 | Agent workspace: five questions, one primary action, progressive disclosure | Implemented | E(b) |
| 7 | Duty-manager workspace: danger reason, timing, owner, next steps, gaps, controlled reassessment and handoff | Implemented | E(c), E(d) |
| 8 | Structured danger checks before AI preparation | Implemented | D4b |
| 8 | Source identity, version, retrieval status, missing data, conflicts | Implemented (mocked sources) | `evidenceSources`, `assessPolicy` |
| 8 | Summary separates allegation, observation, history and AI interpretation | Implemented | Agent workspace labels |
| 8 | Triage, policy assessment and recommendation outputs; translation labelled; unsupported translation is never low risk | Implemented | D14, A14 |
| 8 | Replaceable provider, structured validation, citation validation, explicit failures | Implemented | `providers.mjs`, `ai.validateTriage`; P5, A13 |
| 9 | SP-7, SP-8, SP-9; frequent reporters not penalised; public text treated as data (and directives removed from model input, T3); second key for text-only automation (T4) | Implemented | D policy tests, P3 |
| 9 | Outage, malformed output, gaps and missing evidence leave a human path | Implemented | A13, P5 |
| 9 | Recommendation → decision → execution → confirmed outcome kept distinct | Implemented | D15 |
| 9 | Automation states; idempotency; simulated adapter | Implemented / Simulated | D8, D19a, A19 |
| 10 | Every active case has a queue or owner; lifecycle with escalation and reopening | Implemented | `case.js`, `workbench.command` |
| 10 | Separate timestamps; clocks never reset; escalation tightens; no pause while awaiting information | Implemented | `sla.js`; D10/11, D “SLA” |
| 10 | Replay and timezone assumptions documented; no historical SLA claimed | Implemented | DECISIONS.md, Overview copy |
| 11 | Backend boundaries, masking, minimisation (incl. injection removal before inference), tamper-evident access log, decision logging, persistent versioned records, tier-based retention, protected exports | Implemented (prototype grade; see LIMITATIONS) | A17, A18/19 |
| 11 | Overrides and errors captured for QA; no automatic retraining | Partial: captured in the event log; no QA sampling UI | — |
| 12 | Accessibility: keyboard navigation, labelled controls, text labels with colours, responsive layout | Partial: skip link, focus styles, j/k navigation, labelled controls, text labels; no formal WCAG audit | — |
| 13 | Tests 1–20 | Implemented: see the mapping in the test titles | all test files |
| 14 | Editable 10-slide mini-PRD | Implemented | `docs/RideNova_Workbench_MiniPRD.pptx` |
