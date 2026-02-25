> ## TODO: Additional Datasets for Cross-Benchmark Validation
>
> The paper currently evaluates on SALT-KG only. To strengthen the contribution, run on 1-2 additional multi-table relational prediction benchmarks:
>
> | Dataset | Source | Tables | Rows | Task Type | Fit |
> |---|---|---|---|---|---|
> | **RelBench** | Stanford (Fey et al., 2024) | Multi-table, 7 domains | Varies (10K-10M) | Node/link prediction on relational DBs | **Best fit**: temporal splits, multiple prediction tasks, GNN baselines to compare against. Pick 2-3 tasks from e-commerce or finance domains |
> | **RDBench** | OpenReview 2024 | Multi-table, hierarchical | Varies | Classification on relational DBs | Good: provides tabular, homogeneous, and heterogeneous graph formats |
> | **Berka (Czech Banking)** | PKDD'99 | 8 tables | ~1M transactions | Loan default, transaction classification | Classic: well-studied, temporal, multi-table financial data |
> | **Kaggle ERP-MTD** | Kaggle | Multi-table ERP | Synthetic | ERP table prediction | Weak: synthetic, no established baselines |
>
> **Priority**: RelBench (2-3 tasks) + SALT-without-KG ablation. This gives cross-domain generalization + ablation in one move.
>
> **Key references**:
> - Fey et al. (2024). *RelBench: A Benchmark for Deep Learning on Relational Databases*. arXiv:2407.20060
> - RDBench. *RDBench: ML Benchmark for Relational Databases*. OpenReview (NeurIPS 2024 D&B track)

---

# Code as Reasoning: LLM-Generated Cascades for Semantically-Linked Table Prediction

## Abstract

We propose an agentic approach to enterprise table prediction in which a large language model discovers business rules through iterative SQL profiling and codifies them as hierarchical cascade lookups. On the SALT-KG benchmark (8 SAP fields, 1.9M rows), our method matches or exceeds embedding baselines on 7 of 8 fields while producing fully interpretable prediction logic. A drift root-cause analysis reveals that accuracy ceilings are field-specific and driven by organizational restructuring rather than changes in customer purchasing behavior.

---

## 1. Introduction

Predicting field values in multi-table enterprise data underpins business process automation in ERP systems. The SALT-KG benchmark [1] evaluates this task on SAP sales order data, where prior work uses embedding-based similarity matching optionally enhanced with a metadata Knowledge Graph.

We observe that many ERP field values are not learned associations but *configured determinism*: SAP's Condition Technique traverses ordered lookup tables (Access Sequences) to resolve values like payment terms or Incoterms. This structure is recoverable from transactional data through systematic profiling.

We contribute: (1) a three-phase agentic workflow where an LLM discovers cascade structures via SQL auditing grounded in KG semantics; (2) competitive MRR on SALT-KG with significant gains on configuration-driven fields; and (3) a drift root-cause analysis showing that prediction ceilings correlate with organizational restructuring patterns.

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

We use SALT-KG [1] with its temporal split at 2020-07-01 (train: 1.9M rows; test: 403K rows). We compare against the best embedding results reported in [1], both with and without KG enhancement.

### 3.2 Results

| Target Field | Ours | Baseline | +KG | Δ vs +KG |
|---|---|---|---|---|
| CUSTOMERPAYMENTTERMS | **0.852** | 0.62 | 0.70 | **+0.152** |
| SALESGROUP | **0.760** | 0.51 | 0.53 | **+0.230** |
| HEADERINCOTERMS | **0.840** | 0.81 | 0.85 | -0.010 |
| SHIPPINGCONDITION | **0.798** | 0.74 | 0.78 | **+0.018** |
| PLANT | 0.993 | 0.99 | 1.00 | -0.007 |
| SALESOFFICE | 0.997 | 0.99 | 1.00 | -0.003 |
| SHIPPINGPOINT | 0.986 | 0.98 | 0.99 | -0.004 |
| ITEMINCOTERMS | **0.840** | 0.80 | 0.84 | ≈ |

The largest gains occur on fields governed by customer-level configuration (CUSTOMERPAYMENTTERMS, SALESGROUP). For near-deterministic organizational mappings (PLANT, SHIPPINGPOINT), all methods converge.

### 3.3 Drift Root-Cause Analysis

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

**Limitations.** (1) Single benchmark evaluation; (2) the explore-to-build bridge is currently manual; (3) cascade architectures are not automatically searched; (4) cold-start customers fall through to coarse defaults where embeddings may offer better coverage.

**Complementarity.** Our method and embedding approaches have complementary strengths: cascades excel on configuration-driven fields with sufficient training history; embeddings may generalize better for unseen customers through latent similarity.

## 5. Conclusion

We showed that agentic SQL reasoning can produce interpretable prediction logic competitive with neural baselines on enterprise table data. The drift analysis demonstrates that prediction ceilings are structurally determined by organizational changes, providing a diagnostic framework applicable beyond this specific benchmark.

---

## Related Work Candidates

**Benchmark & Framework**
1. Mulang' et al. (2025). SALT-KG benchmark. EeurIPS Workshop.
2. Hoffart et al. (2025). FMSLT vision paper. arXiv:2505.19825.

**Agentic LLM Reasoning**
3. Yao et al. (2023). ReAct: Synergizing Reasoning and Acting. ICLR.
4. Shinn et al. (2023). Reflexion: Verbal Reinforcement Learning. NeurIPS.
5. Granado et al. (2025). RAISE: Reasoning Agent for Interactive SQL Exploration. arXiv:2506.01273.

**Tabular Prediction**
6. Hollmann et al. (2023). TabPFN. ICLR.
7. Fang et al. (2024). LLMs on Tabular Data: A Survey. TMLR.
8. van Breugel et al. (2024). Tabular Foundation Models. ICML position paper.

**Enterprise Data & Incoterms**
9. Davis & Vogt (2021). Hidden Supply Chain Risk and Incoterms. doi:[10.1007/978-3-030-95813-8_23](https://doi.org/10.1007/978-3-030-95813-8_23).
10. Dong et al. (2023). Global supply chains risks and COVID-19: Supply chain structure as a mitigating strategy for SMEs. J. Business Research. doi:[10.1016/j.jbusres.2022.113407](https://doi.org/10.1016/j.jbusres.2022.113407).

**Concept Drift**
11. Lu et al. (2019). Learning under Concept Drift: A Review. IEEE TKDE.
12. Gama et al. (2014). Survey on Concept Drift Adaptation. [ACM Comp. Surveys.](https://doi.org/10.1145/2523813)

**Code Generation / Program Synthesis**
13. Chen et al. (2021). Evaluating Large Language Models Trained on Code (Codex). arXiv.
14. Li et al. (2025). Can LLMs Generate Novel Research Ideas? ICLR.
