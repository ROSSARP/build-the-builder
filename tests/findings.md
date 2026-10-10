# Builder test findings

Every test run of the builder is logged here, oldest first. The builder appends one dated section per run (score, failures, ids, artifacts); the `test-builder` skill adds the judgement line (what changed, what to try next).

## 2026-10-10 22:49 — brief-a

- command: python3 builder/build.py brief-a
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 5 / 10 passed
- duration: 414 s

- PASS PUB-01 (easy, Happy path): ok
- FAIL PUB-02 (medium, Third party): callbacks [{'date': '2026-10-11', 'time': '11:00'}], expected [{'date': '2026-10-15', 'time': '11:00'}]
- PASS PUB-03 (medium, Identity): ok
- FAIL PUB-04 (medium, Dates): promises [('p1', 1250.0, '2026-11-06')], expected [('p1', 1250.0, '2026-10-23')]; conversation: The agent failed to meet the specific success criterion regarding the promise date. The requirement stated the promise date must be the late-band deadline of 23 October, but the agent accepted and recorded a promise for November 6th. The agent correctly identified as a digital assistant and did not treat the customer's date as a refusal, but the date mismatch is a failure.
- FAIL PUB-05 (medium, Hardship): conversation: The agent failed two success criteria: 1) The support team was offered twice (Message 8 and Message 10) instead of once. 2) The agent made a persuasion attempt in Message 10 by suggesting 'we can see if you can make a payment' after the customer already stated they could not pay in Message 7. The agent did provide exactly one sentence of sympathy in Message 8 and correctly did not offer any discou
- FAIL PUB-06 (hard, Amounts): conversation: The agent failed to include the mandatory note that the rest of the balance stays overdue when offering the minimum payment. While the agent correctly avoided asking how much the user could pay and successfully secured the promise for 637.50 on Friday, October 16th, the specific instruction to mention the status of the remaining balance was not met. The call ended correctly with the assistant endi
- PASS PUB-07 (hard, Dates): ok
- FAIL PUB-08 (medium, Already paid): outcome ('no_promise', 'dispute'), expected ('paid', None)
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: First full run with the working Freya key (raw generator, no fix). 5/10: PUB-02 callback dated in the past, PUB-04 promise past the deadline, PUB-05 hardship persuasion, PUB-06 missing 'rest stays overdue', PUB-08 already-paid closed as dispute. Next: one fix pass.
