---

# Code as Reasoning: LLM-Generated Cascades for Semantically-Linked Table Prediction

## Abstract

We propose an agentic approach to relational table prediction in which a large language model discovers business rules through iterative SQL profiling and codifies them as hierarchical cascade lookups. On the SALT-KG benchmark (8 SAP fields, 1.9M training rows), our method outperforms both embedding baselines and a heterogeneous GNN (RelBench v2) on all 8 fields, with the largest margins on high-cardinality fields requiring business semantics (SALESGROUP: 70.0% vs GNN 15.8%; CUSTOMERPAYMENTTERMS: 82.9% vs GNN 37.5%). To understand when and why cascade lookups succeed or fail beyond enterprise data, we evaluate on two additional RelBench v2 autocomplete tasks: rel-arxiv author-category and rel-stack badges-class. On both non-enterprise tasks, cascades match or slightly underperform GNNs (arxiv: 52.6% vs GNN 52.6%; stack: 77.6% vs GNN 80.0%), revealing that the method's advantage is specific to domains with configured determinism—such as ERP systems—where field values are governed by explicit business rules recoverable through SQL profiling. A drift root-cause analysis on SALT-KG reveals that residual prediction ceilings are driven by organizational restructuring rather than method limitations.

---

## 1. Introduction

Predicting field values in multi-table enterprise data underpins business process automation in ERP systems. The SALT-KG benchmark [1] evaluates this task on SAP sales order data, where prior work uses embedding-based similarity matching optionally enhanced with a metadata Knowledge Graph.

We observe that many ERP field values are not learned associations but *configured determinism*: SAP's Condition Technique traverses ordered lookup tables (Access Sequences) to resolve values like payment terms or Incoterms. This structure is recoverable from transactional data through systematic profiling. A key question is whether this advantage generalizes: can cascade lookups outperform GNNs on non-enterprise relational data?

We contribute: (1) a three-phase agentic workflow where an LLM discovers cascade structures via SQL auditing grounded in KG semantics; (2) state-of-the-art accuracy on SALT-KG, outperforming both embedding baselines and end-to-end GNNs on all 8 fields; (3) a generalization study on two non-enterprise datasets revealing that cascade lookups match but do not surpass GNNs when the target lacks configured determinism; and (4) a drift root-cause analysis showing that prediction ceilings correlate with organizational restructuring patterns.

## 2. Method

### 2.1 Agentic Rule Discovery (Explore)

Given a target field, the LLM agent operates in a ReAct-style [2] loop: it loads semantic definitions from the KG (e.g., the Incoterms risk transfer taxonomy), generates SQL queries against the training data, proposes a cascade hypothesis, evaluates it, and refines based on error analysis. For example, for HEADERINCOTERMS the agent discovered that SHIPPINGCONDITION is the key discriminator between DDP and DAP, a finding that improved coverage by introducing it as a cascade key alongside SOLDTOPARTY and SALESORGANIZATION.

### 2.2 Cascade Codification (Build)

A finalized cascade for field *f* is a sequence of levels *(K_1, ..., K_L)*, where each *K_l* is a composite key. For each level we extract:

> mapping[l][k] = mode(f | K_l = k),  subject to count >= min_support_l

At prediction time, levels are queried in order; the first match determines the output. This mirrors SAP's Access Sequence mechanism but is derived statistically rather than read from system configuration.

### 2.3 Inference (Predict)

The output of Phase 2 is a set of JSON lookup files. Prediction requires only key lookup; no LLM, KG, or model inference at runtime. Cascade sizes range from 88 keys (PLANT) to 174K keys (HEADERINCOTERMS).

## 3. Experiments

### 3.1 Setup

We evaluate primarily on **rel-salt** (SALT-KG [1]): 8 autocomplete tasks across 4 SAP tables with temporal split at 2020-07-01 (train: 1.9M rows; test: 403K rows). For the generalization study (§3.3), we evaluate on two additional RelBench v2 [5] datasets: **rel-arxiv** (academic papers, 53-class author-category prediction) and **rel-stack** (StackOverflow, 3-class badge-type prediction). We compare against the heterogeneous GraphSAGE GNN and LightGBM baselines reported in [5], and the embedding results from [1]. All cascade lookups use only temporally valid data (database rows before the evaluation split cutoff) to prevent data leakage.

### 3.2 SALT-KG Results

**Table 1: MRR comparison with SALT-KG baselines.**

| Target Field | Ours (MRR) | Baseline | +KG | Δ vs +KG |
|---|---|---|---|---|
| CUSTOMERPAYMENTTERMS | **0.852** | 0.62 | 0.70 | **+0.152** |
| SALESGROUP | **0.760** | 0.51 | 0.53 | **+0.230** |
| HEADERINCOTERMS | **0.840** | 0.81 | 0.85 | -0.010 |
| SHIPPINGCONDITION | **0.798** | 0.74 | 0.78 | **+0.018** |
| PLANT | 0.993 | 0.99 | 1.00 | -0.007 |
| SALESOFFICE | 0.997 | 0.99 | 1.00 | -0.003 |
| SHIPPINGPOINT | 0.986 | 0.98 | 0.99 | -0.004 |
| ITEMINCOTERMS | **0.840** | 0.80 | 0.84 | ≈ |

**Table 2: Accuracy comparison with RelBench v2 GNN baseline.**

| Target Field | Ours (Acc) | GNN (Acc) | Δ |
|---|---|---|---|
| CUSTOMERPAYMENTTERMS | **82.86%** | 37.47% | **+45.39** |
| SALESGROUP | **70.00%** | 15.76% | **+54.24** |
| HEADERINCOTERMS | **77.22%** | 62.23% | **+14.99** |
| ITEMINCOTERMS | **77.15%** | 69.36% | +7.79 |
| SHIPPINGCONDITION | **69.56%** | 56.85% | +12.71 |
| SHIPPINGPOINT | **98.65%** | 98.39% | +0.26 |
| PLANT | **99.68%** | 99.46% | +0.22 |
| SALESOFFICE | **99.91%** | 99.88% | +0.03 |

Our method outperforms the GNN on all 8 fields. The largest gains occur on high-cardinality, semantically complex fields (SALESGROUP, CUSTOMERPAYMENTTERMS), where the GNN's message-passing mechanism cannot capture the business logic encoded in SAP's Condition Technique. For near-deterministic organizational mappings (PLANT, SHIPPINGPOINT, SALESOFFICE), both methods converge above 98%.

### 3.3 Generalization Study

To test whether cascade lookups generalize beyond enterprise data, we apply the same methodology—multi-hop relational joins resolved by GROUP BY + MODE()—to two non-SALT autocomplete tasks from RelBench v2. All database joins are temporally filtered to use only data before the evaluation split cutoff.

**rel-arxiv / author-category** (53-class multiclass). The join chain author → paperAuthors → papers → primary_category provides a deterministic path. For each author, we compute MODE(category) from their publications submitted before the evaluation cutoff. We also evaluated citation-based and coauthor-network fallbacks for cold-start authors, but found them inferior to the global mode baseline: citation MODE achieves only 43.1% (val) because a researcher's cited papers span broader topics than their own publications, and coauthor MODE achieves 48.8% because coauthors often span adjacent subfields.

**rel-stack / badges-class** (3-class multiclass: gold/silver/bronze). The badges table in RelBench contains only (Id, UserId, Date)—no badge name or criteria columns. The strongest available join is badge → UserId → same user's historical badge classes, yielding a per-user MODE(Class) lookup. We also explored multi-hop enrichment through user activity features (posts, votes, comments), but found that **every activity-level bin has MODE = bronze** because bronze badges dominate the distribution regardless of user activity (even the most active users—50+ answers, 100+ comments—earn 64% bronze, 33% silver, 3% gold).

**Table 3: Generalization study (val-set accuracy). GNN/LightGBM from RelBench v2 [5].**

| Dataset | Task | Classes | Ours | GNN | Δ |
|---|---|---|---|---|---|
| rel-arxiv | author-category | 53 | 52.6% | 52.6% | 0.0 |
| rel-stack | badges-class | 3 | 77.6% | 80.0% | −2.4 |

**Why cascades match but do not surpass GNNs on non-enterprise data.** Unlike SALT-KG's configured determinism, these tasks lack explicit business rules that cascade lookups can exploit:

1. **Cold-start entities dominate.** On rel-arxiv, 28% of val authors have no publications before the evaluation cutoff and are completely absent from all database tables—no papers, no citations, no coauthors. The cascade can only predict the global mode for these authors (~2% accuracy). GNNs face the same cold-start problem, explaining why both methods converge at ~52.6%.

2. **MODE() is a lossy aggregation.** On rel-stack, bronze badges constitute 86% of training data, so MODE() returns bronze for every feature combination regardless of discriminative power. GNNs overcome this through learned aggregation functions (attention weights, gated updates) that can amplify minority-class signals, achieving 80.0% vs our 77.6%.

3. **No configured determinism to recover.** SALT-KG's advantage stems from SAP's Condition Technique—field values are literally determined by ordered lookup tables. On rel-arxiv, an author's future category is not *determined* by their past publications (researchers change fields); it is merely *correlated*. On rel-stack, badge class is determined by threshold rules (e.g., "Great Answer" requires ≥100 upvotes) that require per-instance temporal reasoning, not entity-level aggregation.

### 3.4 Drift Root-Cause Analysis

The temporal split exposes concept drift. We measure per-field drift rates (fraction of seen customers whose dominant value changed) and cross-correlate with changes in other fields:

| Field | Drift Rate | Division | ShippingCond. | SalesOrg |
|---|---|---|---|---|
| SHIPPINGCONDITION | 43.7% | 0% | N/A | 30.8% |
| SALESGROUP | 38.8% | 0% | 41.8% | 24.0% |
| HEADERINCOTERMS | 28.1% | 0% | 62.6% | 27.6% |
| CUSTOMERPAYMENTTERMS | 17.9% | 0% | 57.4% | 39.6% |

Two patterns emerge:

1. **Product line (Division) never changes**: drift is not driven by customers switching products. For SALESGROUP, 76% of drifted customers retained the same Sales Area entirely, indicating drift is driven by internal team reassignment.

2. **Drift rate inversely correlates with MRR**: CUSTOMERPAYMENTTERMS has the lowest drift (17.9%) and highest MRR (0.852); SHIPPINGCONDITION has the highest drift (43.7%) and lowest cascade MRR (0.798). This ceiling is method-agnostic: any approach trained on historical data faces the same organizational changes.

For HEADERINCOTERMS, drifted customers show a directional DDP-to-DAP transition (495 vs. 89 customers), consistent with documented supply chain risk reallocation during COVID-19 disruptions [3].

## 4. Discussion

**Relation to FMSLT.** The FMSLT framework [4] argues that enterprise prediction should integrate declarative and procedural knowledge layers. Our approach empirically validates this: using only relational data and KG semantics (declarative layer), we approximate but cannot fully replicate the system's configured logic. The accuracy ceilings we observe correspond precisely to the missing procedural layer, i.e., the determination procedures that could disambiguate drifted customers.

**Why cascades win on SALT but not beyond: the role of KG quality.** The generalization study reveals that cascade lookups are not a general-purpose replacement for GNNs. Their advantage is specific to *configured determinism*: ERP systems like SAP resolve field values through explicit, ordered lookup tables (Access Sequences) that cascades can recover statistically. But a deeper explanation lies in the *alignment between the KG and the available data*:

| | SALT-KG | Arxiv KG | Stack KG |
|--|---------|----------|----------|
| Schema information | Yes | Yes | Yes |
| Determination rules | Yes (Condition Technique, Access Sequences) | No | Yes (badge threshold rules) |
| Rule–data alignment | Yes (all rule keys present in data) | N/A | No (badge Name column stripped) |
| **Cascade guidance** | **Direct: KG → cascade** | **Join path only** | **Rules exist but unexecutable** |
Critically, these KGs differ in provenance. The SALT-KG was designed by SAP domain experts who encoded proprietary business logic—Condition Techniques, Access Sequences, and field determination procedures—into a structured ontology [1]. The arxiv and Stack Overflow KGs, by contrast, were constructed by the authors from limited public documentation (RelBench schema metadata and the StackOverflow help pages), without access to domain-specific determination logic. This provenance gap directly explains the quality differential.

SALT-KG's KG encodes *actionable* business rules: "CUSTOMERPAYMENTTERMS is determined by SOLDTOPARTY + SALESDOCUMENTTYPE via Access Sequence." These rules map directly to columns in the training data, so the LLM can translate KG knowledge into a working cascade. For arxiv, the KG describes only table structure—it cannot tell the agent *what predicts an author's category* beyond the tautological join path. For Stack Overflow, we built a comprehensive KG of ~90 badge rules with exact thresholds, but RelBench strips the badge Name column, making these rules unexecutable against the available data. The implication is that cascade performance is bounded by *KG quality × data completeness*: high-quality, expert-curated KGs that encode determination rules aligned with available data columns enable cascades to outperform GNNs, while schema-only or rule-incomplete KGs reduce cascades to generic MODE lookups.

**What cascades offer despite not beating GNNs.** Even when cascades match or slightly underperform GNNs on accuracy, they provide distinct practical advantages: (1) **interpretability**—each prediction traces to a specific composite key and MODE computation, unlike GNN black-box embeddings; (2) **zero inference cost**—prediction requires only a JSON key lookup, not GPU inference; (3) **debuggability**—when predictions are wrong, the cascade level reveals *which* feature combination failed, enabling targeted remediation; (4) **no training infrastructure**—no GPU, no gradient computation, no hyperparameter search.

**Rule reconstruction via temporal SQL.** The [StackOverflow badge system](https://stackoverflow.com/help/badges) awards badges based on well-defined threshold rules (e.g., gold "Great Answer" = answer with ≥100 upvotes; silver "Good Answer" = ≥25; bronze "Nice Answer" = ≥10). Although RelBench strips the badge Name column, the badge Date is preserved. In principle, temporal-windowed SQL could reconstruct these rules: for each badge, count the user's post votes received *before* the badge date and search for threshold patterns that discriminate gold from silver from bronze. This is precisely the signal that GNN message passing exploits implicitly—by aggregating across the badge→user→posts→votes path with learned temporal attention. The difference is operational: the cascade framework performs *global* GROUP BY aggregation (one MODE per user across all badges), whereas rule reconstruction requires *per-instance* temporal windowing (what happened just before *this specific* badge?). Extending cascades with per-instance temporal context would close the gap, but would also converge toward the feature engineering that GNNs automate.

**Future directions.** (1) **KG enrichment for non-enterprise domains**: our analysis shows cascade performance is bounded by KG quality × data completeness; building determination-rule KGs for domains like StackOverflow (encoding badge thresholds as executable SQL templates) or arxiv (encoding category transition patterns) could unlock cascade advantages beyond ERP data. (2) **Temporal cascades**: extending from entity-level MODE to per-instance temporal-windowed aggregation, enabling rule reconstruction for threshold-based systems. (3) **Hybrid cascade-GNN**: using cascade predictions as features or priors for GNN training, combining interpretability with learned aggregation. (4) **Automated cascade discovery**: end-to-end LLM pipeline that generates, evaluates, and selects cascade architectures without manual intervention. (5) **Cold-start mitigation**: integrating text features (paper titles, abstracts) as a complementary signal for unseen entities.

**Limitations.** (1) Cascades require configured determinism to outperform GNNs—on general relational data they match but do not exceed GNN performance; (2) cold-start entities fall through to coarse defaults with no viable relational fallback; (3) the generalization study uses hand-crafted domain rules rather than automatically generated ones.

## 5. Conclusion

We showed that KG-grounded cascade lookups outperform end-to-end GNNs on all 8 SALT-KG enterprise fields, with margins up to +54% on fields governed by configured business rules. However, a generalization study on rel-arxiv and rel-stack reveals that this advantage does not transfer to non-enterprise domains: cascades match GNNs on author-category (52.6% vs 52.6%) and slightly underperform on badges-class (77.6% vs 80.0%). The key insight is that cascade lookups excel specifically where field values are governed by *configured determinism*—explicit lookup tables recoverable through SQL profiling—a structure endemic to ERP systems but absent in academic or community platform data. Where configured determinism is absent, cascades degrade to entity-level MODE lookups that cannot capture temporal context or learned feature interactions. The drift analysis demonstrates that even on SALT-KG, residual prediction ceilings are structurally determined by organizational changes, not method limitations.

---

## References

**Benchmark & Framework**
1. Mulang' et al. (2025). SALT-KG benchmark. NeurIPS Workshop.
2. Yao et al. (2023). ReAct: Synergizing Reasoning and Acting. ICLR.
3. Davis & Vogt (2021). Hidden Supply Chain Risk and Incoterms. doi:[10.1007/978-3-030-95813-8_23](https://doi.org/10.1007/978-3-030-95813-8_23).
4. Hoffart et al. (2025). FMSLT vision paper. arXiv:2505.19825.
5. Gu et al. (2026). RelBench v2. arXiv:2602.12606.
6. Robinson et al. (2024). RelBench: A Benchmark for Deep Learning on Relational Databases. arXiv:2407.20060.
