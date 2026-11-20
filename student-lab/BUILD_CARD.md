# Build card — Atlas Telecom level-1 support agent

## Q1 · Where is the value?
- **User:** Atlas customers writing on WhatsApp about internet or bills.
- **Problem:** they wait 4 hours for a first reply.
- **Baseline → target:** time to first response 4 h → **5 min**.
- **Must not break (guardrail metrics):** share solved without a technician stays ≥ 60%; zero credits above 50 MAD; no customer data given to the wrong person.

## Q2 · What is worth building?
| Kill filter | Answer |
|---|---|
| Needs AI? | Yes. Free text in French, Darija, English, mixed, with typos; keyword rules can't read it. |
| Cost of being wrong | Medium: money (goodwill credits) and privacy (another customer's data). |
| Would a free chatbot do it? | No. It has no access to Atlas's customer data or tools. |
| Can the output be checked? | Yes. Code checks the actions (tools called, credit ≤ 50 MAD); an LLM judge checks the wording against a rubric. |

**Pattern: agent.** The steps depend on the message (an outage needs one lookup; a compensation request needs verification, ticket history, then a decision between a credit and a human).
Risk tier: medium → hidden-test pass bar 90% for graduation (85% eval bar today).
