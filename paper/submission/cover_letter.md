# Cover Letter

**To**: The Editors of *Applied Sciences* (MDPI)
**Re**: Submission of Original Research Article
**Date**: 2026-11-27 (target)

---

Dear Editor,

We are pleased to submit the manuscript entitled **"Error Taxonomy and Mitigation Strategies for LLM Agents Querying Blockchain-Based Insurance Data"** for consideration for publication in *Applied Sciences*.

## Summary of the Contribution

As large language model (LLM) agents are increasingly deployed to query real-time structured data sources on behalf of users, a systematic characterization of their failure modes becomes essential. Our paper addresses a failure class that has not been previously taxonomized: **tool-layer presentation errors** (TLPEs), which arise when an LLM agent correctly retrieves structured data via tool-calling but then makes errors in synthesizing or presenting that data to the user.

We ground the taxonomy in a production blockchain-based insurance advisory system (InsureChain) that queries Ethereum smart contract state. The choice of domain is deliberate: insurance data is time-sensitive (maturity dates, payment deadlines), legally significant (incorrect values carry regulatory risk), and structured (arrays of policies, timestamp fields, status codes) — making TLPE consequences immediately visible.

Concretely, we:
1. Identify and define six recurring TLPE classes (array truncation, temporal arithmetic errors, stale tool-result reuse, timezone ambiguity, response expression variability, and conditional UI logic failure) grounded in documented user-reported incidents.
2. Propose four targeted mitigation strategies addressing each class's root cause.
3. Evaluate the mitigations via a 49-query before/after harness that calls the live chatbot's streaming API and compares responses against ground truth extracted from the blockchain node.

## Fit with Applied Sciences

The manuscript fits *Applied Sciences*' scope in computer science and information technology. It addresses applied system design rather than theoretical contributions, provides a concrete implementation case study, and offers generalizable design principles transferable to other LLM agent applications in finance and healthcare. It is consistent with previously published work in this venue on LLM evaluation (e.g., Pałgan et al., Vol. 16, 2026) and blockchain-based insurance systems.

## Originality

This work has not been published previously and is not under consideration for publication elsewhere. All co-authors have approved the manuscript and agree with its submission to *Applied Sciences*.

## Conflicts of Interest

The authors declare no conflict of interest.

## Suggested Reviewers

We suggest the following qualified reviewers (none of whom are co-authors or collaborators):

1. **Prof. Khaled Salah** (Khalifa University) — blockchain-based insurance systems, smart contracts; relevant prior work: DOI 10.1038/s41598-025-15676-4 (co-author of related paper in this area, different research group)
2. **Researchers in the LLM tool-calling / agent evaluation community** familiar with benchmarks such as CryptoAnalystBench or ToolLLM — we defer to the editor's selection for this category.
3. **Reviewers with applied NLP in finance/insurance background** — the intersection of LLM evaluation and financial-domain structured data is the core of this paper.

## Contact

Corresponding author: [name and email to be inserted]
Institution: [institution to be inserted]

We thank the editors for their time and consideration.

Sincerely,

[Author name(s)]
