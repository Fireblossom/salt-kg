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

| Target Field | Ours | SALT Baseline Best | SALT-KG Best | vs Baseline | vs SALT-KG |
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

### Methodology: Code as Reasoning

Instead of embedding-based similarity matching, I use:
1. **Statistical profiling**: Find the mode (most frequent value) per feature combination
2. **Hierarchical fallback**: When specific lookup misses, fall back to broader patterns  
3. **Business rule discovery**: Identify deterministic relationships (e.g., `SHIPPINGCONDITION≥94 → virtual ShippingPoint`)

**Why This Works**:
- SAP ERP has strong configuration-driven determinism
- Many fields are master data relationships (not truly "predictive")
- Transactional patterns follow business process rules

### Key Insights Discovered

1. **SALESOFFICE class imbalance**: 99.91% of test data is value `0010`, making any method appear ~100% accurate
2. **SHIPPINGCONDITION ≥94**: Indicates virtual/non-physical shipping points
3. **Incoterms cascade**: Hierarchical fallback (SOLDTO → SHIPTO → ORG) improves coverage

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo (uses mock LLM - no API key needed)
python demo.py

# With real LLM
python demo.py --provider anthropic  # requires ANTHROPIC_API_KEY

# Run script improvement with SQL analysis
python demo.py --improve --target CUSTOMERPAYMENTTERMS --provider anthropic
```

**Example output:**
```
PREDICTING: SALESGROUP
Generating prediction script...
Generated Code:
  def predict(row):
      return lookup_table.get((row['SOLDTOPARTY'], row['SALESDOCUMENTTYPE']))
Accuracy: 76.0%
```

---

## Script Improvement Workflow

The `--improve` flag runs an iterative improvement loop using **DuckDB for SQL-based pattern analysis**:

```
┌──────────────────────────────────────────────────────────┐
│  1. evaluate_script()                                    │
│     Load saved script, run on validation set             │
├──────────────────────────────────────────────────────────┤
│  2. analyze_patterns_with_sql()  [DuckDB]                │
│     LLM generates SQL → DuckDB executes → pattern stats  │
├──────────────────────────────────────────────────────────┤
│  3. analyze_errors() + improve_script()                  │
│     LLM analyzes errors + SQL insights → generates fix   │
├──────────────────────────────────────────────────────────┤
│  4. Test & Save if accuracy improves                     │
└──────────────────────────────────────────────────────────┘
```

**Key files:**
- `duckdb_analyzer.py` - SQL-based data analysis with DuckDB
- `script_improver.py` - Iterative improvement agent

---

## Project Structure

```
salt-kg/
├── agentic_solver/          # Agentic Scripting Solver
│   ├── predictor.py         # Main predictor class
│   ├── script_generator.py  # LLM-based script generation
│   ├── script_improver.py   # Iterative improvement agent
│   ├── duckdb_analyzer.py   # SQL-based pattern analysis
│   ├── kg_loader.py         # Knowledge Graph loader
│   └── saved_scripts/       # Generated prediction scripts & lookup tables
├── data/                    # SALT-KG dataset
│   ├── salt/                # Tabular data (parquet)
│   └── salt-kg/             # Knowledge Graph metadata
├── demo.py                  # Interactive demo (--improve flag for SQL workflow)
└── requirements.txt
```

---

## Limitations

- Requires seeing specific customer/combination in training data
- Cannot generalize to truly new customers (cold start problem)
- Paper's KG+Embedding approach may better handle novel entity relationships

---

# Original SALT-KG Dataset

This repository is based on the **SALT-KG benchmark** from SAP Research, presented at NeurIPS'25 Table Representation Workshop.

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
