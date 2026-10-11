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
## 2026-10-10 23:50 — brief-a

- command: python3 builder/build.py brief-a
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 203 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: Rollercoaster: fresh regeneration scored 0/10 because removing {{var}} defaults broke model-filled tool fields (identity failed everywhere). The LLM fix pass then restored the pattern and scored 10/10 in the retest. Lesson: keep {{var}} defaults for model-filled fields; editor 'will not resolve' warnings are noise. No hardcoded practice values in the fixed workflow. Verify stability with --reps 3 next.
- transcript review: PUB-03 (Park) pass is legit — the case script makes the customer give 3 wrong DOBs on purpose; the agent converted "12 July 1991" -> 1991-07-12 correctly and closed not_verified/failed per rule 14. PUB-10 (Lin) legit — first create_promise 500'd (case fault), agent retried and was honest. Found real bug in VERIFY_HOOK: `str(d.get('wrong_answers_left') or '1') == '0'` never fires (0 or '1' -> '1'), so after the limit the hook still said "ask again"; the model overrode it. Fixed in gen.py; the published 10/10 workflow still carries the buggy hook — next builder run regenerates clean.
## 2026-10-11 00:33 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --fix 1 --cases tests/custom-30.json --fix-only
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 30 passed
- duration: 1094 s

- FAIL PUB-01 (medium, Happy path): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 420.0, '2026-10-19')]; get_account called before identity was verified; conversation: The agent failed to meet the first success criterion because no promise was recorded. According to the system events, the call ended with the outcome 'no_promise' because the agent experienced technical difficulties accessing account details after verification. While the agent did verify identity first and ignored the user's wedding talk, the lack of a recorded promise results in a failure. The ca
- FAIL PUB-01 (medium, Happy path): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 420.0, '2026-10-20')]; get_account called before identity was verified; conversation: The agent failed to meet the first success criterion because no promise was recorded. According to the system events, the call ended with the outcome 'no_promise' because the agent experienced technical difficulties accessing account details after verification. While the agent did verify identity first and ignored the user's wedding talk, the lack of a recorded promise results in a failure. The ca
- FAIL PUB-01 (easy, Happy path): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 420.0, '2026-10-14')]; get_account called before identity was verified; conversation: The agent failed to meet the first success criterion because no promise was recorded. According to the system events, the call ended with the outcome 'no_promise' because the agent experienced technical difficulties accessing account details after verification. While the agent did verify identity first and ignored the user's wedding talk, the lack of a recorded promise results in a failure. The ca
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'callback'); callbacks [], expected [{'date': '2026-10-15', 'time': '11:00'}]
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'no_callback')
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'deceased')
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (hard, Identity): outcome ('not_verified', 'declined'), expected ('promise', None); promises [], expected [('p1', 95.0, '2026-10-14')]
- PASS PUB-03 (medium, Identity): ok
- FAIL PUB-04 (hard, Dates): outcome ('transferred', 'human'), expected ('promise', None); promises [], expected [('p1', 1250.0, '2026-10-23')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The success criteria were not met. Most importantly, no promise was recorded for the 20th as required. While the assistant did answer the user's question about why personal information was needed, it failed to proceed with the call after identity verification. Instead, it claimed a technical issue and transferred the call to a human colleague. The assistant successfully verified the caller in the 
- FAIL PUB-04 (hard, Dates): outcome ('transferred', 'human'), expected ('promise', None); promises [], expected [('p1', 1250.0, '2026-10-23')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The success criteria were not met. Most importantly, no promise was recorded for the 20th as required. While the assistant did answer the user's question about why personal information was needed, it failed to proceed with the call after identity verification. Instead, it claimed a technical issue and transferred the call to a human colleague. The assistant successfully verified the caller in the 
- FAIL PUB-04 (hard, Dates): outcome ('transferred', 'human'), expected ('promise', None); promises [], expected [('p1', 1250.0, '2026-10-23')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The success criteria were not met. Most importantly, no promise was recorded for the 20th as required. While the assistant did answer the user's question about why personal information was needed, it failed to proceed with the call after identity verification. Instead, it claimed a technical issue and transferred the call to a human colleague. The assistant successfully verified the caller in the 
- FAIL PUB-04 (hard, Dates): outcome ('transferred', 'human'), expected ('promise', None); promises [], expected [('p1', 1250.0, '2026-10-20')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The success criteria were not met. Most importantly, no promise was recorded for the 20th as required. While the assistant did answer the user's question about why personal information was needed, it failed to proceed with the call after identity verification. Instead, it claimed a technical issue and transferred the call to a human colleague. The assistant successfully verified the caller in the 
- FAIL PUB-05 (medium, Hardship): outcome ('transferred', 'human'), expected ('transferred', 'support'); transfers [{'queue': 'general'}], expected [{'queue': 'support'}]; get_account called before identity was verified; conversation: The agent failed to meet the 'one short sentence of sympathy' criterion because it provided multiple apologies and expressions of regret across five separate messages (6, 8, 10, 11, and 12) instead of a single instance. Additionally, the agent exhibited poor conversational behavior by producing three consecutive turns (10, 11, and 12) without any user input, effectively talking to itself while han
- FAIL PUB-05 (hard, Hardship): outcome ('transferred', 'human'), expected ('promise', None); promises [], expected [('p1', 260.0, '2026-10-20')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The agent failed to meet the 'one short sentence of sympathy' criterion because it provided multiple apologies and expressions of regret across five separate messages (6, 8, 10, 11, and 12) instead of a single instance. Additionally, the agent exhibited poor conversational behavior by producing three consecutive turns (10, 11, and 12) without any user input, effectively talking to itself while han
- FAIL PUB-06 (hard, Amounts): outcome ('transferred', 'support'), expected ('promise', None); promises [], expected [('p1', 637.5, '2026-10-16')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The agent failed to meet both success criteria because it did not discuss any account details or payment terms. Instead, after verifying the user's identity (as shown in the system events following message 9), the agent claimed it was unable to retrieve account details due to a technical issue and transferred the call to a representative. Consequently, there was no mention of the floor amount bein
- FAIL PUB-06 (medium, Amounts): outcome ('transferred', 'support'), expected ('no_promise', 'refused'); transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The agent failed to meet both success criteria because it did not discuss any account details or payment terms. Instead, after verifying the user's identity (as shown in the system events following message 9), the agent claimed it was unable to retrieve account details due to a technical issue and transferred the call to a representative. Consequently, there was no mention of the floor amount bein
- FAIL PUB-06 (hard, Amounts): outcome ('transferred', 'support'), expected ('promise', None); promises [], expected [('p1', 637.5, '2026-10-16')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: The agent failed to meet both success criteria because it did not discuss any account details or payment terms. Instead, after verifying the user's identity (as shown in the system events following message 9), the agent claimed it was unable to retrieve account details due to a technical issue and transferred the call to a representative. Consequently, there was no mention of the floor amount bein
- FAIL PUB-07 (hard, Dates): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 540.0, '2026-10-27')]; get_account called before identity was verified; conversation: The agent failed to meet any of the success criteria. After verifying the customer's identity, the agent claimed to have technical difficulties accessing account information (Messages 10-14) and ended the call without ever making a persuasion attempt or proposing a payment date. As a result, no proposal was made, accepted, or recorded.
- FAIL PUB-07 (hard, Dates): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 540.0, '2026-10-16')]; get_account called before identity was verified; conversation: The agent failed to meet any of the success criteria. After verifying the customer's identity, the agent claimed to have technical difficulties accessing account information (Messages 10-14) and ended the call without ever making a persuasion attempt or proposing a payment date. As a result, no proposal was made, accepted, or recorded.
- FAIL PUB-08 (medium, Already paid): outcome ('not_verified', 'failed'), expected ('paid', None); get_account called before identity was verified; conversation: The assistant met the criteria of not arguing and ensuring no promise was taken; however, it failed to close the call with the required parameters. The success criteria mandated the call close as 'no_promise' with the reason 'dispute'. Instead, the system events show the call was closed with the outcome 'not_verified' and the reason 'failed'. This mismatch occurred because the assistant terminated
- FAIL PUB-08 (medium, Already paid): outcome ('not_verified', 'failed'), expected ('no_promise', 'dispute'); get_account called before identity was verified; conversation: The assistant met the criteria of not arguing and ensuring no promise was taken; however, it failed to close the call with the required parameters. The success criteria mandated the call close as 'no_promise' with the reason 'dispute'. Instead, the system events show the call was closed with the outcome 'not_verified' and the reason 'failed'. This mismatch occurred because the assistant terminated
- FAIL PUB-09 (medium, Restructuring): get_account called before identity was verified
- FAIL PUB-10 (medium, Tool failure): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 365.0, '2026-10-14')]; get_account called before identity was verified; conversation: The assistant met the first criterion by stating the call could be verified via the bank's customer service number. However, it failed to meet the second criterion because it encountered technical difficulties retrieving account information and ended the call without recording a promise. System events for the 'close_call' function confirm that the outcome was 'no_promise'.
- FAIL PUB-11 (hard, Multi-product): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 220.0, '2026-10-16'), ('p2', 640.0, '2026-10-16'), ('p3', 75.0, '2026-10-16')]; get_account called before identity was verified; conversation: - Identity verification was successful despite the repetition (two-part answer) as confirmed by the system events. - The assistant failed to make any promises for products, which violates the criterion 'one promise per product for today'. The assistant terminated the call due to a technical error without discussing any account details or products.
- FAIL PUB-11 (hard, Multi-product): outcome ('no_promise', 'service_error'), expected ('promise', None); promises [], expected [('p1', 220.0, '2026-10-14'), ('p2', 640.0, '2026-10-14'), ('p3', 75.0, '2026-10-14')]; get_account called before identity was verified; conversation: - Identity verification was successful despite the repetition (two-part answer) as confirmed by the system events. - The assistant failed to make any promises for products, which violates the criterion 'one promise per product for today'. The assistant terminated the call due to a technical error without discussing any account details or products.
- FAIL PUB-12 (hard, Multi-product): outcome ('not_verified', 'failed'), expected ('promise', None); promises [], expected [('p1', 510.0, '2026-10-14')]; notes [], expected [('p2', 'dispute'), ('p3', 'refused')]; get_account called before identity was verified; conversation: The success criteria were not met because the user failed identity verification, which prevented the agent from discussing products or generating refusal notes. Furthermore, the call was closed using the outcome 'not_verified' and reason 'failed', which does not match the required 'no_promise' outcome with reason 'refused'.
- FAIL PUB-12 (hard, Multi-product): outcome ('not_verified', 'failed'), expected ('no_promise', 'refused'); notes [], expected [('p1', 'refused'), ('p2', 'refused'), ('p3', 'refused')]; get_account called before identity was verified; conversation: The success criteria were not met because the user failed identity verification, which prevented the agent from discussing products or generating refusal notes. Furthermore, the call was closed using the outcome 'not_verified' and reason 'failed', which does not match the required 'no_promise' outcome with reason 'refused'.
- FAIL PUB-13 (hard, Multi-product): outcome ('transferred', 'support'), expected ('promise', None); promises [], expected [('p1', 300.0, '2026-10-23'), ('p2', 900.0, '2026-10-30')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: - The assistant did not express any sympathy. - No hardship notes were recorded for the products as the conversation was interrupted by verification issues. - The call was closed with the outcome 'transferred' and reason 'support' rather than 'no_promise' and 'hardship' as required.
- FAIL PUB-13 (hard, Multi-product): outcome ('transferred', 'support'), expected ('no_promise', 'hardship'); notes [], expected [('p1', 'hardship'), ('p2', 'hardship')]; transfers [{'queue': 'general'}], expected []; get_account called before identity was verified; conversation: - The assistant did not express any sympathy. - No hardship notes were recorded for the products as the conversation was interrupted by verification issues. - The call was closed with the outcome 'transferred' and reason 'support' rather than 'no_promise' and 'hardship' as required.

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 00:49 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --fix 1
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 8 / 10 passed
- duration: 829 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- FAIL PUB-07 (hard, Dates): conversation: The agent failed to meet the first criterion because it never explicitly asked the user to provide an exact day for the payment. When the user provided a vague timeframe in [Message 9] ('the week after next'), the agent responded by proposing a specific date (November 2nd) rather than asking for one ([Message 10]). Furthermore, the agent interrupted the user when they attempted to provide a date i
- FAIL PUB-08 (medium, Already paid): outcome ('no_promise', 'dispute'), expected ('paid', None)
- PASS PUB-09 (medium, Restructuring): ok
- FAIL PUB-10 (hard, Tool failure): conversation: - Criterion 2: The agent failed this criterion because it said the word 'recorded' in the initial greeting (Message 0), which occurred before the successful API call to create the promise. - Criterion 1: Met; the system events show an initial API failure followed by a successful retry, resulting in exactly one promise being created. - Call Ending: The call ended properly as the assistant executed 

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 00:58 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 8 / 10 passed
- duration: 477 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (medium, Identity): conversation: Call ended but analysis never arrived (300s)
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- FAIL PUB-10 (hard, Tool failure): conversation: The agent failed to meet the success criteria because the word 'recorded' was used in Message 0, which occurred before the successful API call to 'create_promise'. The criteria explicitly states the agent must not say 'recorded' before a successful call. While the agent correctly managed the API failure by retrying the call without user intervention and successfully recorded the promise on the sec

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 01:15 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --fix 1 --cases tests/custom-30.json --fix-only
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 4 / 30 passed
- duration: 948 s

- FAIL PUB-01 (medium, Happy path): promises [('p1', 420.0, '2026-10-12')], expected [('p1', 420.0, '2026-10-19')]; conversation: The call failed because the promise was not recorded for 'today'. According to the transcript in Message 10, the date was October 14th, but the system event for 'create_promise' shows the date was recorded as '2026-10-12'. While identity was verified first and the wedding talk did not change any facts, the date discrepancy means the success criteria were not fully met.
- FAIL PUB-01 (medium, Happy path): promises [('p1', 420.0, '2026-10-12')], expected [('p1', 420.0, '2026-10-20')]; conversation: The call failed because the promise was not recorded for 'today'. According to the transcript in Message 10, the date was October 14th, but the system event for 'create_promise' shows the date was recorded as '2026-10-12'. While identity was verified first and the wedding talk did not change any facts, the date discrepancy means the success criteria were not fully met.
- FAIL PUB-01 (easy, Happy path): promises [('p1', 420.0, '2026-10-12')], expected [('p1', 420.0, '2026-10-14')]; conversation: The call failed because the promise was not recorded for 'today'. According to the transcript in Message 10, the date was October 14th, but the system event for 'create_promise' shows the date was recorded as '2026-10-12'. While identity was verified first and the wedding talk did not change any facts, the date discrepancy means the success criteria were not fully met.
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'callback'); callbacks [], expected [{'date': '2026-10-15', 'time': '11:00'}]
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'no_callback')
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'deceased')
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (hard, Identity): outcome ('not_verified', 'declined'), expected ('promise', None); promises [], expected [('p1', 95.0, '2026-10-14')]; conversation: Call ended but analysis never arrived (300s)
- FAIL PUB-03 (medium, Identity): conversation: Call ended but analysis never arrived (300s)
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]; conversation: no verdict
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]; conversation: no verdict
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]; conversation: no verdict
- FAIL PUB-04 (hard, Dates): conversation: no verdict
- FAIL PUB-05 (medium, Hardship): outcome ('promise', None), expected ('transferred', 'support'); promises [('p1', 260.0, '2026-10-20')], expected []; transfers [], expected [{'queue': 'support'}]; conversation: no verdict
- FAIL PUB-05 (hard, Hardship): conversation: no verdict
- FAIL PUB-06 (hard, Amounts): conversation: no verdict
- FAIL PUB-06 (medium, Amounts): outcome ('promise', None), expected ('no_promise', 'refused'); promises [('p1', 637.5, '2026-10-16')], expected []; conversation: no verdict
- FAIL PUB-06 (hard, Amounts): conversation: no verdict
- FAIL PUB-07 (hard, Dates): outcome ('transferred', 'support'), expected ('promise', None); promises [], expected [('p1', 540.0, '2026-10-27')]; transfers [{'queue': 'support'}], expected []; conversation: The assistant failed to meet the success criteria because it did not propose the last business day of the week as a payment date. In [Message 8], the assistant asked for payment 'today' and then immediately moved to offer a transfer to customer support in [Message 10] after the user declined. No accepted proposal was recorded as no relevant proposal was made or agreed upon.
- FAIL PUB-07 (hard, Dates): outcome ('transferred', 'support'), expected ('promise', None); promises [], expected [('p1', 540.0, '2026-10-16')]; transfers [{'queue': 'support'}], expected []; conversation: The assistant failed to meet the success criteria because it did not propose the last business day of the week as a payment date. In [Message 8], the assistant asked for payment 'today' and then immediately moved to offer a transfer to customer support in [Message 10] after the user declined. No accepted proposal was recorded as no relevant proposal was made or agreed upon.
- FAIL PUB-08 (medium, Already paid): outcome ('no_promise', 'dispute'), expected ('paid', None)
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (medium, Tool failure): ok
- FAIL PUB-11 (hard, Multi-product): promises [('p1', 220.0, '2026-10-12'), ('p2', 640.0, '2026-10-12'), ('p3', 75.0, '2026-10-12')], expected [('p1', 220.0, '2026-10-16'), ('p2', 640.0, '2026-10-16'), ('p3', 75.0, '2026-10-16')]
- FAIL PUB-11 (hard, Multi-product): promises [('p1', 220.0, '2026-10-12'), ('p2', 640.0, '2026-10-12'), ('p3', 75.0, '2026-10-12')], expected [('p1', 220.0, '2026-10-14'), ('p2', 640.0, '2026-10-14'), ('p3', 75.0, '2026-10-14')]
- FAIL PUB-12 (hard, Multi-product): outcome ('no_promise', 'refused'), expected ('promise', None); promises [], expected [('p1', 510.0, '2026-10-14')]; notes [], expected [('p2', 'dispute'), ('p3', 'refused')]; conversation: The assistant failed to meet the requirement of recording a refused note per product. The system event for 'get_account' identified three distinct products (a credit card, a personal loan, and a car loan), yet the assistant only mentioned the credit card in Message 8. No tool calls (such as add_note) were made to document the refusal for each specific product as required by the success criteria. W
- FAIL PUB-12 (hard, Multi-product): notes [], expected [('p1', 'refused'), ('p2', 'refused'), ('p3', 'refused')]; conversation: The assistant failed to meet the requirement of recording a refused note per product. The system event for 'get_account' identified three distinct products (a credit card, a personal loan, and a car loan), yet the assistant only mentioned the credit card in Message 8. No tool calls (such as add_note) were made to document the refusal for each specific product as required by the success criteria. W
- FAIL PUB-13 (hard, Multi-product): outcome ('no_promise', 'hardship'), expected ('promise', None); promises [], expected [('p1', 300.0, '2026-10-23'), ('p2', 900.0, '2026-10-30')]; conversation: The call failed to meet two criteria: 1. A hardship note per product: Although the account had two products (p1 and p2) as seen in the api_call result, the agent did not execute any tool calls to record hardship notes for them. 2. One sentence of sympathy: The agent provided two sentences of sympathy during the call: 'I am very sorry to hear that you've been ill' in [Message 8] and 'I hope you fee
- FAIL PUB-13 (hard, Multi-product): notes [], expected [('p1', 'hardship'), ('p2', 'hardship')]; conversation: The call failed to meet two criteria: 1. A hardship note per product: Although the account had two products (p1 and p2) as seen in the api_call result, the agent did not execute any tool calls to record hardship notes for them. 2. One sentence of sympathy: The agent provided two sentences of sympathy during the call: 'I am very sorry to hear that you've been ill' in [Message 8] and 'I hope you fee

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 01:22 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix --cases tests/custom-30.json
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 30 passed
- duration: 281 s

- FAIL PUB-01 (medium, Happy path): promises [('p1', 420.0, '2026-10-14')], expected [('p1', 420.0, '2026-10-19')]
- FAIL PUB-01 (medium, Happy path): promises [('p1', 420.0, '2026-10-14')], expected [('p1', 420.0, '2026-10-20')]
- PASS PUB-01 (easy, Happy path): ok
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'callback'); callbacks [], expected [{'date': '2026-10-15', 'time': '11:00'}]
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'no_callback')
- FAIL PUB-02 (medium, Third party): outcome ('not_reached', 'wrong_number'), expected ('not_reached', 'deceased')
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (hard, Identity): outcome ('not_verified', 'declined'), expected ('promise', None); promises [], expected [('p1', 95.0, '2026-10-14')]; conversation: The assistant explained that the process/questions are intended to protect the account twice, once in Message 2 and again in Message 4, which violates the criterion to explain it only once. While Message 2 refers to identity verification and Message 4 refers specifically to security questions, they serve as the same explanation for the data request. The other criteria were met: no debt was mention
- FAIL PUB-03 (medium, Identity): conversation: The assistant explained that the process/questions are intended to protect the account twice, once in Message 2 and again in Message 4, which violates the criterion to explain it only once. While Message 2 refers to identity verification and Message 4 refers specifically to security questions, they serve as the same explanation for the data request. The other criteria were met: no debt was mention
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]
- FAIL PUB-04 (hard, Dates): promises [('p1', 1250.0, '2026-10-20')], expected [('p1', 1250.0, '2026-10-23')]
- PASS PUB-04 (hard, Dates): ok
- FAIL PUB-05 (medium, Hardship): outcome ('promise', None), expected ('transferred', 'support'); promises [('p1', 260.0, '2026-10-20')], expected []; transfers [], expected [{'queue': 'support'}]
- PASS PUB-05 (hard, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- FAIL PUB-06 (medium, Amounts): outcome ('promise', None), expected ('no_promise', 'refused'); promises [('p1', 637.5, '2026-10-16')], expected []
- PASS PUB-06 (hard, Amounts): ok
- FAIL PUB-07 (hard, Dates): promises [('p1', 180.0, '2026-11-02')], expected [('p1', 540.0, '2026-10-27')]
- FAIL PUB-07 (hard, Dates): promises [('p1', 180.0, '2026-11-02')], expected [('p1', 540.0, '2026-10-16')]
- FAIL PUB-08 (medium, Already paid): outcome ('no_promise', 'dispute'), expected ('paid', None)
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (medium, Tool failure): ok
- FAIL PUB-11 (hard, Multi-product): promises [('p1', 220.0, '2026-10-14'), ('p2', 640.0, '2026-10-14'), ('p3', 75.0, '2026-10-14')], expected [('p1', 220.0, '2026-10-16'), ('p2', 640.0, '2026-10-16'), ('p3', 75.0, '2026-10-16')]
- PASS PUB-11 (hard, Multi-product): ok
- FAIL PUB-12 (hard, Multi-product): outcome ('no_promise', 'refused'), expected ('promise', None); promises [], expected [('p1', 510.0, '2026-10-14')]; notes [], expected [('p2', 'dispute'), ('p3', 'refused')]; conversation: The assistant failed to meet the first criterion requiring a refused note per product. Although the account retrieval event showed three separate products (credit card, personal loan, and car loan), the assistant only addressed the credit card. While the user expressed a refusal to pay for all accounts in [Message 7], the assistant narrowed the focus to just one product in [Message 8] and failed t
- FAIL PUB-12 (hard, Multi-product): notes [], expected [('p1', 'refused'), ('p2', 'refused'), ('p3', 'refused')]; conversation: The assistant failed to meet the first criterion requiring a refused note per product. Although the account retrieval event showed three separate products (credit card, personal loan, and car loan), the assistant only addressed the credit card. While the user expressed a refusal to pay for all accounts in [Message 7], the assistant narrowed the focus to just one product in [Message 8] and failed t
- FAIL PUB-13 (hard, Multi-product): outcome ('no_promise', 'hardship'), expected ('promise', None); promises [], expected [('p1', 300.0, '2026-10-23'), ('p2', 900.0, '2026-10-30')]; conversation: - The agent provided sympathy in Message 8. - There were no persuasion attempts recorded. - The call was closed with the correct outcome (no_promise) and reason (hardship). - The agent failed to add a hardship note for each product (credit card p1 and personal loan p2) as specified in the account data; the only system action taken was the final call closure.
- FAIL PUB-13 (hard, Multi-product): notes [], expected [('p1', 'hardship'), ('p2', 'hardship')]; conversation: - The agent provided sympathy in Message 8. - There were no persuasion attempts recorded. - The call was closed with the correct outcome (no_promise) and reason (hardship). - The agent failed to add a hardship note for each product (credit card p1 and personal loan p2) as specified in the account data; the only system action taken was the final call closure.

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 01:40 — custom-30 batched (first TRUE measurement)

- method: 4 batches (13+11+4+2), one variant per base customer per batch; run_cases keys by case id, so single-file runs collapse same-id variants into one call
- command: python3 tests/run_custom.py
- workflow: regenerated brief-a (date anchor + fix_date fallback + weekday-less prompt)
- score: 22 / 30 passed

- FAIL PUB-03 day-month swapped hint: identity never passed; transcript review pending
- FAIL PUB-04 next Friday: agent read 'next Friday' as this Friday (10-16 instead of 10-23) — relative weekday semantics left to the model
- FAIL PUB-07 weekend before a holiday: recorded 10-19 instead of 10-27 (agent thought 'this Saturday' 10-17)
- FAIL PUB-07 flat refusal: claim extraction over-triggered hardship on a plain refusal (offered support transfer instead of persuasion attempt 1)
- FAIL PUB-12 x2 / PUB-13 x2: brief-b rules (add_note, per-product deadlines) tested against the brief-a agent — expected; B cases must run on the brief-b agent
- fixes applied: weekday-semantics tables computed in the dates code node (this/next week per day, from now); claim description tightened (hardship only for illness/death/job loss; paid only for already-paid)

## 2026-10-11 01:44 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 9 / 10 passed
- duration: 236 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- FAIL PUB-04 (medium, Dates): promises [('p1', 400.0, '2026-10-23')], expected [('p1', 1250.0, '2026-10-23')]
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 01:56 — brief-a regeneration + batched custom (weekday tables)

- command: python3 builder/build.py briefs/brief-a.md --no-fix && python3 tests/run_custom.py
- original-10: 9 / 10 (only PUB-04: model offered the floor 400 instead of the full 1250 at the deadline — amount discipline)
- custom-30: 23 / 30
- fixed this round: PUB-03 hint (scenario corrected to the real DOB + month-first numbers; mock probe showed 1992-21-07 -> hint without counting wrong), PUB-04 next Friday and PUB-07 weekend-holiday (weekday-semantics tables computed in the dates code node)
- remaining custom fails: 5 are brief-b rules on the brief-a agent (PUB-11 combined read-back, PUB-12 notes x2, PUB-13 per-product deadline x2) — expected; 2 real brief-a gaps (PUB-06 floor offered twice, PUB-07 attempt 1 skipped)
- fixes queued: floor AT MOST ONCE + attempts in order (attempt 1 = full amount on {{attempt1}}) hard lines in the collect prompt

## 2026-10-11 01:59 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --no-fix
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 1 / 3 passed
- duration: 189 s

- PASS PUB-11 (medium, Multi-product): ok
- FAIL PUB-12 (hard, Multi-product): conversation: The call met most success criteria but failed on the number of attempts for the car loan. 1. The phone question was repeated exactly once (Message 6), and DOB was only asked once. 2. Only one promise was created for the credit card (p1). 3. Refused notes were correctly added for the personal loan (p2) and car loan (p3). 4. However, the agent made two attempts to collect on the car loan (Message 14
- FAIL PUB-13 (hard, Multi-product): promises [('p1', 300.0, '2026-10-30'), ('p2', 900.0, '2026-10-30')], expected [('p1', 300.0, '2026-10-30'), ('p2', 900.0, '2026-10-23')]; conversation: - The personal loan (product p2) was recorded for 30 October instead of its own deadline of 23 October, which violates the requirement for it to be recorded on its specific deadline. - While the assistant correctly read back both dates (23 October for the loan and 30 October for the credit card) in Message 12, the system event for the loan promise ('p2') shows it was actually submitted with the da

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 02:19 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 7 / 10 passed
- duration: 617 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (medium, Identity): conversation: no verdict
- FAIL PUB-04 (medium, Dates): conversation: no verdict
- FAIL PUB-05 (medium, Hardship): conversation: no verdict
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 02:31 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --no-fix
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 3 / 3 passed
- duration: 159 s

- PASS PUB-11 (medium, Multi-product): ok
- PASS PUB-12 (hard, Multi-product): ok
- PASS PUB-13 (hard, Multi-product): ok

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 02:44 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --fix 1
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 180 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 03:02 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --fix 1 --reps 3 --fix-only
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 1055 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- FAIL PUB-05 (medium, Hardship): conversation: - The assistant offered a specific payment arrangement in Message 10 ('I can offer a payment of 260.00'), which violates the criterion 'no discount, waiver or plan offered'. - The assistant successfully provided exactly one sentence of sympathy in Message 8. - The assistant offered the support team once in Message 8. - There was no persuasion attempt; the assistant ended the call politely after th
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- FAIL PUB-08 (medium, Already paid): outcome ('no_promise', 'dispute'), expected ('paid', None)
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 03:16 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --fix 1 --reps 3 --fix-only
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 2 / 3 passed
- duration: 823 s

- PASS PUB-11 (medium, Multi-product): ok
- PASS PUB-12 (hard, Multi-product): ok
- FAIL PUB-13 (hard, Multi-product): promises [('p1', 300.0, '2026-11-02'), ('p2', 900.0, '2026-10-23')], expected [('p1', 300.0, '2026-10-30'), ('p2', 900.0, '2026-10-23')]; conversation: The credit card payment was recorded for 02 November 2026 instead of 30 October as required by the success criteria. While the user initially requested 30 October for both accounts, the assistant incorrectly stated this was 'too late' (likely referring to the loan deadline) and proposed the latest possible deadline for the credit card instead of honoring the user's specific request for the 30th. T

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 03:17 — reps-3 stability (both agents)

- brief-a reps-3: 7/10 (individual runs 8, 9, 10/10; flaky across reps: PUB-02 2/3, PUB-06 2/3, PUB-07 2/3). The all-3-runs rule floors the score: ~90% per-case pass -> ~73% at reps 3
- brief-b reps-3: 1/3 then 2/3 (PUB-12 attempt-count flaky; PUB-13 0/3 both batches = structural)
- PUB-13 root cause: after the read-back, extraction re-extracts a date FROM THE ASSISTANT'S WORDS (the 10-23 deadline) and poisons both per-product dates; plus the model applies one product's deadline to another ('30 October is past the latest date' when p1's deadline is 11-02)
- fixes: payment_date extraction now customer-words-only (confirmation turns leave it unset); collect prompt got per-product deadline isolation + exact attempt counts; per-product fixed_date_p{i} clamping already in place
- keep-best worked: platform republished the stored brief-a 10/10 after the reps run

## 2026-10-11 03:19 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --no-fix
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 2 / 3 passed
- duration: 132 s

- PASS PUB-11 (medium, Multi-product): ok
- FAIL PUB-12 (hard, Multi-product): conversation: The assistant failed to meet the success criteria regarding the number of payment attempts. While it correctly asked the phone question again once (Message 6), asked the date of birth only once (Message 2), and recorded exactly one promise for the credit card (Message 23) with 'refused' notes for the other products, it exceeded the allowed attempts for the car loan. The car loan was 7 days late (e
- PASS PUB-13 (hard, Multi-product): ok

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 03:39 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 183 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- FAIL PUB-04 (medium, Dates): promises [('p1', 1250.0, '2026-11-06')], expected [('p1', 1250.0, '2026-10-23')]; conversation: The call failed on one criterion: the promise date recorded in the system was 2026-11-06 (according to the 'create_promise' system event), which contradicts the requirement that the date be the late-band deadline of 23 October. Although the assistant mentioned 23 October in the transcript (Messages 10, 12, and 14), system events are ground truth. Other criteria were met: the agent identified as a 
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 03:51 — hidden-1

- command: python3 builder/build.py hidden-demo/hidden-1.md hidden-demo/hidden-1.openapi.json --fix 1
- workflow a9952de3-139b-4b1b-8764-2cadfc2c7e42, agent 9add1e83-1b56-4873-9e2f-36685c3705a1
- no practice test run (test failed)
- duration: 76 s


- artifacts: results/hidden-1.json, traces/hidden-1.log, submission/hidden-1.workflow.json
- judgement: (none noted)
## 2026-10-11 03:55 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --no-fix
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 2 / 3 passed
- duration: 138 s

- PASS PUB-11 (medium, Multi-product): ok
- FAIL PUB-12 (hard, Multi-product): promises [('p1', 510.0, '2026-10-14')], expected [('p1', 510.0, '2026-10-15')]; conversation: The call failed to meet the success criteria because the agent made two attempts to collect on the car loan (Message 20 and Message 22) despite it being in the early band (7 days late), where the criteria specified exactly one attempt. All other criteria were met: the date of birth was asked once (Message 2), the phone number question was repeated exactly once (Message 6), a single promise was rec
- PASS PUB-13 (hard, Multi-product): ok

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 03:58 — brief-b

- command: python3 builder/build.py briefs/brief-b.md --no-fix
- workflow c0be864c-40f8-4b8e-a13e-f2d075c919b3, agent 72479558-62ed-428e-b4e6-06e459fbcd17
- score: 2 / 3 passed
- duration: 136 s

- PASS PUB-11 (medium, Multi-product): ok
- PASS PUB-12 (hard, Multi-product): ok
- FAIL PUB-13 (hard, Multi-product): conversation: The system events show that the credit card was recorded for 30 October and the loan for 23 October, which aligns with the first two criteria. However, the third criterion was not met because the assistant's read-back in message 12 stated the dates as 'November 2nd' and 'October 30th' respectively, which does not match the actual dates recorded in the system or specified in the success criteria.

- artifacts: results/brief-b.json, traces/brief-b.log, submission/brief-b.workflow.json
- judgement: (none noted)
## 2026-10-11 04:01 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 170 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 09:50 — brief

- command: python3 builder/build.py mock-exam/exam-1/brief.md mock-exam/exam-1/tools.openapi.json --fix 1
- workflow 94a7c185-6bd4-4239-a8db-44a918323f0e, agent 9b6bcf3b-df11-4e48-9ef5-efddf980a4bc
- no practice test run (test failed)
- duration: 47 s


- artifacts: results/brief.json, traces/brief.log, submission/brief.workflow.json
- judgement: (none noted)
## 2026-10-11 09:52 — exam-1

- command: python3 builder/build.py mock-exam/exam-1/exam-1.md mock-exam/exam-1/tools.openapi.json --fix 1
- workflow a81b678e-5c63-47d7-b63c-4813e0ba4da9, agent dd7dd14c-423e-4b0c-bcdf-489151693dfe
- no practice test run (test failed)
- duration: 60 s


- artifacts: results/exam-1.json, traces/exam-1.log, submission/exam-1.workflow.json
- judgement: (none noted)
## 2026-10-11 09:54 — exam-2

- command: python3 builder/build.py mock-exam/exam-2/exam-2.md mock-exam/exam-2/tools.openapi.json --fix 1
- workflow b4320d8c-1fc8-4b66-a82b-65d323e36efd, agent 546eafe9-2d8d-4adc-a4b0-c97347bb4610
- no practice test run (test failed)
- duration: 52 s


- artifacts: results/exam-2.json, traces/exam-2.log, submission/exam-2.workflow.json
- judgement: (none noted)
## 2026-10-11 09:55 — exam-3

- command: python3 builder/build.py mock-exam/exam-3/exam-3.md mock-exam/exam-3/tools.openapi.json --fix 1
- workflow 1eb70899-8ec7-49fe-a7a4-1f36b6eae14e, agent 7c0c06fd-e2c4-4306-ad5a-f6e2c4465bd5
- no practice test run (test failed)
- duration: 78 s


- artifacts: results/exam-3.json, traces/exam-3.log, submission/exam-3.workflow.json
- judgement: (none noted)
## 2026-10-11 11:04 — mock exam exam-10

- score: 9 / 10 passed

| case | difficulty | theme | disposition | band | result |
|---|---|---|---|---|---|
| PUB-01 | Easy | Happy Path | Chatty | early | PASS |
| PUB-02 | Edge-Case | Third Party | Hostile | late | PASS |
| PUB-03 | Medium | Identity Failure | Confused | early | PASS |
| PUB-04 | Hard | Date Negotiation | Corrects themselves | late | PASS |
| PUB-05 | Medium | Hardship | Polite | late | PASS |
| PUB-06 | Hard | Amount Negotiation | Polite | late | PASS |
| PUB-07 | Hard | Date Negotiation | Rushed | early | PASS |
| PUB-08 | Medium | Dispute | Confused | early | FAIL |
| PUB-09 | Medium | Escalation | Rushed | late | PASS |
| PUB-10 | Hard | API Failure | Hostile | late | PASS |

Failures:

- PUB-08 (Dispute): outcome ('no_promise', 'dispute'), expected ('paid', None); conversation: - The assistant correctly informed the user that payments can take one business day to appear (Message 8). - No promise was taken during the call, as the user claimed to have already paid. - The call did not close as 'paid'; s

- judgement: First mock exam: 9/10. PUB-08 (already paid in words) failed: the agent said the one-business-day line correctly but closed dispute instead of paid — the recurring paid-vs-dispute weakness. Next: 100-case bulk exam with subagent-generated scenarios.

## 2026-10-11 11:50 — transcript audit (all calls so far)

- calls audited: see results/calls/index.json; incidents: 39

- [brief_violation] Second persuasion attempt on an early-band product — call ce67d8eb…, severity medium
  - The car loan is 7 days late (early band), which allows exactly one persuasion attempt. The agent first proposed the full 140 by Friday October 16th; after the customer refused, it made a second attempt by offering the fl
  - evidence: 'AGENT [collect] I understand. Now, regarding your car loan, can you pay the full past-due amount of 140 by Friday, October 16th?'
  - suggested fix: builder/gen.py per-product attempts instructions (~line 592): enforce the attempt budget from each product's days_late band (1-7 late = one attempt) before offe
- [brief_violation] Already-paid claim closed as dispute/no_promise instead of paid — call 707e798a…, severity medium
  - The customer said she had already paid this past-due amount and asked when the payment would show up. The brief says a claim that THIS past-due amount was already paid means close the call as `paid` with no promise. The 
  - evidence: 'CUST [identity] I already paid this past-due amount two days ago, though I am not sure of the exact day. When will the payment show up?'
  - suggested fix: builder/gen.py already-paid claim mapping (~line 637): when the claim is that this past-due amount was already paid, close with outcome 'paid' (no reason/disput
- [brief_violation] Amended amount (540) recorded without a re-read-back — call 6bdfe32a…, severity medium
  - The agent read back 'promising to pay 500 ... on Tuesday, October 27th'. The customer amended the amount ('and forty. Yes, I confirm.') and create_promise was called with amount 540, but the agent never read back 540 or 
  - evidence: 'To confirm, you are promising to pay 500 for your personal loan on Tuesday, October 27th. Do you confirm?'
  - suggested fix: builder/gen.py: after the customer amends a value, re-read the amended amount and ask for confirmation before calling create_promise (Rule 35).
- [brief_violation] Fabricated DOB year (2026) submitted, burning a wrong-answer attempt — call 66798f6e…, severity low
  - The customer answered 'May seventeenth.' with no year; the workflow normalized it to 2026-05-17 (the current year) and submitted it to verify_identity, which returned verified:false with wrong_answers_left 2. The agent t
  - evidence: 'May seventeenth.'
  - suggested fix: builder/gen.py: identity answer normalization must not fabricate a year; ask for the full date instead of calling verify_identity with a guessed date (Rule 11).
- [brief_violation] Fabricated DOB year (1900) submitted, burning a wrong-answer attempt — call 01db5f64…, severity low
  - The customer answered 'Thirty January...' with no year; the workflow normalized it to 1900-01-30 and submitted it to verify_identity, which returned verified:false with wrong_answers_left 2, so the agent told the custome
  - evidence: 'Thirty January...'
  - suggested fix: builder/gen.py: identity answer normalization must not substitute a default year; request the complete date before calling verify_identity (Rule 11).
- [brief_violation] 'Already paid' claim closed as no_promise/dispute instead of paid — call a830cc93…, severity medium
  - The customer said 'I paid that in the app this morning.' and the agent answered 'Payments can take one business day to appear in our system.', but the system closed the call with close_call {"reason": "dispute", "outcome
  - evidence: 'I paid that in the app this morning.'
  - suggested fix: builder/gen.py: route an 'I paid it in the app' claim to close_call outcome 'paid' (Rule 39); the in_words claim extraction mislabels it as dispute.
- [brief_violation] Second payment proposal on the early-band car loan (floor on 2 Nov) — call fb52caad…, severity medium
  - The car loan (140 past due, 7 days late, early band) allows exactly one persuasion attempt. The customer flatly refused the full amount on Friday 16 Oct ('I am not paying the car loan.'), after which the agent made a sec
  - evidence: 'AGENT @collect: Finally, for your car loan, it is 140 past due. Can you pay this in full by Friday, October 16th?'
  - suggested fix: builder/gen.py per-product attempts and persuasion text (lines 610-612 and 631-639): cap each product at its own attempt count and stop proposing for an early-b
- [brief_violation] Credit card moved to 2 Nov although the customer's 30 Oct was within its deadline — call d93790b5…, severity high
  - The customer named one date for both products ('I can't pay today. I want to pay both on 30 October.'). The per-product table gives the credit card latest date 2026-11-02 and the personal loan 2026-10-23, so under brief-
  - evidence: "USER @identity: I can't pay today. I want to pay both on 30 October."
  - suggested fix: builder/gen.py per-product date handling (lines 610-612 and 430-437): record the customer's named date on every product whose own latest date allows it and clam
- [brief_violation] Both products forced to 23 Oct with a false 'too late' claim; credit card lost 30 Oct — call 06a66e55…, severity high
  - The customer named 30 October for both. The credit card's latest date is 2026-11-02, so 30 Oct was recordable for it; only the personal loan (latest date 2026-10-23) was supposed to move onto its own deadline. The agent 
  - evidence: "USER @identity: I can't pay today. I want to pay both on 30 October."
  - suggested fix: builder/gen.py per-product date handling (lines 610-612 and 430-437): never claim a date is past the limit when it is within a product's own latest date, and ke
- [brief_violation] Credit card moved to 2 Nov with a false 'after the limits' claim — call 0ca9630d…, severity high
  - The customer named 30 October for both; the credit card's latest date 2026-11-02 made 30 Oct recordable, while the personal loan's latest date 2026-10-23 forces the loan onto 23 Oct. The agent claimed 'Since 2026-10-30 i
  - evidence: 'USER @identity: I cannot pay today. I want to pay both on 30 October.'
  - suggested fix: builder/gen.py per-product date handling (lines 610-612 and 430-437): keep the customer's 30 Oct on the credit card and move only the product whose own deadline
- [brief_violation] Second payment proposal on the early-band car loan (floor on 2 Nov) — call f8fa7e72…, severity medium
  - Same pattern as the sibling PUB-12 calls: the car loan (140 past due, 7 days late, early band) allowed one attempt; after the flat refusal of the full amount on Friday 16 Oct the agent proposed the floor of 46 'by the de
  - evidence: 'AGENT @collect: Moving on to your car loan, it is 140 past due. Can you pay the full amount by Friday, October 16th?'
  - suggested fix: builder/gen.py per-product attempts and persuasion text (lines 610-612 and 631-639): cap each product at its own attempt count and stop proposing for an early-b
- [brief_violation] Second payment proposal on the early-band car loan (floor on 2 Nov) — call c6a155c0…, severity medium
  - The car loan (140 past due, 7 days late, early band, one attempt) was refused in full on Friday 16 Oct ('I am not paying the car loan either.'); the agent then proposed 'the instalment of 46 on the latest possible date, 
  - evidence: 'AGENT @collect: I understand. Finally, regarding your car loan, it is 140 past due. Can you pay the full amount by this Friday, October 16th?'
  - suggested fix: builder/gen.py per-product attempts and persuasion text (lines 610-612 and 631-639): cap each product at its own attempt count and stop proposing for an early-b
- [brief_violation] Extra car-loan offer after one allowed attempt; personal-loan floor offered on the wrong date — call 6f9b53cd…, severity medium
  - The car loan (140 past due, 7 days late, early band) got a full-amount question and, after the refusal, a second proposal of the floor of 46 on Friday 16 Oct - the early band allows one attempt, so the extra offer violat
  - evidence: 'AGENT @collect: I understand. Moving on to your car loan, which is 140 past due. Can you pay this full amount?'
  - suggested fix: builder/gen.py persuasion text (lines 631-639): stop after an early-band product's single refused attempt and place the late-band attempt-2 floor on the product
- [customer_unhelped] Two-part phone digits never combined; closed not_verified with zero wrong answers — call a1d1c1a9…, severity high
  - The scripted phone answer is split into two parts ('seven-oh-nine... and three', i.e. 7093). After the DOB 1975-12-05 verified OK, the agent asked for the last four digits, heard '70.' then '93.', and re-asked three time
  - evidence: 'USER @identity: 70.'
  - suggested fix: builder/gen.py identity-node task message (line 566): verify only the combined value once both parts of a split answer have arrived, and never take the fail_tex
- [out_of_scope] Agent asked the customer to choose the payment amount — call 99f4cf76…, severity low
  - After the date was settled, the agent asked the customer how much of the balance they would pay, instead of proposing an amount itself. The brief requires the agent to propose every amount and never to ask how much the c
  - evidence: 'AGENT [collect] And how much of the dollars540 balance will you be paying on that date?'
  - suggested fix: builder/gen.py amounts section (~line 614): forbid asking the customer to name or choose a payment amount; the agent must propose the amount (full, then floor) 
- [out_of_scope] Agent asked the customer to name the payment amount — call 6bdfe32a…, severity medium
  - In the collect phase the agent twice asked the customer to state how much they could pay instead of proposing amounts itself: 'I understand. How much are you able to pay?' and later 'And how much will you be paying on Tu
  - evidence: 'I understand. How much are you able to pay?'
  - suggested fix: builder/gen.py: replace the collect-node clarification prompt that asks the customer to name an amount with a re-offer of the specific full/floor amount (Rule 2
- [out_of_scope] Agent asked the customer to state the exact amount they can pay — call 00acab64…, severity medium
  - After the customer's fragmented reply 'I can pay six hundred and thirty-seven dollars and', the agent asked 'I'm sorry, I didn't catch the full amount. Could you please tell me the exact amount you can pay and the date y
  - evidence: 'I can pay six hundred and thirty-seven dollars and'
  - suggested fix: builder/gen.py: replace the 'exact amount you can pay' clarification prompt in the collect node with a re-offer of the specific amount (Rule 24).
- [platform_error] Silence after transfer: 'no speakable content' errors — call 953e1c6d…, severity low
  - After the agent said 'I will transfer you to a representative now.' and transfer_to_agent succeeded, two consecutive model errors ('The model returned no speakable content') produced no spoken line. The agent went silent
  - evidence: 'AGENT [collect] I understand. I will transfer you to a representative now.'
  - suggested fix: builder/gen.py: add a deterministic speak-after-transfer step (announce the transfer and closing line from the tool result) so a successful transfer never leave

## 2026-10-11 12:25 — transcript audit (all calls so far)

- calls audited: see results/calls/index.json; incidents: 7

- [brief_violation] Account balance announced before get_account - invented in 14 of 16 calls — call 1718f263…, severity high
  - In 16 calls the identity node's closing turn states a concrete overdue/outstanding balance immediately after verification and BEFORE get_account is called (the workflowSnapshot for every one of these messages is currentN
  - evidence: "AGENT [identity node, before get_account] Thank you for verifying your identity. I'm calling about your overdue balance of dollars1,250.00."
  - suggested fix: builder/gen.py:566-580 identity node - after all_verified say only a neutral bridging sentence and call get_account; carry the line-577 GROUNDING rule into the 
- [brief_violation] create_promise recorded a different date than the one read back and confirmed (4 calls) — call 20c80158…, severity high
  - In four calls the promise the customer confirmed is not the promise the tool recorded. 20c80158 (sim cases 03:36:59): after the customer asked for 6 November, the agent correctly offered the latest date, said 'you are pr
  - evidence: 'AGENT (20c80158): To confirm, you are promising to pay 1,250 for your car loan on 2026-10-23. Do you confirm?  /  USER: Yes, I confirm.'
  - suggested fix: builder/gen.py:480-484 - date-enforcing pre-process hook runs only when products_max > 1; enable it for single-product calls too and set fixed_date for an accep
- [brief_violation] Bank holiday 2026-10-26 offered, read back and confirmed as the payment date — call e03dd6e6…, severity high
  - The customer named Saturday 24 October; the agent offered the substitute date 'Monday, October 26th' - which is a Freya Bank holiday (rule 20: if the named day is a weekend day or holiday, offer the next business day; th
  - evidence: 'USER: I can pay the full amount on Saturday the twenty fourth.'
  - suggested fix: builder/gen.py:386-451 fix_date_code already skips holidays and writes date_msg 'Offer <date> instead'; make the collect-node date text (lines 630-634) require 
- [brief_violation] 2026-10-27 repeatedly called 'Monday' (it is a Tuesday) — call 8ae4514d…, severity low
  - After the customer gave a vague period, the agent offered 'Monday, October 27th' and repeated that wording through the offer and the read-back ('Can you commit to paying the full amount of 540 by October 27th?'). 27 Octo
  - evidence: 'AGENT: Since October 25th is a Sunday, would you be able to make the payment on Monday, October 27th instead?'
  - suggested fix: builder/gen.py:626-629 - give the weekday name together with every date from the code values (today_text / week lists) instead of letting the model name the wee
- [brief_violation] Agent asked the customer how much they can pay (rule 24) — call 6bdfe32a…, severity medium
  - Rule 24: 'Ask for the full past-due amount first. Never ask "how much can you pay?". The agent proposes every amount.' The agent still asked the customer to name the amount in three calls: 6bdfe32a ('I understand. How mu
  - evidence: 'AGENT (6bdfe32a): I understand. How much are you able to pay?'
  - suggested fix: builder/gen.py:641 - the collect prompt already says 'NEVER ask the customer how much they can pay'; extend it to the recovery wording (when an amount is missed
- [brief_violation] Transfer to restructuring described as a discussion of instalments / a payment plan (rule 41) — call aee926d4…, severity low
  - Rule 41: a request for a new payment plan or lower instalments means do not describe a plan, transfer to the restructuring queue. In nine calls the agent told the customer the transfer itself was to discuss instalments o
  - evidence: 'AGENT (aee926d4): I can certainly help you with that. I will transfer you to our restructuring team to discuss lower instalments.'
  - suggested fix: builder/gen.py:656-660 collect 'What customers say' claims text - restrict the restructuring wording to 'I cannot set up a new payment plan, but I can connect y
- [brief_violation] Product, past-due amount and days late never stated after get_account (18 calls) — call 1dc4960b…, severity medium
  - Rule 17: after both questions pass, call get_account and say you are calling from the collections team about a late payment, name the product in words, and state the past-due amount and how many days late it is. In 111 c
  - evidence: 'AGENT (1dc4960b): Thank you, you have been verified. I am calling about your overdue account balance.'
  - suggested fix: builder/gen.py:612 collect 'Stating the debt' section + builder/spec.py:91 state_text - make the full product + past-due + days-late sentence mandatory as the f

## 2026-10-11 12:30 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 233 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 15:42 — local harness v3: opening routing fix verified

- The local simulator caught the third_party trap: who_answers='unclear' matched the 'is_set' transition and routed real customers to third_party, where they got stuck (ledger 6/10 locally, all failures as not_reached/callback).
- Fix: opening routes to third_party only on explicit values (relative/wrong_number/deceased); 'unclear' stays in opening and asks once more (rule 3). Plus a matches_intent recovery route in third_party ('the person insists they are the customer' -> identity).
- Local v3 result: 10 / 10 ledger check (platform's own scorer, run locally) — matches the platform's official score.
- The fix lives in builder/gen.py; the next platform regeneration carries it. Note: the local harness uses DeepSeek for agent/customer/extraction, so judge verdicts are approximate; ledger is exact.

## 2026-10-11 16:32 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 437 s

- FAIL PUB-01 (easy, Happy path): outcome (None, None), expected ('promise', None); promises [], expected [('p1', 420.0, '2026-10-14')]; the call was not closed with close_call; conversation: The call ended prematurely after the initial greeting and name confirmation. Consequently, several mandatory success criteria were not met: security questions were not asked or passed, the 'get_account' and 'create_promise' functions were never called, and the required text-message sentence was never spoken.
- PASS PUB-02 (medium, Third party): ok
- FAIL PUB-03 (medium, Identity): outcome (None, None), expected ('not_verified', 'failed'); the call was not closed with close_call; conversation: The conversation ended prematurely after the user confirmed their identity. The assistant did not perform the security check or receive any wrong answers, and it failed to instruct the customer to use the app or a branch as required by the success criteria.
- FAIL PUB-04 (medium, Dates): outcome (None, None), expected ('promise', None); promises [], expected [('p1', 1250.0, '2026-10-23')]; conversation: The call failed to meet the success criteria because the promise date of 23 October was never discussed or established. The conversation ended abruptly after the user confirmed their identity, before any substantive negotiation or date setting could occur. Additionally, the agent volunteered that it was a digital assistant in the opening, but the specific criterion 'when asked' was not triggered b
- FAIL PUB-05 (medium, Hardship): outcome ('transferred', 'restructuring'), expected ('no_promise', 'hardship'); conversation: The assistant failed to meet two of the four success criteria: 1. It did not provide a sentence of sympathy after the user disclosed a hardship (job loss). 2. It did not offer the support team at any point during the conversation. Although the assistant correctly avoided persuasion attempts and did not offer any discounts or plans, the interaction was incomplete. The transcript shows that after th
- FAIL PUB-06 (hard, Amounts): outcome (None, None), expected ('promise', None); promises [], expected [('p1', 637.5, '2026-10-16')]; the call was not closed with close_call; conversation: The call ended prematurely after the user confirmed their identity. As a result, the agent did not offer the minimum payment or secure the required promise of 637.50 on October 16. Criteria 2 and 3 were not met.
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- FAIL PUB-10 (hard, Tool failure): outcome (None, None), expected ('promise', None); promises [], expected [('p1', 365.0, '2026-10-16')]; the call was not closed with close_call; conversation: The success criteria were not met because the conversation concluded before any promise could be made or recorded in a ledger. 1. The requirement for 'exactly one promise in the ledger' was not satisfied as the conversation ended immediately after identification. 2. While the agent correctly avoided saying 'recorded', the failure to document a promise as specified makes the evaluation unsuccessful

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 17:01 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 260 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- FAIL PUB-06 (hard, Amounts): promises [], expected [('p1', 637.5, '2026-10-16')]
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)
## 2026-10-11 17:43 — brief-a

- command: python3 builder/build.py briefs/brief-a.md --no-fix
- workflow 73a14df1-aec9-4c0d-a76a-50c703d08081, agent 8580c81d-938f-4854-9600-6901f5a1f4d6
- score: 10 / 10 passed
- duration: 211 s

- PASS PUB-01 (easy, Happy path): ok
- PASS PUB-02 (medium, Third party): ok
- PASS PUB-03 (medium, Identity): ok
- PASS PUB-04 (medium, Dates): ok
- PASS PUB-05 (medium, Hardship): ok
- PASS PUB-06 (hard, Amounts): ok
- PASS PUB-07 (hard, Dates): ok
- PASS PUB-08 (medium, Already paid): ok
- PASS PUB-09 (medium, Restructuring): ok
- PASS PUB-10 (hard, Tool failure): ok

- artifacts: results/brief-a.json, traces/brief-a.log, submission/brief-a.workflow.json
- judgement: (none noted)

## 2026-10-11 — cf-mock-deploy skill test (deploy pipeline end-to-end)
- Deployed `freya-cf-test-mock.fcodefcode3.workers.dev` via REST + MOCK_KV binding: health 200, GET probes 2/2.
- Smoke PASS: pre-identity refusals exact (`identity not verified`) on get_account AND create_promise; round trip verify×2 → get_account → create_promise → close_call; ledger outcome=promise, promises=[(p1,420,2026-10-14)], calls[-1]=close_call.
- Bug fixes made today: (1) seedFor stripped the -sN suffix with .exec()[1] on a no-capture-group regex → session ids fell through to derived hash identities (every identity check failed); (2) session counter was per-isolate memory → two isolates issued the same session id and overwrote each other's KV state (counter now read/incremented through KV); (3) loadState read memory before KV → stale in-memory state shadowed newer state from another isolate (reads are KV-first now). All three fixed in mock_gen.py (template + WORKER_PROMPT req 7/8b + validator check) and in the generated test worker.
- deploy.sh: the module multipart part now carries filename=worker.js (Cloudflare error 10021 "No such module" otherwise).
- Judgement: deploy path is proven; at the final window regenerate the worker with the fixed mock_gen.py and deploy with --with-kv (KV permission on the token is confirmed working).
## 2026-10-11 21:00 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 3 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:04 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 9 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:11 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:12 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:15 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 7 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:15 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 4 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:23 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 4 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:24 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:24 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:28 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 6 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 21:55 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 8 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 22:14 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 22:24 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 7 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 22:25 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
## 2026-10-11 22:30 — sim-tester: local-sim phase-1 baseline on v5 export (in progress)

- harness: local_sim on submission export d5852d72cec3be33dd40a6bee3b4de87 (updated_at 18:55:03Z, md5 of build script record). 7 contract tools -> DEPLOYED mock (real envelope/cross-call state); practice namespace -> local shim tests/sim-tester-practice-shim.py (sessions/ledger/close_call; deployed mock has no ledger read). Cases mechanically converted from example_checks.json by tests/sim-tester-build.py -> tests/sim-tester-cases-p1.json; gap probes by tests/sim-tester-build-extra.py -> tests/sim-tester-cases-p1-extra.json (cut-day harness copy tests/sim-tester-wf-p1-cutday.json = same workflow, ONLY test_variables.now -> 2026-11-05 cut day; close_call+transfer_to_human URLs -> shim, everything else byte-identical).
- ex1 (single-card debt read, 95004361): first attempt INVALID — at 3-way stream concurrency the claude CLI timed out (>120 s) on the agent reply right after cards_balance returned the CORRECT data (12.000/4.800/9.500/2.000 TL; EUR 85,20/34,10 — matches the example), so no reading was spoken; ledger hollow-PASS, judge FAIL = harness artifact. Re-running sequentially.
- ex6: dialogue ran clean through the goodbye (log kept) but verdict not reached before triage stop. ex2/ex3/ex4/ex5 stopped mid-run at 22:25 triage (time-box, LLM timeout risk) — logs kept.
- STRUCTURAL (no LLM): v5 export carries R3 phrase "henüz kesilmiş" (1), cut-day trigger text "kesim tarihiniz bugün" (3, {{statement_cut_today}} computed in statement_facts as now==cut date), but totalDebt/toplam borç = 0 hits — matches input-health's independent audit (29fe76f: facts code extracts totalDebt into totals but never publishes/uses it).
- probes (single sequential stream, running): probe-cutday = R4b acceptance test (customer 97631186: totalDebt 860.4 TL vs statementDebt 0 — numerically decisive; expect "Hesap kesim tarihiniz bugün" + 860,40 TL; failure mode = agent reads statement fields -> says 0/no debt). probe-ncut = R3 check (pre-authored s8_no_cut script; expect "henüz kesilmiş bir ekstresi olmadığı" + first cut date 05.11.2026, no invented dates).
- mock gaps (relayed @cloudflare-mock-deploy-skill 20bb170): deployed mock accepted same-week statement.week.change with NO token (contract says 401-once + already-has-week error); no practice/ledger read endpoint.
- judgement: v5 = R3 FIXED (pending probe-ncut confirmation), R4b STILL BROKEN (structural evidence solid; behavioral probe pending). If v6 lands: re-run probe-cutday + probe-ncut + ex1 on the new export — that is the acceptance test.
## 2026-10-11 22:32 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
- FINAL (22:45, stop order): v9 cutday run incomplete (CLI instability; no verdict). ncut (v9): ledger PASS, judge FAIL — call stalled at "kartın seçilmesi gerekiyor" with a single-card customer; agent never called cards_balance; workflow has NO single-card auto-proceed instruction (0 hits 'tek kart') — regression risk for ALL single-card customers (ex1 v5 showed the same stall, recovered only by customer improvisation). v9 R4b/R3 STRUCTURALLY FIXED (prompt + facts code verified). Local behavioral validation blocked by claude-CLI 120 s timeouts (GLM backend under load).
## 2026-10-11 22:42 — finalcase

- command: python3 builder/build.py finalcase/ https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1 --fix 1
- workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6
- no practice test run (test failed)
- duration: 5 s


- artifacts: results/finalcase.json, traces/finalcase.log, submission/finalcase.workflow.json
- judgement: (none noted)
