# Error Taxonomy and Mitigation Strategies for LLM Agents Querying Blockchain-Based Insurance Data

**[DRAFT v0.2 — 2026-11-14]**
**Target venue**: Applied Sciences (MDPI, SCIE) · Future Internet (MDPI, SCIE)
**Submission deadline**: 2026-11-27
**Experiment results**: [TBD — run `python paper/eval/harness.py --phase before/after` when blockchain stack is live]

---

## Abstract

Large language model (LLM) agents that invoke external tools to retrieve structured data introduce a category of errors that is distinct from factual hallucination: errors arising in the LLM's reasoning and presentation layer even when the underlying data retrieval succeeds. We identify, classify, and measure this failure class in a research prototype insurance chatbot system (InsureChain) that queries Ethereum smart contract state via tool-calling. Through analysis of real user-reported incidents and an 80-query before/after experiment, we document six recurring error types — (E1) array truncation, (E2) temporal arithmetic mistakes, (E3) stale tool-result reuse, (E4) timezone/locale ambiguity, (E5) response expression variability, and (E6) conditional UI logic failure — and propose four corresponding mitigation strategies: pre-computed string injection, explicit enumeration prompting, server-side tool-use flags, and history-aware tool tracking. Our evaluation shows that the mitigations reduce error rates from [TBD]% to [TBD]% on affected query types while leaving baseline performance unchanged. These findings generalize to any LLM agent that must faithfully report arrays, timestamps, or status codes from real-time structured data sources, with particular relevance for financial and healthcare applications where incorrect responses carry regulatory risk.

**Keywords**: large language model; tool calling; blockchain; insurance; error taxonomy; smart contract; hallucination mitigation; LLM agent

---

## 1. Introduction

The integration of large language models (LLMs) with external tools has enabled a new class of conversational agents capable of querying real-time databases, APIs, and distributed ledgers [1,2]. In domains such as insurance, banking, and healthcare, such agents offer significant promise: users can obtain policy status, claim updates, or transaction histories through natural-language conversation rather than navigating complex portals [9,10]. The resulting systems combine the flexibility of LLMs with the precision of structured data sources — in principle.

In practice, the tool-calling paradigm introduces a subtle failure mode that is both consequential and undercharacterized. When an LLM agent correctly retrieves structured data from an external source but then makes errors in interpreting, presenting, or propagating that data to the user, the resulting response is incorrect despite the data layer being accurate. We term this class of errors **tool-layer presentation errors** (TLPEs). Unlike hallucination — which involves the LLM generating content unsupported by any source — TLPEs occur specifically at the intersection of correct data retrieval and incorrect LLM synthesis. This distinction matters because standard hallucination mitigations (retrieval-augmented generation, source attribution, factuality scoring) are not designed to address TLPEs: the retrieved data is correct, yet the error persists.

This paper presents the first systematic taxonomy of TLPEs, grounded in an academic prototype deployment. Our system, InsureChain, is a research prototype of an insurance advisory chatbot backed by Ethereum smart contracts that record dental insurance policies, parametric triggers, and investment positions, deployed on a local Hardhat testnet. The immutable and time-sensitive nature of blockchain data makes TLPE consequences especially visible: a one-day error in a reported maturity date can cause a user to miss a claim window; a misreported DRY\_RUN status can lead a user to believe real trades are executing when they are not.

We make three contributions:

1. **A six-class taxonomy of TLPEs** (Section 4), each class grounded in one or more real user-reported incidents from the InsureChain deployment log. The taxonomy spans structural (array truncation), temporal (arithmetic errors, timezone ambiguity), multi-turn (stale result reuse), and system-level (expression variability, conditional logic failure) error classes.

2. **Four targeted mitigation strategies** (Section 5) that address the root cause of each class. The mitigations range from tool-layer changes (pre-computing human-readable strings before passing data to the LLM) to prompt-layer changes (explicit enumeration directives) to application-layer changes (emitting authoritative flags in the SSE event stream).

3. **An empirical evaluation** (Section 6) using an 80-query before/after experiment harness that calls the live chatbot's streaming API and compares responses against ground truth extracted from the blockchain node. Results demonstrate [TBD] after mitigation.

The remainder of this paper is organized as follows. Section 2 reviews related work. Section 3 describes the InsureChain system architecture. Sections 4 and 5 present the taxonomy and mitigations. Section 6 reports the evaluation. Section 7 discusses implications and limitations. Section 8 concludes.

---

## 2. Related Work

### 2.1 LLM Tool-Calling and Agents

Augmenting LLMs with the ability to invoke external tools has been a central theme in recent research. Yao et al. [1] introduced ReAct, which interleaves reasoning traces with tool actions (search, calculator, database lookup) in a single generation stream, achieving strong performance on multi-step question answering. Schick et al. [2] showed that LLMs can self-generate training data for tool use via Toolformer. The OpenAI function-calling interface [4] and its successors standardized the protocol by which LLMs declare and invoke typed function schemas, enabling reliable structured output.

Agent frameworks such as LangChain [5] and tool-learning surveys [9] extend tool-calling to multi-step, multi-tool pipelines, applying them to web browsing [6], code execution [7], and database query [8]. User-facing applications of such agents in regulated domains raise additional considerations around explainability and trustworthiness [3]. Despite this breadth, the literature on failure modes specific to the tool-calling interface remains sparse. Prior work has characterized errors in tool selection (invoking the wrong tool) and in tool output parsing (misreading structured responses), but has not systematically addressed errors in the LLM's subsequent presentation of correctly retrieved data to the user — the class we study here.

### 2.2 LLM Hallucination and Error Characterization

The hallucination literature addresses cases where LLMs generate plausible but factually incorrect content [11,12]. Ji et al. [11] survey hallucination in natural language generation and distinguish intrinsic (contradicting the source) from extrinsic (unverifiable against the source) hallucination. Huang et al. [12] catalogue causes and mitigation strategies, including chain-of-thought prompting and retrieval augmentation.

TLPEs differ from both intrinsic and extrinsic hallucination. The source (the tool output) is correct; the error arises not from fabrication but from reasoning steps applied to correct input — rounding a timestamp differently than the display layer, summarizing an array instead of enumerating it, or matching text patterns that the LLM has expressed in variable phrasings. These are, in a sense, *correct-source errors*, and require different detection and mitigation approaches. The closest related concept is faithfulness in summarization [13] — the degree to which a summary accurately reflects its source — but our setting involves structured data rather than natural language sources, and the errors we document are more systematic and reproducible than the stochastic faithfulness failures studied in that literature.

Recent work on LLM evaluation in structured settings includes CryptoAnalystBench [14], which establishes an error classification framework and LLM-as-judge evaluation methodology for financial data queries. We draw on this methodology in designing our evaluation harness (Section 6.1).

### 2.3 Blockchain Applications in Insurance

Blockchain-based insurance systems have been studied in the context of parametric triggers [15], fraud detection [16], and claims automation [17]. Etherisc and AXA's Fizzy platform are early production examples of on-chain parametric insurance, triggering payouts automatically when observable conditions (flight delays, weather events) cross thresholds [15].

Recent work has begun combining LLMs with blockchain insurance data. Islayem et al. [16] apply LLMs to fraud analysis in blockchain-based health insurance claims, achieving improved detection rates over baseline classifiers. ClaimPilot [17] uses an LLM-driven pipeline for end-to-end claim processing. The State-Aware Dual-Tool architecture [18] addresses multi-turn context loss in LLM agents using dual memory structures. These systems focus on the correctness of the downstream task (fraud detection, claim decision) rather than on the LLM's presentation of on-chain data to end users. To our knowledge, no prior work systematically identifies or mitigates the class of presentation errors we describe.

### 2.4 Gap

No prior work (a) defines TLPEs as a distinct error class, (b) provides a systematic taxonomy across multiple TLPE subtypes in a real deployment, or (c) evaluates targeted mitigations for each subtype against a blockchain data source. This paper addresses all three gaps.

---

## 3. System Architecture

### 3.1 InsureChain Overview

InsureChain integrates two subsystems: an LLM-based insurance advisory chatbot and an Ethereum-compatible smart contract backend for dental insurance policies. Figure 1 illustrates the high-level architecture.

```
+-------------------------------------------------------------+
|                    User (Browser)                           |
+-------------------+-----------------------------------------+
                    | HTTP / SSE
+-------------------v-----------------------------------------+
|          Flask Web Server  (port 5000)                      |
|  +-----------------------------------------------------+    |
|  |            Orchestrator Agent (GPT-4o)              |    |
|  |   +----------+  +----------+  +----------------+   |    |
|  |   | Underwr. |  |  Search  |  |  Blockchain    |   |    |
|  |   | Sub-Agent|  |  Tools   |  |  Query Tools   |   |    |
|  |   +----------+  +----------+  +--------+-------+   |    |
|  +-----------------------------------------------------+    |
+------------------------------------------+-----------------+
                    subprocess / JSON      |
+------------------------------------------v-----------------+
|          Node.js Scripts  (query-policy.js, etc.)           |
|          ethers.js -> Hardhat Node  (port 8545)             |
|  +-----------------------------------------------------+    |
|  |  DentalInsurance * ParametricInsurance              |    |
|  |  ReinsurancePool * AltInvestmentFund * ReserveFund  |    |
|  +-----------------------------------------------------+    |
+-------------------------------------------------------------+
```

**Figure 1.** InsureChain system architecture. The Orchestrator agent dispatches tool calls to blockchain query scripts, which return JSON representations of on-chain state. TLPEs occur in the LLM synthesis step between the tool output and the user response.

### 3.2 Chatbot Layer

The chatbot layer is a Flask application hosting a multi-agent GPT-4o pipeline. The primary Orchestrator agent (`agents/orchestrator.py`) handles intent classification and tool dispatch. It manages 24 tools across three categories: (i) product search tools (insurance product database, scraped market data), (ii) underwriting tools (health risk assessment, credit evaluation, flexible payment eligibility; 18 sub-tools delegated to a specialist sub-agent with structured output), and (iii) blockchain query tools (the focus of this paper).

The Orchestrator follows the standard function-calling loop: it generates tool\_call messages until it reaches a stop condition, then synthesizes a natural-language response from the accumulated tool outputs. This response is streamed to the client via Server-Sent Events (SSE).

### 3.3 Blockchain Query Layer

Four blockchain query tools are relevant to this study:

- `get_blockchain_dental_status(wallet_address)` — returns the full state of all dental insurance policies held by a wallet, including premium history, claim records, loan balances, and maturity status.
- `get_blockchain_altinvest_status(wallet_address)` — returns all alternative investment fund positions.
- `get_crypto_reserve_status(bot_id)` — returns the company's cryptocurrency reserve account status from a trading scheduler snapshot.
- `get_personal_trading_status(session_id)` — returns a session-specific personal trading account status.

Each Python tool function invokes a Node.js script via `subprocess.run()`, passing the wallet address as a command-line argument and reading the JSON output. The Node.js scripts use ethers.js to query the Hardhat local node and format the results. This two-layer design avoids adding Python web3 dependencies by reusing the existing JavaScript stack.

### 3.4 Data Characteristics That Amplify TLPEs

Blockchain data has three properties that make it particularly susceptible to TLPEs:

**Immutability and precision.** Timestamps are stored as Unix epoch integers (seconds). Converting them to human-readable dates requires arithmetic that the LLM performs in its synthesis step, introducing rounding and timezone errors (E2, E4).

**Array structures.** A wallet may hold multiple insurance policies, investment positions, or claim records simultaneously. The LLM must enumerate all items without omission, a task that conflicts with its default summarization tendency (E1).

**Multi-turn context.** Users naturally ask follow-up questions about data retrieved in a previous turn. The LLM may answer correctly from cached context without re-invoking the tool, while the application logic incorrectly treats this as a non-blockchain response (E3).

---

## 4. Error Taxonomy

We document six TLPE classes, each confirmed by: (a) a reproducible query sequence, (b) a documented before-state exhibiting the error, and (c) an identified root cause. All incidents were encountered during the InsureChain prototype testing period (September–November 2026).

### 4.1 E1: Array Truncation

**Definition.** The LLM reports only a subset of items in an array returned by the tool, omitting the remainder without indicating that items were omitted.

**Root cause.** GPT-4o applies a summarization heuristic when generating responses from long structured inputs. When the tool output contains an array of three or more items, the model tends to describe "representative" examples rather than enumerate all items exhaustively.

**Observed incident.** A user asked "내 보험 현황 전부 알려줘" (Show me all my insurance policies). The tool returned three policies. The model's response covered only policies #1 and #2, omitting policy #3 (a matured policy that had already been paid out). Direct inspection of the tool output confirmed all three were present.

**Example (before mitigation):**

```
Tool output:  policies: [
  {id:1, active:true, ...},
  {id:2, active:true, ...},
  {id:3, active:false, maturityPaid:true, ...}
]

LLM response: "현재 가입된 보험증권은 두 건입니다:   [= "Currently two policies are enrolled:"]
  - 증권 #1: 활성, 월 납입 $30.00, ...          [= "Policy #1: active, monthly $30.00"]
  - 증권 #2: 활성, 월 납입 $25.00, ..."         [= "Policy #2: active, monthly $25.00"]
  [Policy #3 silently omitted]
```

**Mitigation (M2).** The system prompt was augmented with an explicit enumeration directive: "policies 배열에 증권이 여러 개 있으면 하나도 빠짐없이 전부 답변에 포함하세요 — '대표로 2개만'처럼 일부만 요약해서 나머지를 조용히 빠뜨리면 안 됩니다."

### 4.2 E2: Temporal Arithmetic Error

**Definition.** The LLM independently computes a date, duration, or relative time expression from raw timestamp values, producing an incorrect result due to rounding or unit errors.

**Root cause.** The original tool returned `daysUntilMaturity` computed as `Math.ceil(remainingSeconds / 86400)`. For a policy maturing in 28 minutes (1,680 seconds), `Math.ceil(1680 / 86400) = 1`, causing the tool to report one day remaining. The LLM, receiving this value, correctly reproduced "1일 후 만기" — which the user interpreted as "tomorrow" — when the policy was in fact expiring that same day.

**Observed incident.** A user asked "오늘 만기야, 내일 만기야?" (Does it expire today or tomorrow?). The chatbot replied "내일 만기됩니다" (It expires tomorrow). The user reported the discrepancy after the policy matured later that same day.

**Example (before mitigation):**

```
Policy maturityDate timestamp: T + 1,680 seconds (~28 minutes)
daysUntilMaturity: Math.ceil(1680/86400) = 1

LLM response: "만기일까지 1일 남았습니다."     [= "1 day until maturity."]
              -> User interprets as: "expires tomorrow"
Correct answer: "오늘, 약 28분 후 만기됩니다." [= "Today, approximately 28 minutes remaining."]
```

**Mitigation (M1a).** The tool now computes a human-readable `timeUntilMaturity` string using `Math.floor`-based duration logic identical to the frontend display, and includes it in the JSON payload. The system prompt instructs the LLM to use this string verbatim rather than performing its own date arithmetic.

### 4.3 E3: Stale Tool-Result Reuse

**Definition.** In a multi-turn conversation, the LLM answers a follow-up query by reusing a tool result from a previous turn without re-invoking the tool. Application logic that checks only the current turn's tool calls incorrectly classifies this response as a non-blockchain response, causing unwanted downstream behavior (such as appending an irrelevant news section).

**Root cause.** GPT-4o's context window includes prior tool results. When a follow-up question (e.g., "이번 달 보험료 냈어?" — Did you pay this month's premium?) can be answered from already-retrieved policy data, the model correctly answers without re-calling the tool. However, the application's tool-use detection flag (`used_blockchain_tool`) was set only when a tool call was observed in the current turn, so follow-up responses were classified as non-blockchain, triggering the irrelevant news section.

**Observed incident.** A user asked "내 보험 현황 보여줘" (Show my insurance status) in turn 1 — the tool was invoked. In turn 2 the user asked "이번 달 납입은 됐어?" (Was this month's payment made?). The turn-2 response was factually correct but had an irrelevant "최신 보험 뉴스" (Latest insurance news) section appended, as if it were a general insurance question.

**Mitigation (M4).** A `_last_tool_call_names()` helper scans the conversation history to identify the most recent tool call. If that call was a blockchain query tool, the current turn is treated as a blockchain response even if no tool was invoked this turn.

### 4.4 E4: Timezone/Locale Ambiguity

**Definition.** The LLM receives a datetime string without an explicit timezone label and interprets it inconsistently across sessions, producing timestamps that differ from the frontend display (which uses explicit KST).

**Root cause.** The original `tsToDate()` function in `query-policy.js` used JavaScript's `toISOString()`, producing UTC strings of the form `"2026-09-18T11:15:05.000Z"`. GPT-4o has no stable policy for interpreting unlabeled UTC strings: in some sessions it treats the string as UTC (correctly), in others it re-interprets it in an assumed local timezone. Meanwhile, the frontend uses `toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })`, which renders the same timestamp 9 hours later (KST). This produced a consistent 9-hour discrepancy between the chatbot's answers and the frontend display.

**Observed incident.** A user provided a screenshot comparison showing the chatbot reporting "오후 2:15:05" for a policy event while the frontend showed "오후 11:15:05" for the same event. On a second query the following day, the chatbot reported "오전 11:15:05" — the UTC time — indicating non-deterministic interpretation.

**Mitigation (M1b).** `tsToDate()` was replaced with `new Date(n * 1000).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) + " (KST)"`. Every timestamp in the tool output now carries an explicit timezone label, ensuring consistent interpretation across LLM sessions.

### 4.5 E5: Response Expression Variability

**Definition.** The LLM describes the same factual state using different natural-language phrasings across turns or sessions. Frontend logic that infers the tool type from response text fails non-deterministically because no single text pattern covers all phrasings.

**Root cause.** LLM non-determinism means the same underlying fact (e.g., "this bot is in dry-run mode") may be expressed as "DRY\_RUN=True", "DRY\_RUN: true", "드라이 런(dry\_run)", "페이퍼(모의) 모드", or "모의 주문 상태" in different sessions. Frontend code that matched the string "DRY\_RUN" to suppress insurance product comparison buttons failed when the LLM used an unlisted phrasing.

**Observed incident.** A user asked about cryptocurrency reserve performance. The chatbot's response included a performance table. In one session, insurance product comparison buttons appeared on the crypto performance table (incorrect); in another they did not (correct), because the LLM happened to use a different phrasing.

**Mitigation (M3).** The application abandons text-based inference entirely. The server now emits authoritative boolean flags (`used_blockchain_tool`, `used_crypto_tool`) in the SSE `done` event. Frontend logic reads these flags directly, with no text pattern matching.

### 4.6 E6: Conditional UI Logic Failure

**Definition.** Application logic infers which tool category was invoked by scanning the LLM's response text for keywords, and takes incorrect conditional action (rendering wrong UI elements, appending wrong sections) because the LLM's phrasing does not match the expected patterns.

**Root cause.** An early implementation determined whether to render insurance product comparison buttons by checking for keywords ("Ticker", "티커", "종목", "DRY\_RUN") in the HTML table headers and cell content of the LLM response. This was motivated by the need to suppress insurance buttons on crypto performance tables, but relied on stable LLM phrasing — which E5 showed is not stable.

**Relationship to E5.** E6 is the application-level consequence of E5: E5 describes the LLM's variable phrasing; E6 describes the resulting incorrect application behavior. We treat them as separate classes because they have different detection and mitigation points (E5 is a model-layer property; E6 is an application-layer failure).

**Observed incident.** A user viewing a crypto trading performance table saw "블록체인 가입 시작" (Blockchain enrollment) buttons attached to table rows, which were irrelevant and confusing. The buttons appeared because the LLM described the trading bot state using "드라이 런" rather than "DRY\_RUN", causing the keyword filter to miss the crypto context.

**Mitigation (M3).** Same as E5: server-side flags replace text-based inference. The `addLinksToTables()` function accepts a `skip` parameter set by the SSE `used_crypto_tool` flag; when true, no insurance buttons are rendered regardless of table content.

---

## 5. Mitigation Strategies

We propose four mitigation strategies addressing the six error classes. Table 1 maps each strategy to the errors it addresses.

**Table 1.** Mitigation-to-error mapping.

| Strategy | Targets | Layer |
|---|---|---|
| M1: Pre-computed string injection | E2, E4 | Tool (Node.js) |
| M2: Explicit enumeration prompt | E1 | Prompt (system) |
| M3: Server-side tool-use flags | E5, E6 | Application (SSE) |
| M4: History-aware tool tracking | E3 | Application (Python) |

### 5.1 M1: Pre-Computed String Injection

**Principle.** Delegate all time-sensitive and locale-sensitive calculations to deterministic code; pass the resulting human-readable string to the LLM rather than raw numeric or timezone-ambiguous values.

**Implementation.** Two changes are made to `query-policy.js`:

(1) `tsToDate(ts)` is rewritten to produce explicit KST-labelled strings:

```javascript
function tsToDate(ts) {
  const n = Number(ts);
  if (n === 0) return null;
  return new Date(n * 1000)
    .toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) + " (KST)";
}
```

(2) A `timeUntilMaturity` field is computed using `Math.floor`-based duration logic:

```javascript
const remaining = Number(p.maturityDate) - nowTs;
const days  = Math.floor(remaining / 86400);
const hours = Math.floor((remaining % 86400) / 3600);
const mins  = Math.floor((remaining % 3600) / 60);
timeUntilMaturity = days > 0 ? `${days}일 ${hours}시간 후`
  : hours > 0 ? `오늘, ${hours}시간 ${mins}분 후`
  : `오늘, ${mins}분 후`;
```

The system prompt instructs the LLM to use the `timeUntilMaturity` string verbatim rather than recomputing from `maturityDate`.

**Why this works.** The LLM never performs date arithmetic; it merely copies a pre-verified string. The string is computed by the same code path as the frontend display, guaranteeing consistency.

### 5.2 M2: Explicit Enumeration Prompt

**Principle.** Override the LLM's default summarization tendency with an explicit instruction that is specific to the tool's array structure.

**Implementation.** The system prompt is extended with:
> "policies 배열에 증권이 여러 개 있으면 **하나도 빠짐없이 전부** 답변에 포함하세요 (증권 ID, 만기일 등). '대표로 2개만', '첫 번째·두 번째만'처럼 일부만 요약하고 나머지를 조용히 빠뜨리면 안 됩니다." (Translation: "If the policies array contains multiple entries, include **every single one** in the response — do not silently omit any by summarizing only a representative subset.")

An equivalent directive is added for the `positions` array in `get_blockchain_altinvest_status`.

**Cost and risk.** Explicit enumeration prompts lengthen the LLM's output proportionally to array size, increasing token cost. For typical policy counts (1–5 policies per wallet) the overhead is negligible. The directive does not affect non-blockchain tool calls, as it is scoped to the specific tool description in the system prompt.

### 5.3 M3: Server-Side Tool-Use Flags

**Principle.** Replace text-based inference of tool type with authoritative boolean flags emitted by the server, eliminating dependence on LLM phrasing.

**Implementation.** The orchestrator tracks which tool categories were invoked in the current turn. At the end of `stream_chat()`, it emits a SSE `done` event with two flag fields:

```python
yield json.dumps({
    "type": "done",
    "full_text": full_content,
    "used_blockchain_tool": used_blockchain_tool,
    "used_crypto_tool": used_crypto_tool,
})
```

The frontend reads these flags and uses them directly:

- `used_blockchain_tool=True` → suppress news section
- `used_crypto_tool=True` → suppress insurance product buttons in `addLinksToTables()`

**Why this works.** The server knows definitively which tools were called, independent of how the LLM chose to describe their outputs. This information is not subject to expression variability.

### 5.4 M4: History-Aware Tool Tracking

**Principle.** Extend tool-use detection beyond the current turn to cover the most recent tool call in the conversation history, handling the case where the LLM reuses a previous turn's result.

**Implementation.** A `_last_tool_call_names()` static method scans the conversation history in reverse:

```python
@staticmethod
def _last_tool_call_names(history: list[dict]) -> set[str]:
    for msg in reversed(history):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            return {tc["function"]["name"]
                    for tc in msg["tool_calls"]}
    return set()
```

After the generation loop completes without any tool call in the current turn, the orchestrator checks whether the most recently called tool was a blockchain query tool:

```python
if not any_tool_used and _last_tool_call_names(history) & {
    "get_blockchain_dental_status",
    "get_blockchain_altinvest_status",
    "get_crypto_reserve_status",
    "get_personal_trading_status",
}:
    used_blockchain_tool = True
```

**Scope limitation.** This heuristic covers one-turn lookback. If the user asks a blockchain follow-up question several turns after the original query, the heuristic may fail to identify the blockchain context. For the typical usage pattern observed (follow-up within 1–2 turns), this is sufficient.

---

## 6. Evaluation

### 6.1 Experimental Setup

**Query set.** We constructed 80 evaluation queries across nine groups (Table 2). For each error class (E1–E6), we define 10 queries each (5 before-mitigation, 5 after-mitigation triggers) that reliably activate the error in the before-mitigation condition and should be resolved in the after-mitigation condition. We also include 5 baseline control queries (non-blockchain questions) to verify that mitigations do not degrade general performance, 10 mixed-condition queries combining multiple error triggers, and 5 stress/boundary queries targeting edge cases such as empty arrays and already-expired policies.

**Table 2.** Evaluation query distribution. E1–E6 queries run in the phase they are labelled for; MX/BL/ST run in both conditions. *n* = number of distinct queries per group.

| Group | Description | *n* | Mitigation tested |
|---|---|---|---|
| E1 | Array truncation | 10 | M2 |
| E2 | Temporal arithmetic | 10 | M1a |
| E3 | Stale tool reuse | 10 | M4 |
| E4 | Timezone ambiguity | 10 | M1b |
| E5 | Expression variability | 10 | M3 |
| E6 | Conditional logic | 10 | M3 |
| MX | Mixed / multi-error | 10 | M1–M4 |
| BL | Baseline (non-blockchain) | 5 | — (control) |
| ST | Stress / boundary | 5 | M1–M4 |
| **Total** | | **80** | |

**Before condition.** Evaluated on the `paper/before-mitigation` git branch, which removes M1–M4 from the codebase: `tsToDate()` reverts to `toISOString()`, `timeUntilMaturity` is removed and `Math.ceil(daysUntilMaturity)` is restored, the enumeration prompt is removed, SSE flags are removed, and `_last_tool_call_names()` is removed.

**After condition.** Evaluated on `main`, the current research prototype branch with all mitigations applied.

**Ground truth.** For structural queries (array counts, timestamps), ground truth is extracted at evaluation time by calling `node blockchain-dental/scripts/query-policy.js <wallet>` on a fixed local Hardhat node with known state (Hardhat Account #1, deployed via `scripts/deploy.js`). The Hardhat node is deterministic: re-deployment always produces the same contract state, ensuring reproducible ground truth.

**Evaluation model.** GPT-4o (`gpt-4o`, API default version at evaluation time), temperature=1 (default). Each query is run once per experimental condition; for E5/E6 (which depend on SSE flags rather than LLM text), the flag value is deterministic and a single run is sufficient. The evaluation harness supports a `--model` flag to repeat runs with alternative models (e.g., `gpt-4o-mini`) for multi-model comparison; results are stored separately per model under `paper/eval/results/{model}/`.

**Scoring.** Each query is scored on three binary dimensions:
- **Correctness (C)**: the main answer is factually correct
- **No-news (N)**: no irrelevant insurance news section appears (blockchain queries only)
- **Flags-ok (F)**: the SSE `used_*_tool` flags match the actual tool call (blockchain queries only)

### 6.2 Results

> **[TBD — run `python paper/eval/harness.py --phase before` on `paper/before-mitigation` branch, then `--phase after` on `main`, then `--report`]**

**Table 3.** Error rates before and after mitigation. [TBD after experiments]

| Error Type | Before CR | After CR | Delta CR | Mitigation |
|---|---|---|---|---|
| E1 Array truncation | [TBD]% | [TBD]% | [TBD] | M2 |
| E2 Temporal arithmetic | [TBD]% | [TBD]% | [TBD] | M1a |
| E3 Stale tool reuse | [TBD]% | [TBD]% | [TBD] | M4 |
| E4 Timezone ambiguity | [TBD]% | [TBD]% | [TBD] | M1b |
| E5 Expression variability | [TBD]% | [TBD]% | [TBD] | M3 |
| E6 Conditional logic | [TBD]% | [TBD]% | [TBD] | M3 |
| Baseline | [TBD]% | [TBD]% | ~0% | — |

**Figure 2.** Before vs. after correctness rate by error type (bar chart). → `paper/draft/figures/fig2_before_after.png` [TBD]

### 6.3 Discussion of Results

> **[TBD — fill after experiments]**

Key claims to verify empirically:
1. TLPEs are systematic, not random — the same query reliably triggers the same error type.
2. Mitigations are targeted — M1 fixes E2/E4 but does not affect E1 rates; M2 fixes E1 without affecting E2–E6.
3. Baseline performance is unchanged — mitigations add no degradation on non-blockchain queries.

---

## 7. Discussion

### 7.1 Generalizability

The six TLPE classes identified here are not specific to insurance or blockchain. They arise from two fundamental structural properties: (1) the tool returns structured data with numeric, temporal, or array fields; (2) an LLM synthesizes a natural-language response from that data. Any system sharing these properties is susceptible to the same taxonomy.

Concretely:
- **E1 (array truncation)** will occur in any agent that returns lists of items (search results, database rows, calendar events) where the LLM is expected to enumerate all items.
- **E2 (temporal arithmetic)** will occur whenever the LLM is asked to reason about timestamps, durations, or deadlines from raw numeric values.
- **E3 (stale reuse)** will occur in any multi-turn agent where the user asks follow-up questions about previously retrieved data.
- **E4 (timezone ambiguity)** will occur when the tool and the user interface use different timezone representations without explicit labeling.
- **E5/E6 (expression variability, conditional logic)** will occur in any application that infers the LLM's reasoning path from its output text rather than from server-authoritative signals.

The mitigations we propose are similarly general. M1 (pre-computed strings) can be applied to any structured data field that the LLM would otherwise recompute. M2 (enumeration prompts) can be scoped to any tool that returns arrays. M3 (server-side flags) is applicable to any application that needs to condition UI behavior on tool-call outcomes. M4 (history tracking) is applicable to any multi-turn agent with single-topic conversation threads.

### 7.2 Implications for Financial and Healthcare Applications

Insurance and financial applications amplify the consequences of TLPEs in two ways. First, the data has legal and fiduciary significance: an incorrect maturity date can cause a user to miss a claim window; an incorrect balance can lead to incorrect investment decisions. Second, users may place disproportionate trust in AI-generated responses that appear precise and confident, even when they contain subtle errors that a human expert would immediately recognize.

Our findings suggest that developers of LLM systems for such applications should explicitly audit for each TLPE class before deployment. The taxonomy provides a checklist: does the system return arrays? Does it return timestamps? Does it support multi-turn conversation? Does the frontend condition any behavior on the LLM's response text? Each affirmative answer is a TLPE risk that warrants targeted mitigation.

### 7.3 Design Principle: Move Knowledge Server-Side

A recurring theme across the mitigations is that the LLM should not be asked to perform computations that the server can perform deterministically. The LLM's role in a tool-augmented system is synthesis and explanation, not arithmetic or state management. M1, M3, and M4 all instantiate this principle: pre-compute durations rather than asking the LLM to calculate them; emit tool-use flags from the server rather than asking the LLM to signal its own reasoning path; track conversation history in application code rather than inferring it from LLM behavior.

This principle has a corollary for system design: LLM-facing tool outputs should be designed as *presentation layers*, not raw data dumps. Rather than passing Unix timestamps, pass human-readable date strings. Rather than passing raw arrays, consider whether the LLM needs all items or only the most relevant subset. Rather than relying on LLM text for downstream application logic, emit structured metadata alongside the LLM response.

### 7.4 Limitations

**Single model.** All experiments use GPT-4o. TLPE rates and mitigation effectiveness may differ for other models. Smaller models (GPT-4o-mini, open-weight models) may exhibit higher base TLPE rates; larger or more recent models may exhibit lower rates, potentially reducing the need for some mitigations.

**Local testnet.** The blockchain node is a local Hardhat instance with synthetic data. Real mainnet deployments may exhibit different latency characteristics; whether this affects TLPE rates is not clear.

**Sample size.** With 10 queries per error class, per-class statistics are based on moderate samples sufficient for taxonomy validation. The study is best interpreted as a taxonomy and feasibility demonstration rather than a large-scale empirical characterization.

**Manual classification.** Correctness scoring for E1 and E2 is automated via pattern matching; E3–E6 scoring involves manual verification of select edge cases.

**Korean language.** InsureChain operates in Korean. It is unclear whether TLPE rates differ in English or other languages, as the LLM's summarization and phrasing tendencies may vary by language.

---

## 8. Conclusion

We presented the first systematic taxonomy of tool-layer presentation errors (TLPEs) in LLM agents querying structured real-time data, grounded in a research prototype blockchain-based insurance advisory system. The six-class taxonomy — array truncation, temporal arithmetic, stale tool-result reuse, timezone ambiguity, response expression variability, and conditional logic failure — identifies recurring, systematic failure modes that persist even when the underlying data retrieval is correct. Four targeted mitigation strategies reduce aggregate error rates by [TBD]% without degrading baseline performance. Beyond the specific system studied, the taxonomy provides a generalizable checklist for developers building LLM agents over structured data sources, and the mitigations instantiate a design principle: move knowledge server-side, and treat the LLM as a synthesizer rather than a calculator.

---

## References

1. Yao, S.; Zhao, J.; Yu, D.; Du, N.; Shafran, I.; Narasimhan, K.; Cao, Y. ReAct: Synergizing Reasoning and Acting in Language Models. In *Proceedings of the International Conference on Learning Representations (ICLR 2023)*; 2023.
2. Schick, T.; Dwivedi-Yu, J.; Dessì, R.; Raileanu, R.; Lomeli, M.; Hambro, E.; Zettlemoyer, L.; Cancedda, N.; Scialom, T. Toolformer: Language Models Can Teach Themselves to Use Tools. In *Proceedings of NeurIPS 2023*; 2023.
3. Liao, Q.V.; Muller, M.; Huang, V.; Chandra, R. AI Fairness in Practice. *IBM Journal of Research and Development* **2021**, *65*, 1–13.
4. OpenAI. Function Calling. Available online: https://platform.openai.com/docs/guides/function-calling (accessed 14 November 2026).
5. Chase, H. LangChain. Available online: https://github.com/langchain-ai/langchain (accessed 14 November 2026).
6. Nakano, R.; Hilton, J.; Balwit, A.; Wu, J.; Glaese, A.; Chen, L.; Schulman, J. WebGPT: Browser-Assisted Question-Answering with Human Feedback. *arXiv* **2021**, arXiv:2112.09332.
7. Chen, M.; Tworek, J.; Jun, H.; Yuan, Q.; de Oliveira Pinto, H.P.; Kaplan, J.; Edwards, H.; Burda, Y.; Joseph, N.; Brockman, G.; et al. Evaluating Large Language Models Trained on Code. *arXiv* **2021**, arXiv:2107.03374.
8. Rajkumar, N.; Li, R.; Bahdanau, D. Evaluating the Text-to-SQL Capabilities of Large Language Models. *arXiv* **2022**, arXiv:2204.00498.
9. Qin, Y.; Liang, S.; Ye, Y.; Zhu, K.; Yan, L.; Lu, Y.; Lin, Y.; Cong, X.; Tang, X.; Qian, B.; et al. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs. *arXiv* **2023**, arXiv:2307.16789.
10. Mialon, G.; Dessì, R.; Lomeli, M.; Nalmpantis, C.; Pasunuru, R.; Raileanu, R.; Rozière, B.; Schick, T.; Dwivedi-Yu, J.; Celikyilmaz, A.; et al. Augmented Language Models: A Survey. *Transactions on Machine Learning Research* **2023**.
11. Ji, Z.; Lee, N.; Frieske, R.; Yu, T.; Su, D.; Xu, Y.; Ishii, E.; Bang, Y.J.; Madotto, A.; Fung, P. Survey of Hallucination in Natural Language Generation. *ACM Computing Surveys* **2023**, *55*, 1–38.
12. Huang, L.; Yu, W.; Ma, W.; Zhong, W.; Feng, Z.; Wang, H.; Chen, Q.; Peng, W.; Feng, X.; Qin, B.; et al. A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions. *arXiv* **2023**, arXiv:2311.05232.
13. Maynez, J.; Narayan, S.; Bohnet, B.; McDonald, R. On Faithfulness and Factuality in Abstractive Summarization. In *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics (ACL 2020)*; 2020; pp. 1906–1919.
14. Eswaran, A.; Golev, O.; Tank, D.; Rahi, S.; Tyagi, H. CryptoAnalystBench: Failures in Multi-Tool Long-Form LLM Analysis. *arXiv* **2026**, arXiv:2602.11304.
15. Diehl, S. Etherisc: Decentralized Insurance Protocol. Available online: https://etherisc.com (accessed 14 November 2026).
16. Islayem, R.; Gebreab, S.; AlKhader, W.; Musamih, A.; Salah, K.; Jayaraman, R.; Khan, M.K. Using Large Language Models for Enhanced Fraud Analysis and Detection in Blockchain Based Health Insurance Claims. *Scientific Reports* **2025**, *15*, 11542. https://doi.org/10.1038/s41598-025-15676-4
17. Mo, Z.; Quan, Z.; O'Donohue, E.; Zhong, K. Claim Automation using Large Language Model. *arXiv* **2026**, arXiv:2602.16836. (Preprint)
18. Pałgan, B.; Wawryszczuk, M.; Chwał, J. A State-Aware Dual-Tool Architecture for Improved Tool Use in Multi-Turn LLM Dialogue. *Applied Sciences* **2026**, *16*, 4329. https://doi.org/10.3390/app16094329

---

## Appendix A: Full Query Set

See `paper/eval/queries.json` (80 queries across 9 groups: E1–E6 primary with 10 queries each, MX mixed, BL baseline control, ST stress; available in the project repository).

## Appendix B: Evaluation Harness

See `paper/eval/harness.py`. Usage:

```bash
# Step 1: Before-mitigation (run on paper/before-mitigation branch)
git checkout paper/before-mitigation
cd insurance_agent && python ..\paper\eval\harness.py --phase before

# Step 2: After-mitigation (run on main branch)
git checkout main
cd insurance_agent && python ..\paper\eval\harness.py --phase after

# Step 3: Summary report
python paper\eval\harness.py --report
```

Requires: Flask server on `localhost:5000` and Hardhat node on `localhost:8545`.
Start with: (1) `blockchain-dental\run.bat` in a new window, (2) `start.bat` in another window.

## Appendix C: System Availability

InsureChain source code: https://github.com/leeyonsei78/capstone_project_alpha
