# Instructor notes — 1-Day Lab simulation, student run 1

Student profile: bac+4 HESTIM, comfortable with computers, never built an agent, never used Claude Code.
Setup: empty Claude Code session, case = Atlas Telecom (unless changed at build card), agent model claude-haiku-5-5, budget < $2.
Format note: one student alone (not a team of 3–4), so the red-team swap is replaced by me attacking the student's agent.

## Running cost
| Gate | Spend so far |
|---|---|
| Opening | $0.00 (no API calls yet) |

## Block log

### Block 1 — The opening (planned 45 min · simulated ~15 min of exchange)
- **Gate: PASS.** 4/4 on the classification check.
- **Misunderstanding:** said the difference between workflow (#3) and agent (#4) is "4 requires LLM judgement". Classic confusion: workflows contain LLMs too. Re-explained with "who decides the steps" + the flowchart test ("could you draw it before the customer writes?"). Will re-test at the build card (pattern choice).
- Injection check: answered correctly and tersely ("model can be tricked; rule 2, the code enforces it").
- **Explained twice:** workflow vs agent (once in the table, once after the wrong answer).
- **Course change:** the course pack's one-line quick check only asks for labels; all four labels can be right while the concept is wrong. Add the follow-up "what's the difference between #3 and #4?" to the official quick check. The four-row table should say explicitly that a workflow can contain a model ("Code fixes the steps; the model fills them" is right but too subtle for a first read).
- **Course change:** the five rules are meant to be "shown live", but in a 1-student or from-zero setting there is no agent yet at 09:15. Either pre-build the instructor demo agent (starter kit, run by the instructor) or explicitly move the live demos to after build v0 / guardrails. Here they were deferred.
- Terms introduced: model, tool, agent, prompt, trace, pass bar, prompt injection, gate, API key, environment variable.
