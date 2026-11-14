# LLM action-surface audit (draft for the "trust-boundary architecture" section)

Question: which paths let an LLM — directly or through a tool — change state, spend money, or
influence a decision, and what stands between the model output and the effect?

Method: static reading of `insurance_agent/agents/orchestrator.py` (tool schemas and dispatch),
`insurance_agent/tools/*.py` (pattern search for file writes, subprocess calls, outbound POSTs),
and the on-chain services in `blockchain-dental/scripts/`. **Verified** = read in code.
**Per docs** = stated in repository documentation but not re-read in code. **Unverified** = open.

Snapshot: 39 tool schemas in `orchestrator.py` (main `TOOLS` + `UNDERWRITING_TOOLS`).

## A. Tools with an effect outside the conversation (3 of 39)

| Tool | Effect | Guard between model output and effect | Residual risk |
|---|---|---|---|
| `start_gasless_dental_enrollment` | Creates a relay wallet, writes it to `data/relay_wallets.json` (private key in plaintext), sponsor pays gas, sends an on-chain application (`tools/relay_wallet.py` → `scripts/relay-wallet.js`). *Verified:* file write and subprocess call. *Per docs:* the transaction is `submitApplication`. | Contract underwriting rules decide approve / pending / reject. No explicit confirmation parameter in the tool signature. *Unverified:* whether the system prompt requires the user to confirm before the call. | An LLM argument-extraction error (age, premium, coverage) becomes an on-chain application. Plaintext key storage is demo-only. |
| `submit_wellness_checkin` | Writes `data/wellness_checkins.json`; adjusts the on-chain premium through `scripts/wellness-oracle.js` (`tools/blockchain_tool.py`, *verified* subprocess call). | The risk score is computed by deterministic code, not by the LLM. *Per docs:* the contract limits the adjustment to ±20% of the baseline premium and only the oracle address may call it. | Inputs are self-reported and come from the conversation. |
| `run_underwriting_review` (sub-agent) | When the final route is `human_review`, appends the case to `data/underwriting_review_queue.json` (`orchestrator.py` → `enqueue`). *Verified.* | The model only chooses `tier`. `route` comes from a code table; a missing or malformed structured answer falls back to `human_review`; a supplement is allowed once. *Per docs* (`insurance_agent/CLAUDE.md`). | Only the queue file is written; no on-chain action and no customer notification. |

No tool schema or subprocess call in `tools/` performs claim payment, premium collection, or
maturity refund. *Verified:* the only subprocess targets are the read-only `query-*.js` scripts,
`wellness-oracle.js`, and `relay-wallet.js`.

## B. Read-only tools (the rest)

`get_blockchain_dental_status`, `get_blockchain_altinvest_status`, `get_blockchain_parametric_status`,
`get_crypto_reserve_status`, `get_personal_trading_status`, `assess_*` (scoring), product search and
RAG tools. They cannot change state, but their output reaches the model, so they are the surface for
the **presentation errors** measured in this paper.

## C. Tools that bring untrusted text into the model

`fetch_webpage`, `search_web` (and the credit-score browser automation). **Verified:** the chatbot-side
Python code contains no prompt-injection check (no match for "injection" in `insurance_agent/**/*.py`).
The on-chain review services import `scripts/lib/injection-guard.js`. This is an open gap to state as
a limitation or close before submission.

## D. On-chain services around the model

| Component | Uses an LLM? | Effect |
|---|---|---|
| Contract rules (`DentalInsurance.sol`) | No | Claims ≤20% of the coverage limit are paid automatically while oracle mode is on; application approve/reject by coverage count. |
| `oracle-service.js` | Advisory only | Rule-based hospital-record verification then on-chain processing (*per file header*); for claims above 20% it posts an AI pre-review opinion to Slack and does nothing else. |
| `application-review-service.js` | Advisory only | Opinion for Pending applications posted to Slack; *verified:* no contract write calls in the file. |
| `lib/openai-client.js` | Text only | Header states it never makes on-chain decisions. |

## E. Human gates

Admin manual approval of pending applications and large claims; the `human_review` queue; Slack
approval for crypto trades and a separate customer-clicked approval route for personal bots
(*per docs*; those are routes, not tools).

## Reading for the paper

- By construction the LLM never executes a payment. It can **start** an application
  (`start_gasless_dental_enrollment`) and **trigger a bounded premium adjustment**
  (`submit_wellness_checkin`); both are bounded by contract-side rules, not by the model.
- In claims and underwriting review the model is an **advisor** (Slack opinion, `tier` proposal);
  rules and humans decide. Statements such as "the LLM never moves money" must be replaced by this
  enumerated, bounded form.
- Open items: confirmation behaviour for gasless enrollment, chatbot-side injection defence,
  plaintext key storage, and re-reading the contract caps behind the wellness adjustment.
