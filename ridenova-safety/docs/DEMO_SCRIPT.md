# Demo script (about 8 minutes)

Setup: `rm -rf data/runtime && npm start`, then open http://localhost:8080/console.html. The same flows run automatically in `npm run test:e2e`.

## e) Overview and SLA reconciliation (start here, 1 min)
1. Sign in as **Jordan Lee (duty manager)** → **Overview**.
2. Point out the filtered population (5,000), *new tickets* versus *open backlog* (different denominators), 138 unacknowledged critical alerts and 432 provisional cases (mostly languages the simulated provider does not understand).
3. Switch **Severity basis** between *Current operational*, *AI-proposed* and *Human-reviewed*. The chart changes, but every bar set still sums to the population.
4. Filter **Region = LatAm**. All cards and tables recompute to the new population.
5. Explain the SLA table. Tier means the highest tier the case has held. The replay clock is 8 March, 08:00 UTC, and the data contains no real responses, so this is **not** historical performance.

## a) Upstream automation and an exception (1.5 min)
1. Under *Automation and exceptions*: 2,456 cases are **shadow-eligible**, but nothing is automated yet. Another 771 L1 cases are supported only by the reporter’s words, so the second key keeps them with a human (one-click confirm) unless a live model agrees.
2. Click **Enable SP-1 automation (demo)** and confirm. About 2,342 are completed by the **simulated** adapter and about 114 fail by design and are *sent to review*. None of them entered an agent queue first.
3. Sign in as **Alex Moreau (agent, EMEA)**. Open a case flagged **Automation exception**: the failed execution is visible, and the case is in human review, not resolved.

## b) Agent investigation (2 min)
1. As Alex, choose **My queues** and open an L2 case (for example a cleaning-fee claim).
2. Walk through the five questions:
   - The **summary** is AI interpretation; the report is an *allegation*. Click **Translate** on a non-English case: the label shows fixture, live, or unavailable.
   - **Evidence** lists each source with its status.
   - **Policy** shows the conditions behind each clause.
   - **Uncertain or missing** shows confidence (uncalibrated) separately from evidence completeness.
3. **Take case**, then **Approve**. Note the separate *Decision* line and *Execution · completed (simulated)* line. The case resolves only after execution is confirmed.
4. Open the identity source: personal data is masked. **Reveal** asks for a reason, which is logged.
5. Try `#work/SC-0002` (a manager-lane case). The server refuses it.

## c) Urgent manager escalation (1.5 min)
1. As **Jordan Lee**, open the top unacknowledged case (SC-0001: driver's GPS near the rider's home after the trip).
2. Show **why this is here**: the structured telematics signal. The alert was created at receipt, before AI preparation (see History).
3. **Acknowledge and own.** The status becomes *Under review*. First response is still "None yet": acknowledgement is not a response.
4. Record **Contact the reporter: reached**, **Emergency services: not needed** (recorded by the manager; the system notifies no one) and **Protect: block re-matching** (sent to Account enforcement, a mock adapter). The danger banner shows the on-call page sent to the duty-manager rotation, and the header shows the support-ticket reference.
5. Step 4 is now **Close the case…**: choose the danger status (for example *no longer present*), the outcome (*reporter confirmed safe*) and a reason. Closing is refused until the reporter has been contacted. To keep SC-0001 for part d, close a different L4 case, such as the next one in the list.

## d) Justified manager downgrade (1.5 min)
1. Open **Not a danger case after all? → Reassess severity**.
2. Try a short reason: it is rejected. Then complete the form: L2, *incorrectly detected*, evidence = Telematics, policy SP-7, destination General review, and a real reason.
3. Result: current severity L2, reviewed L2, and AI-proposed **still L4**. Alerts and acknowledgement are kept, and the **deadline and breach are unchanged** (`max_held` stays L4). The case is handed off (pending) to a human queue: not resolved, not automated.
4. Optional: **Demo: inject a new SOS signal**. A *fresh* alert is created and the case returns to the duty-manager lane, despite the earlier downgrade.
