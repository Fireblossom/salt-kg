# SALT-KG

[![Made with Python](https://img.shields.io/badge/Made%20with-Python-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-CC--BY--NC--SA--4.0-green)](licence)
[![OpenReview](https://img.shields.io/badge/OpenReview-Paper-blue)](https://openreview.net/forum?id=9vVMSvilGX)

> **Research Extension**: This repository extends the [SALT-KG benchmark](https://github.com/SAP-samples/salt-kg) with an **Agentic Scripting Solver** that achieves competitive results using "Code as Reasoning" instead of traditional ML approaches.

## Agentic Scripting Solver

I developed a novel prediction approach that uses **LLM-generated Python scripts grounded in business rules** instead of embedding-based similarity matching. This approach:
- **Achieves competitive results with paper benchmarks**
- Shows how interpretable rule-based methods can **complement** embedding approaches
- Provides **fully interpretable and editable** prediction logic

### Results: MRR Comparison

| Target Field | Mine | SALT Baseline Best | SALT-KG Best | vs Baseline | vs SALT-KG |
|--------------|------|---------------|--------------|-------------|------------|
| SALESOFFICE | **0.997** | 0.99 | 1.00 | +0.007 | ≈ |
| PLANT | **0.993** | 0.99 | 1.00 | +0.003 | ≈ |
| SHIPPINGPOINT | **0.986** | 0.98 | 0.99 | +0.006 | ≈ |
| CUSTOMERPAYMENTTERMS | **0.852** | 0.62 | 0.70 | **+0.232** | **+0.152** |
| SALESGROUP | **0.760** | 0.51 | 0.53 | **+0.250** | **+0.230** |
| HEADERINCOTERMS | **0.840** | 0.81 | 0.85 | +0.030 | ≈ |
| ITEMINCOTERMS | **0.840** | 0.80 | 0.84 | +0.040 | ≈ |
| SHIPPINGCONDITION | **0.798** | 0.74 | 0.78 | +0.058 | **+0.018** |

> **Baseline Best**: Best model from Table 2 (without KG)  
> **SALT-KG Best**: Baseline + KG enhancement from Table 1  
> **Note**: Results are comparable within margin; SALT-KG embeddings likely provide additional value for cold-start scenarios.

### Accuracy Comparison

[RelBench v2](https://arxiv.org/abs/2602.12606) (Gu et al., 2026) adopted SALT as an official benchmark dataset and introduced **autocomplete tasks**, a new task type directly inspired by SALT's sales order completion use case. Their end-to-end GNN (heterogeneous GraphSAGE) was evaluated on all 8 target fields. Below we compare test Accuracy under the same metric:

| Target Field | Mine (Accuracy) | RelBench v2 GNN (Accuracy) |
|---|---|---|
| PLANT | **99.68%** | 99.46% |
| SHIPPINGPOINT | **98.65%** | 98.39% |
| SALESOFFICE | **99.91%** | 99.88% |
| HEADERINCOTERMS | **77.22%** | 62.23% |
| ITEMINCOTERMS | **77.15%** | 69.36% |
| SHIPPINGCONDITION | **69.56%** | 56.85% |
| CUSTOMERPAYMENTTERMS | **82.86%** | 37.47% |
| SALESGROUP | **70.00%** | 15.76% |

> **Takeaway**: The Agentic Solver outperforms the end-to-end GNN on **all 8 fields**. GNNs approach parity on structurally deterministic fields (Plant, ShippingPoint, SalesOffice), but on high-cardinality fields requiring business semantics (SalesGroup: 70% vs 16%, PaymentTerms: 83% vs 37%), the gap is dramatic. The two approaches are complementary: GNNs for structural inference, rule-based methods for semantic reasoning.

### Methodology: Code as Reasoning

Instead of embedding-based similarity matching, I use:
1. **Statistical profiling**: Find the mode (most frequent value) per feature combination
2. **Hierarchical fallback**: When specific lookup misses, fall back to broader patterns
3. **Business rule discovery**: Identify deterministic relationships (e.g., `SHIPPINGCONDITION>=94` signals virtual ShippingPoint)

**Why this works**: SAP ERP has strong configuration-driven determinism. Many fields are master data relationships (not truly "predictive"), and transactional patterns follow business process rules.

### Key Insights Discovered

1. **SALESOFFICE class imbalance**: 99.91% of test data is value `0010`, making any method appear ~100% accurate
2. **SHIPPINGCONDITION >=94**: Indicates virtual/non-physical shipping points
3. **Incoterms cascade**: Hierarchical fallback (SOLDTO, SHIPTO, ORG) improves coverage

### Role of the Knowledge Graph

The KG plays an **indirect** role. It provides schema-level semantic context (e.g., "DDP = Delivered Duty Paid", Incoterms risk transfer rules) that helps the LLM understand SAP domain concepts during initial script generation. However, the KG does not contain instance-level mappings (e.g., "Customer X always uses payment term 32").

The final prediction performance comes from **statistical lookup tables** extracted from training data via DuckDB SQL analysis, not from KG entity relationships. Once scripts are optimized and saved, the KG is no longer involved at prediction time.

```
KG (semantic context) -> LLM generates initial script -> DuckDB SQL analysis
-> iterative improvement -> saved_scripts/ (KG no longer needed)
```

---

## Workflow

```
Phase 1: EXPLORE                Phase 2: BUILD              Phase 3: PREDICT
(discover rules via LLM+SQL)    (codify into lookups)       (apply at inference)

demo.py --improve               build_mappings.py           predictor.py
  |-- script_improver.py           |                           |-- saved_scripts/*.py
  |-- duckdb_analyzer.py           |                           \-- saved_scripts/*.json
  \-- kg_loader.py                 |
         |                         |                                   |
         v                         v                                   v
  "SOLDTO x DT x ORG x SC     *_mapping.json                   predictions on
   is a good cascade"          (lookup tables)                  new test data
```

### Phase 1: Explore (LLM-driven discovery)

```bash
python demo.py --improve --target CUSTOMERPAYMENTTERMS --provider anthropic
```

The LLM writes SQL queries via `duckdb_analyzer.py` to discover data patterns (e.g., "SHIPPINGCONDITION is the key discriminator for Incoterms"). The KG provides semantic context (e.g., "DDP = Delivered Duty Paid", Incoterms risk transfer rules), but does not contain instance-level mappings. Results are logged in `optimization_logs/`.

### Phase 2: Build (codify discoveries into lookup tables)

```bash
python agentic_solver/build_mappings.py
```

Once cascade strategies are finalized, this script reads training data and generates all lookup JSON files in one step (~2 seconds via DuckDB). The cascade configurations inside this script are the **codified result** of Phase 1 exploration.

| Output File | Field | Levels |
|---|---|---|
| `customerpaymentterms_mapping.json` | CUSTOMERPAYMENTTERMS | 4 |
| `salesgroup_mapping.json` | SALESGROUP | 6 |
| `headerincotermsclassification_mapping.json` | HEADERINCOTERMSCLASSIFICATION | 9 |
| `itemincotermsclassification_mapping.json` | ITEMINCOTERMSCLASSIFICATION | 9 |
| `shippingcondition_mapping_simple.json` | SHIPPINGCONDITION | 7 |

### Phase 3: Predict (apply at inference time)

```bash
python demo.py  # runs saved scripts on test data
```

Each `saved_scripts/*.py` loads its `*_mapping.json` and applies the cascade lookup. No LLM or KG needed at this stage.

> **Note:** Phase 1 to Phase 2 is a manual step: you read the exploration logs and encode the best cascade strategy into `build_mappings.py`. Fully automating this bridge is a potential future improvement.

---

## Project Structure

```
salt-kg/
|-- agentic_solver/
|   |  Phase 1: Explore
|   |-- script_generator.py      # LLM-based script generation
|   |-- script_improver.py       # Iterative improvement agent
|   |-- duckdb_analyzer.py       # SQL-based pattern analysis
|   |-- kg_loader.py             # Knowledge Graph context loader
|   |-- script_executor.py       # Safe script execution sandbox
|   |  Phase 2: Build
|   |-- build_mappings.py        # One-step mapping builder (all fields)
|   |  Phase 3: Predict
|   |-- predictor.py             # Main predictor class (sklearn-like API)
|   |-- saved_scripts/           # Prediction functions + lookup tables (JSON)
|   |  Documentation
|   \-- optimization_logs/       # Per-field analysis logs with SQL queries & results
|-- data/
|   |-- salt/                    # Tabular data (parquet)
|   \-- salt-kg/                 # Knowledge Graph metadata (JSON)
|-- demo.py                      # Entry point (explore / predict)
\-- requirements.txt
```

---

## Limitations and Future Work

### Current Limitations

- **Cold start problem**: Prediction requires seeing a customer/combination in training data. Truly new customers fall through to organization-level defaults.
- **Concept drift**: SALT-KG uses a temporal train/test split at **2020-07-01** (train: 2018-01-02 to 2020-06-30, 1.9M rows; test: 2020-07-01 to 2020-12-31, 403K rows). This mirrors real-world deployment where models are trained on historical data, but it also exposes concept drift: customers change payment terms, organizations restructure sales groups, and trade agreements shift Incoterms preferences over time. My analysis found that 38% of seen customers changed their dominant SALESGROUP between the two periods, capping accuracy at ~70% regardless of cascade design. A random split would mask this problem and overestimate real-world performance.
- **Statistical discovery, not causal understanding**: Business rules are reverse-engineered from transaction patterns via SQL analysis, not read from source logic. This means I discover *what* the system does, but not *why*.

### Connection to FMSLT

The [Foundation Models for Semantically Linked Tables (FMSLT)](https://arxiv.org/abs/2505.19825) vision paper (Hoffart et al., 2025) proposes that enterprise table prediction should integrate three knowledge layers beyond raw relational data:

| SLT Layer | What SALT-KG Provides | What Is Missing |
|---|---|---|
| **Relational Data** | Full | -- |
| **Declarative Knowledge** (semantic) | Rich | Field definitions + business rule semantics (e.g., Incoterms risk transfer rules, Sales Area structure). Missing: instance-level determination rules |
| **Declarative Knowledge** (rules) | Missing | SAP Condition Tables, Access Sequences |
| **Procedural Knowledge** (code) | Missing | ABAP determination logic, validation scripts |
| **World Knowledge** | Implicit | LLM provides general domain knowledge; coverage and accuracy are unverifiable |

My Agentic Scripting Solver **inadvertently performs a subset of the FMSLT vision**: I use LLM world knowledge + KG semantics to generate initial scripts (world + declarative layers), then use DuckDB SQL auditing to *reverse-engineer* hidden business rules from transaction data (a statistical proxy for the missing procedural layer). My cascade lookups effectively *simulate* SAP's Condition Technique, but through frequency analysis rather than direct code comprehension.

### Roadmap

To close the gap between what SALT-KG provides and what FMSLT proposes, future work could:

1. **Add Condition Records**: Include SAP determination procedure configurations for each target field, enabling direct rule application instead of statistical mode lookups
2. **Include Master Data snapshots**: Customer master records (KNA1/KNVV) and material masters (MARA/MARC) would eliminate the need to infer customer-level defaults from transaction patterns
3. **Embed procedural logic**: Excerpts of ABAP validation/determination code would allow LLMs to reason causally about field values (e.g., "SHIPPINGCONDITION ≥ 94 triggers virtual shipping") rather than discovering these rules through SQL auditing
4. **Temporal-aware cascades**: Incorporate recency weighting or time-windowed lookups to handle concept drift, since the current mode-based approach treats all training data equally regardless of age

# Original SALT-KG Dataset

This repository is based on the **SALT-KG benchmark** from SAP Research, presented at EeurIPS'25 Workshop.

## Abstract

Building upon the SALT benchmark for relational prediction, SALT-KG extends SALT by linking its multi-table transactional data with a structured Operational Business Knowledge represented in a Metadata Knowledge Graph (OBKG) that captures field-level descriptions, relational dependencies, and business object-types.

## Dataset Overview

- 4 relational tables with transactional data
- Metadata Knowledge Graph (OBKG) with field-level descriptions
- Train/validation/test splits (1.9M / 402K rows)

## Authors (Original SALT-KG)

- [Isaiah Onando Mulang'](https://www.linkedin.com/in/mulang-onando-phd-31a16ab1/)
- [Felix Sasaki](https://www.linkedin.com/in/felixsasaki/)
- [Tassilo Klein](https://tjklein.github.io/)
- [Jonas Kolk](https://www.linkedin.com/in/jonas-kolk-b8a94b123/)
- [Nikolay Grechanov](https://www.linkedin.com/in/grechanov/)
- [Johannes Hoffart](https://www.linkedin.com/in/johanneshoffart/)

## Citations

```bibtex
@inproceedings{mulang2025saltkg,
  title={SALT-KG: A Benchmark for Semantics-Aware Learning on Enterprise Tables},
  author={Mulang', Isaiah Onando and Sasaki, Felix and Klein, Tassilo and Kolk, Jonas and Grechanov, Nikolay and Hoffart, Johannes},
  booktitle={Proceedings of the NeurIPS 2025 Table Representation Learning Workshop},
  year={2025}
}
```

## License

Copyright (c) 2025 SAP SE or an SAP affiliate company. All rights reserved. This project is licensed under CC-BY-NC-SA-4.0.
