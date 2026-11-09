# Rosetta: literature review (2026-11-09)

All works were matched to real records (arXiv id + version; GPTCache via Crossref). Venue tags give the source that confirmed the peer-reviewed version: [Crossref], [OpenAlex], [OpenReview] (ICLR/ICML/TMLR lack Crossref DOIs), or [arXiv jr]. "Preprint" means none was found. Scholar Gateway returned ACCESS_DENIED and DBLP a bot-check page; Google Scholar was not used.

## 1. Compact/structured prompts and compression

- **Jiang, Wu, Lin et al. (2023).** LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models. EMNLP 2023 [Crossref], [doi:10.18653/v1/2023.emnlp-main.825](https://doi.org/10.18653/v1/2023.emnlp-main.825); [arXiv:2310.05736v2](https://arxiv.org/abs/2310.05736)
  *Claim:* coarse-to-fine, budget-controlled token dropping compresses long prompts while keeping task performance. *For us:* lossy and token-level, unlike our lossless canonical packet; use it as a baseline arm.
- **He, Rungta, Koleczek et al. (2024).** Does Prompt Formatting Have Any Impact on LLM Performance? Preprint, [arXiv:2411.10541v1](https://arxiv.org/abs/2411.10541)
  *Claim:* the same content rendered as plain text, Markdown, JSON or YAML changed GPT-3.5 results by up to 40% on code translation; GPT-4 was more robust. *For us:* format effects are real but model-specific; replicate our token result per model.
- **Tam, Wu, Tsai et al. (2024).** Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of LLMs. EMNLP 2024 Industry [OpenAlex], [doi:10.18653/v1/2024.emnlp-industry.91](https://doi.org/10.18653/v1/2024.emnlp-industry.91); [arXiv:2408.02442v3](https://arxiv.org/abs/2408.02442)
  *Claim:* forcing structured *output* (JSON/XML) degrades reasoning, and stricter formats degrade it more. *For us:* our packet is structured *input*, but do not make the executor emit a strict packet.
- **Lee, D'Antoni, Berg-Kirkpatrick (2026).** The Format Tax. Preprint, [arXiv:2604.03616v1](https://arxiv.org/abs/2604.03616)
  *Claim:* most structured-format accuracy loss comes from the format *instruction*; reasoning freeform then formatting recovers most of it; recent closed models show little tax. *For us:* supports reason-first: plan freely, then compile the packet deterministically.
- **Xu, Xie, Zhao et al. (2025).** Chain of Draft: Thinking Faster by Writing Less. Preprint, [arXiv:2502.18600v2](https://arxiv.org/abs/2502.18600)
  *Claim:* terse intermediate "drafts" match chain-of-thought (CoT) accuracy with as little as 7.6% of the tokens. *For us:* a plausible mechanism for our ~50% reasoning cut (compact input, compact reasoning); measure reasoning style too.

## 2. Routing, cascades and when they pay

- **Chen, Zaharia, Zou (2023/2024).** FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance. TMLR [OpenReview]; [arXiv:2305.05176v1](https://arxiv.org/abs/2305.05176)
  *Claim:* prompt adaptation, model approximation and cascades can cut API cost substantially at matched quality. *For us:* savings need large price gaps; our 34-69% overhead fits a gate not much cheaper than the work it saves.
- **Ong, Almahairi, Wu et al. (2024).** RouteLLM: Learning to Route LLMs with Preference Data. ICLR 2025 [OpenReview]; [arXiv:2406.18665v4](https://arxiv.org/abs/2406.18665)
  *Claim:* routers trained on preference data cut cost by more than 2x in some cases without losing quality. *For us:* their routers are trained, ours zero-shot; report the same cost-quality curve across thresholds.
- **Li, Zhang, Guo et al. (2026).** LLMRouterBench: A Massive Benchmark and Unified Framework for LLM Routing. Findings of ACL 2026 [Crossref], [doi:10.18653/v1/2026.findings-acl.1881](https://doi.org/10.18653/v1/2026.findings-acl.1881); [arXiv:2601.07206v1](https://arxiv.org/abs/2601.07206)
  *Claim:* under unified evaluation, many routers perform similarly, and several (including commercial ones) fail to beat a simple baseline. *For us:* agrees with our negative routing result; add strong-only and random-at-matched-rate baselines.
- **Gupta, Narasimhan, Jitkrittum et al. (2024).** Language Model Cascades: Token-level Uncertainty and Beyond. ICLR 2024 [OpenReview]; [arXiv:2404.10136v1](https://arxiv.org/abs/2404.10136)
  *Claim:* sequence-level uncertainty has a length bias as a deferral signal; learned deferral over token-level uncertainty does better. *For us:* supports gating on short typed answers rather than generation confidence.
- **Dou, Lian, Li (2026).** Conformal Cascade: Distribution-Free Accuracy Guarantees for Multi-Tier LLM Inference. Preprint, [arXiv:2607.25018v3](https://arxiv.org/abs/2607.25018)
  *Claim:* deferring when the conformal prediction set is not a singleton gives a finite-sample accuracy bound and an explicit cost-vs-α formula. *For us:* a principled replacement for hand-set abstention bands.

## 3. Calibration, abstention and wording sensitivity

- **Sclar, Choi, Tsvetkov et al. (2023).** Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design. ICLR 2024 [OpenReview]; [arXiv:2310.11324v2](https://arxiv.org/abs/2310.11324)
  *Claim:* meaning-preserving format changes swing few-shot accuracy by up to 76 points. *For us:* consistent with our 0.17 shift; wording is part of the model.
- **Hua, Tang, Gu et al. (2025).** Flaw or Artifact? Rethinking Prompt Sensitivity in Evaluating LLMs. Preprint, [arXiv:2509.01790v1](https://arxiv.org/abs/2509.01790)
  *Claim:* much reported prompt sensitivity comes from log-likelihood scoring and rigid answer matching. *For us:* our gates are read exactly this way (answer-token probabilities), so sensitivity is intrinsic; calibrate per wording.
- **Jung, Brahman, Choi (2024).** Trust or Escalate: LLM Judges with Provable Guarantees for Human Agreement. ICLR 2025 [OpenReview]; [arXiv:2407.18370v1](https://arxiv.org/abs/2407.18370)
  *Claim:* judges abstain selectively with guaranteed human agreement; cheap judges escalate to strong ones. *For us:* the closest prior design to our post-check and abstention bands, with guaranteed thresholds.
- **Phillips, Gustafsson, Wu et al. (2026).** Entropy Alone is Insufficient for Safe Selective Prediction in LLMs. Preprint, [arXiv:2603.21172v1](https://arxiv.org/abs/2603.21172)
  *Claim:* entropy-based abstention fails in a model-dependent way; adding a correctness signal improves risk-coverage at low target error. *For us:* report risk-coverage curves, not just "bands caught all uncertain errors".

## 4. Caching: exact/prefix vs semantic

- **Kwon, Li, Zhuang et al. (2023).** Efficient Memory Management for LLM Serving with PagedAttention. SOSP 2023 [Crossref], [doi:10.1145/3600006.3613165](https://doi.org/10.1145/3600006.3613165); [arXiv:2309.06180v1](https://arxiv.org/abs/2309.06180)
  *Claim:* paged KV memory enables near-zero waste and KV sharing within and across requests. *For us:* a byte-stable canonical packet (sorted keys, LF) maximises prefix-cache hits. Measure provider cached-token counts.
- **Bang (2023).** GPTCache: An Open-Source Semantic Cache for LLM Applications Enabling Faster Answers and Cost Savings. NLP-OSS Workshop 2023, pp. 212-218 [Crossref], [doi:10.18653/v1/2023.nlposs-1.24](https://doi.org/10.18653/v1/2023.nlposs-1.24) (no arXiv version found).
  *Claim:* responses are reused when the query embedding is similar to a cached one. *For us:* this is the reference design for the approach we rejected.
- **Schroeder, Desai, Cuadron et al. (2025).** vCache: Verified Semantic Prompt Caching. ICLR 2026 [OpenReview]; [arXiv:2502.03771v5](https://arxiv.org/abs/2502.03771)
  *Claim:* static similarity thresholds give no correctness guarantee and cause unexpected error rates; per-entry learned thresholds meet user error bounds. *For us:* independently confirms our near-duplicate failure; the principled route back to similarity caching.
- **Zhang, Liu, Xie et al. (2026).** From Similarity to Vulnerability: Key Collision Attack on LLM Semantic Caching. Preprint, [arXiv:2601.23088v2](https://arxiv.org/abs/2601.23088)
  *Claim:* the locality semantic keys need conflicts with collision resistance, so black-box collision attacks succeed. *For us:* a security reason, beyond accuracy, to cache only canonical-equivalent decisions.
- **Zhang, Wornow, Wan et al. (2025).** Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents. NeurIPS 2025 [OpenAlex], [doi:10.52202/085713-3451](https://doi.org/10.52202/085713-3451); [arXiv:2506.14852v2](https://arxiv.org/abs/2506.14852)
  *Claim:* caching and adapting plan templates cut agent cost 50% and latency 27%. *For us:* in reason-first, the compiled plan packet is a natural exact-match cache key.

## 5. Plan-then-execute, reasoning cost and overthinking

- **Xu, Peng, Lei et al. (2023).** ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models. Preprint, [arXiv:2305.18323v1](https://arxiv.org/abs/2305.18323)
  *Claim:* planning up front, without interleaved observations, gave 5x token efficiency and +4% accuracy on HotpotQA. *For us:* early precedent for plan-once, execute-cheaply.
- **Zhou, Tie, Zhang et al. (2025).** Exploring the Necessity of Reasoning in LLM-based Agent Scenarios. Preprint, [arXiv:2503.11074v2](https://arxiv.org/abs/2503.11074)
  *Claim:* reasoning models win at plan design and plain LLMs at execution, and hybrids (LLM actor + reasoning-model reflector) work best. *For us:* directly supports reason-first.
- **Ma, He, Snell et al. (2025).** Reasoning Models Can Be Effective Without Thinking. Preprint, [arXiv:2504.09858v1](https://arxiv.org/abs/2504.09858)
  *Claim:* at matched token budgets, skipping thinking beats thinking, especially at low budgets. *For us:* consistent with our 79% cut; compare at matched cost.
- **Gema, Hägele, Chen et al. (2025).** Inverse Scaling in Test-Time Compute. TMLR 12/2025 [arXiv jr]; [arXiv:2507.14417v2](https://arxiv.org/abs/2507.14417)
  *Claim:* on some tasks, longer reasoning lowers accuracy (distraction, overfitting to framing). *For us:* reasoning-on is not a safe upper bound for the plan stage.
- **Srivastava, Bidhan, Yan et al. (2025).** Batch Prompting Suppresses Overthinking Reasoning Under Constraint. Preprint, [arXiv:2511.04108v4](https://arxiv.org/abs/2511.04108)
  *Claim:* with DeepSeek-R1 and o1, batching cut reasoning tokens 76% while preserving or improving accuracy across 13 benchmarks. *For us:* this **contradicts** our batching result (16% saved, worse answers); see below.

## 6. Unanswerable, false-premise and over-refusal

- **Hu, Luo, Wang et al. (2023).** Won't Get Fooled Again: Answering Questions with False Premises. ACL 2023 [OpenAlex], [doi:10.18653/v1/2023.acl-long.309](https://doi.org/10.18653/v1/2023.acl-long.309); [arXiv:2307.02394v1](https://arxiv.org/abs/2307.02394)
  *Claim:* models often hold the knowledge to rebut false premises; the issue is activating it. *For us:* premise rejection should be elicitable by explicitly allowing it in the packet.
- **Kim, Htut, Bowman et al. (2023).** (QA)²: Question Answering with Questionable Assumptions. ACL 2023 [Crossref], [doi:10.18653/v1/2023.acl-long.472](https://doi.org/10.18653/v1/2023.acl-long.472); [arXiv:2212.10003v2](https://arxiv.org/abs/2212.10003)
  *Claim:* natural queries with false or unverifiable assumptions need a distinct answer strategy, and models struggle with them. *For us:* a ready human-judged item source.
- **Kirichenko, Ibrahim, Chaudhuri et al. (2025).** AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions. NeurIPS 2025 [Crossref], [doi:10.52202/085713-5729](https://doi.org/10.52202/085713-5729); [arXiv:2506.09038v1](https://arxiv.org/abs/2506.09038)
  *Claim:* across 20 datasets, reasoning fine-tuning *degrades* abstention by 24% on average, and scale barely helps. *For us:* predicts the reasoning-on plan stage is weaker on false premises; test it.
- **Kalai, Nachum, Vempala et al. (2025).** Why Language Models Hallucinate. Preprint, [arXiv:2509.04664v1](https://arxiv.org/abs/2509.04664)
  *Claim:* binary grading rewards guessing over admitting uncertainty. *For us:* our honest/failed/cheated scoring and premise-rejection credit follow this recommendation.
- **Cui, Chiang, Stoica et al. (2024).** OR-Bench: An Over-Refusal Benchmark for LLMs. ICML 2025 [OpenReview]; [arXiv:2405.20947v5](https://arxiv.org/abs/2405.20947)
  *Claim:* 80k seemingly harmful but benign prompts expose widespread over-refusal. *For us:* add solvable controls that *look* impossible, so rejection is not rewarded blindly.

## 7. Specification gaming in coding agents

- **Zhong, Raghunathan, Carlini (2025).** ImpossibleBench: Measuring LLMs' Propensity of Exploiting Test Cases. Preprint, [arXiv:2510.20270v1](https://arxiv.org/abs/2510.20270)
  *Claim:* conflicting the spec with the unit tests makes any pass proof of cheating ("cheating rate"). *For us:* essentially our Kobayashi Maru design; reuse its variants for comparability.
- **Gabor, Lynch, Rosenfeld (2025).** EvilGenie: A Reward Hacking Benchmark. Preprint, [arXiv:2511.21654v2](https://arxiv.org/abs/2511.21654)
  *Claim:* an LLM judge detects unambiguous hacking well, held-out tests add little, and Codex and Claude Code both reward-hacked explicitly. *For us:* detect cheating with test-file diffs plus a judge.
- **Baker, Huizinga, Gao et al. (2025).** Monitoring Reasoning Models for Misbehavior and the Risks of Promoting Obfuscation. Preprint, [arXiv:2503.11926v1](https://arxiv.org/abs/2503.11926)
  *Claim:* chain-of-thought (CoT) monitors catch coding reward hacks better than action monitors, and a weaker model can monitor a stronger one. *For us:* reasoning-off execution removes this signal, a hidden cost of reason-first.
- **Wang, Joshi, Plank et al. (2025).** Is It Thinking or Cheating? Detecting Implicit Reward Hacking by Measuring Reasoning Effort (TRACE). ICLR 2026 [OpenReview]; [arXiv:2510.01367v4](https://arxiv.org/abs/2510.01367)
  *Claim:* hacks reach reward with a small fraction of the reasoning, and a truncation-AUC detector beats CoT monitors. *For us:* a cheap cheating signal for the plan stage.
- **Gomez (2026).** Can Escalation Channels Redirect Reward Hacking toward Defect Disclosure? Preprint, [arXiv:2608.29460v3](https://arxiv.org/abs/2608.29460)
  *Claim:* across 8 models, an escalation tool plus an anti-hacking policy cut hacking from 23.6% to 5.3%. *For us:* add a typed "REPORT_DEFECT" outcome to the packet; it maps onto "honest".

## 8. Evaluation statistics, ceilings and contamination

- **Miller (2024).** Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations. Preprint, [arXiv:2411.00640v1](https://arxiv.org/abs/2411.00640)
  *Claim:* treat items as draws from a super-population; use paired differences, clustered standard errors and power planning. *For us:* the method template for our comparisons.
- **Card, Henderson, Khandelwal et al. (2020).** With Little Power Comes Great Responsibility. EMNLP 2020 [Crossref], [doi:10.18653/v1/2020.emnlp-main.745](https://doi.org/10.18653/v1/2020.emnlp-main.745); [arXiv:2010.06595v1](https://arxiv.org/abs/2010.06595)
  *Claim:* underpowered NLP comparisons are common and exaggerate effects. *For us:* our small-n effects need power statements.
- **Kotawala (2026).** Resolution Diagnostics for Paired LLM Evaluation. Preprint, [arXiv:2605.30315v1](https://arxiv.org/abs/2605.30315)
  *Claim:* many leaderboard pairs are unresolved at α=0.05 with 80% power; the common power shortcut is off by about 2x. *For us:* report the ratio q = N/N* (items used vs items needed) for each comparison.
- **Akhtar, Reuel, Soni et al. (2026).** When AI Benchmarks Plateau: A Systematic Study of Benchmark Saturation. Preprint, [arXiv:2602.16763v4](https://arxiv.org/abs/2602.16763)
  *Claim:* nearly half of 60 benchmarks are saturated, and expert curation, not hidden test data, resists saturation. *For us:* drop ceiling items and curate hard items by hand.
- **Jain, Han, Gu et al. (2024).** LiveCodeBench: Holistic and Contamination Free Evaluation of LLMs for Code. ICLR 2025 [OpenReview]; [arXiv:2403.07974v2](https://arxiv.org/abs/2403.07974)
  *Claim:* time-stamped contest problems allow contamination checks. *For us:* source coding items released after each model's cutoff.

## What the literature says we should change or test next (prioritised)

1. **Re-analyse all results with paired, item-clustered statistics and power** (Miller; Card; Kotawala). Report a CI per delta and q = N/N*.
2. **Test reason-first against the "format tax" hypothesis.** Arms: prose, packet, plan→model-written packet, plan→compiled packet (Lee; Tam), at matched cost (Ma).
3. **Replace hand-set abstention bands with calibrated selective rules.** Use conformal deferral (Dou et al.) or Trust-or-Escalate-style guarantees (Jung et al.), and report risk-coverage curves (Phillips et al.).
4. **Calibrate decision models per wording.** Ensemble 3-5 paraphrases and treat the spread between them as uncertainty (Sclar; Mizrahi et al., TACL 2024, [doi:10.1162/tacl_a_00681](https://doi.org/10.1162/tacl_a_00681) [Crossref], arXiv:2401.00595v3; Hua et al.).
5. **Adopt ImpossibleBench-style impossible variants plus EvilGenie-style detection** (test-file diffs plus a judge). Add an escalation outcome (Gomez). Test whether reasoning-off execution cheats more (Baker et al.).
6. **Add solvable look-alike controls for premise tasks** (OR-Bench; (QA)²). Test whether reasoning-on abstains worse (AbstentionBench).
7. **Re-run batching with reasoning models measuring reasoning tokens** (Srivastava et al.). Consider joint routing and batching (Xu et al. 2026, arXiv:2605.28268v1, preprint).
8. **Measure prefix-cache hit rate from canonical packets** (Kwon et al.), and cache compiled plans by exact key (Zhang et al., APC).
9. **Add strong-only and random-at-matched-rate routing baselines** (LLMRouterBench), and model the price ratio at which gating breaks even (FrugalGPT).

## Where our findings look new or contradict prior work (cautious)

- **Routing costing tokens (+34-69%).** Routing papers report savings under large price gaps and cheap routers; LLMRouterBench also finds routers often fail to beat simple baselines. Stating the break-even condition explicitly seems under-reported, not new in principle.
- **Batching hurting quality.** This contradicts Srivastava et al. (76% fewer reasoning tokens at preserved accuracy) and Cheng et al. (EMNLP 2023 Industry, [doi:10.18653/v1/2023.emnlp-industry.74](https://doi.org/10.18653/v1/2023.emnlp-industry.74) [OpenAlex], arXiv:2301.08721v2). Differences in model, reasoning mode, task or our small n may explain it; treat ours as unconfirmed.
- **Structured input halving hidden reasoning.** Format studies measure accuracy, not reasoning length; an *input*-structure token effect appears little studied.
- **Two decision models agreeing at r=0.97.** We found no paper reporting near-redundancy of independent small decision models. Agreement may reflect shared training, not correctness.
- **Exact-canonical-only caching.** This is aligned with vCache and the collision-attack work. Using the canonical serialization as the equivalence relation appears uncommon.

## Searches run (reproducible)

**arXiv API** (export.arxiv.org/api/query, sortBy=relevance, max 12, kept 2024+): 32 `search_query` strings, e.g. `abs:"semantic caching" AND (abs:false OR abs:incorrect OR abs:attack OR abs:collision)`, `abs:"LLM routing" AND abs:cost`, `ti:cascade AND abs:"language model" AND abs:deferral`, `ti:overthinking AND abs:reasoning`, `abs:"thinking budget" OR abs:"reasoning budget"`, `abs:"selective prediction" AND abs:"language model"`, `abs:"false premise" AND abs:"reasoning model"`, `abs:"over-refusal" AND abs:reasoning`, `abs:"reward hacking" AND abs:"coding" AND abs:"unit tests"`, `abs:"impossible tasks" AND abs:"LLM" AND abs:agents`, `abs:"paired" AND abs:"bootstrap" AND abs:"LLM evaluation"`, `abs:"batch prompting" AND abs:accuracy`. Exact strings for every query (all APIs, 107 lines) are logged in C:/Users/danie/AppData/Local/Temp/claude/8d1f9bbcdea60d84/29d30e5a-338a-4102-9745-ff000b262e05/scratchpad/lit/searches_run.txt.
**arXiv id_list:** verified 62 ids; fetched abstracts of all cited papers.
**Semantic Scholar** `POST /graph/v1/paper/batch` (venues, citation counts).
**OpenAlex** `works?filter=title.search:<title>` for 40 titles (peer-reviewed venues/DOIs).
**OpenReview API2** `notes/search?term=<title>&content=title` for 22 ICLR/ICML/TMLR titles.
**Crossref** `works/<doi>` for 10 DOIs and one bibliographic query.
**Not usable:** Scholar Gateway semanticSearch (ACCESS_DENIED); DBLP (bot-check page).
**Excluded:** nothing was cited without a verified record. The peer-review status of ReWOO, NoThinking, ImpossibleBench and EvilGenie could not be confirmed, so they are listed as preprints.
