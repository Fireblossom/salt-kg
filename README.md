# Agentic Cascade Solver for Enterprise Field Prediction

This repository contains the complete implementation of an **Agentic Cascade Solver** that uses LLM-guided SQL profiling, grounded in Knowledge Graph semantics, to discover deterministic field-prediction rules and codify them as lightweight JSON cascade lookups. The system achieves state-of-the-art results on the SALT-KG benchmark (8 SAP fields) and includes generalization experiments on two public RelBench v2 datasets (rel-arxiv, rel-stack).

## Results

### Accuracy Comparison (SALT-KG)

| Target Field | Cascade (Ours) | GNN (RelBench v2) |
|---|---|---|
| CustomerPaymentTerms | **82.86%** | 37.47% |
| SalesGroup | **70.00%** | 15.76% |
| HeaderIncoterms | **77.22%** | 62.23% |
| ItemIncoterms | **77.15%** | 69.36% |
| ShippingCondition | **69.56%** | 56.85% |
| ShippingPoint | **98.65%** | 98.39% |
| Plant | **99.68%** | 99.46% |
| SalesOffice | **99.91%** | 99.88% |

### MRR Comparison (SALT-KG)

| Target Field | Cascade (Ours) | SALT Baseline Best | SALT-KG Best (w/ KG) |
|---|---|---|---|
| CustomerPaymentTerms | **0.852** | 0.62 | 0.65 |
| SalesGroup | **0.760** | 0.51 | 0.51 |
| HeaderIncoterms | **0.840** | 0.81 | 0.81 |
| ItemIncoterms | **0.840** | 0.80 | 0.80 |
| ShippingCondition | **0.798** | 0.74 | 0.78 |
| ShippingPoint | **0.986** | 0.98 | 0.98 |
| Plant | **0.993** | 0.99 | 0.99 |
| SalesOffice | **0.997** | 0.99 | 1.00 |

### Generalization Study (RelBench v2)

| Dataset | Task | Cascade (Test) | GNN (Test) |
|---|---|---|---|
| rel-arxiv | author-category (53-class) | 50.3% | 50.7% |
| rel-stack | badges-class (3-class) | 79.3% | 82.8% |

---

## Method Overview

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

**Phase 1 (Explore):** An LLM agent, guided by KG-provided semantic descriptions of each target field, iteratively proposes candidate composite keys, profiles them via `GROUP BY` / `MODE` SQL queries against training data, and evaluates candidates on a validation split.

**Phase 2 (Build):** Finalized cascade strategies are codified into deterministic JSON lookup tables via `build_mappings.py` (~2 seconds via DuckDB).

**Phase 3 (Predict):** Each `saved_scripts/*.py` loads its `*_mapping.json` and applies cascade lookup. No LLM or KG needed at inference time.

---

## Repository Structure

```
salt-kg/
|-- agentic_solver/
|   |  Phase 1: Explore
|   |-- script_generator.py      # LLM-based script generation (includes all prompts)
|   |-- script_improver.py       # Iterative improvement agent
|   |-- duckdb_analyzer.py       # SQL-based pattern analysis
|   |-- kg_loader.py             # Knowledge Graph context loader
|   |-- script_executor.py       # Safe script execution sandbox
|   |  Phase 2: Build
|   |-- build_mappings.py        # One-step mapping builder (all fields)
|   |  Phase 3: Predict
|   |-- predictor.py             # Main predictor class
|   |-- saved_scripts/           # Prediction functions + lookup tables (JSON)
|   |  Documentation
|   \-- optimization_logs/       # Per-field analysis logs with SQL queries & results
|-- addition_experiments/
|   |-- build_mappings.py        # rel-arxiv and rel-stack cascade builders
|   |-- saved_scripts/           # Saved scripts for generalization experiments
|   \-- data/                    # Public dataset processing
|-- data/
|   |-- salt/                    # Tabular data (parquet, requires SALT-KG access)
|   \-- salt-kg/                 # Knowledge Graph metadata (JSON)
|-- demo.py                      # Entry point (explore / predict)
\-- requirements.txt
```

---

## Reproducibility

### Prerequisites

```bash
pip install -r requirements.txt
```

### Replicating SALT-KG Results (without LLM access)

The finalized cascade JSON files are included in `agentic_solver/saved_scripts/`. To reproduce reported accuracy numbers:

```bash
python demo.py
```

This runs saved cascade lookups against the test set — no LLM API key is required.

### Running Rule Discovery (Phase 1)

To re-run the LLM-guided discovery process:

```bash
python demo.py --improve --target CUSTOMERPAYMENTTERMS --provider anthropic
```

This requires an Anthropic or OpenAI API key set in environment variables.

### Building Mappings from Scratch (Phase 2)

```bash
python agentic_solver/build_mappings.py
```

Regenerates all JSON lookup tables from training data (~2 seconds).

### Generalization Experiments

The `addition_experiments/` directory contains scripts for rel-arxiv and rel-stack evaluations using only public RelBench v2 data.

---

## Key Artifacts

| Artifact | Path | Description |
|---|---|---|
| LLM Prompts | `agentic_solver/script_generator.py` | All system and user prompts used during discovery |
| Cascade JSONs | `agentic_solver/saved_scripts/*.json` | Finalized lookup tables for all 8 fields |
| Prediction Scripts | `agentic_solver/saved_scripts/*.py` | Deterministic prediction functions |
| Optimization Logs | `agentic_solver/optimization_logs/` | Full agent traces and SQL query logs |
| KG Descriptions | `data/salt-kg/` | Knowledge Graph metadata used as semantic context |

---

## Data Availability

- **SALT-KG tabular data**: See the [SALT-KG benchmark](https://github.com/SAP-samples/salt-kg).
- **rel-arxiv and rel-stack**: Public datasets available through [RelBench v2](https://relbench.stanford.edu/).