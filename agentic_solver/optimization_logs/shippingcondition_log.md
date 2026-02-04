# SHIPPINGCONDITION Optimization Log

## Overview
- **Target Field**: SHIPPINGCONDITION
- **Primary Keys**: (SOLDTOPARTY, SALESDOCUMENTTYPE, SHIPPINGPOINT)
- **Strategy**: 7-level composite lookup

## Current Performance
| Metric | Value |
|--------|-------|
| Accuracy | 69.65% |
| MRR (Top-1) | ≥0.6965 |
| Baseline (mode) | 35.50% |
| Paper Baseline MRR | 0.74 |
| Improvement | +34.15pp |

## Script Location
- `agentic_solver/saved_scripts/shippingcondition.py`
- `agentic_solver/saved_scripts/shippingcondition_mapping_v3.json`

---

## Key Discoveries

### 1. Best Single Factors (Accuracy on Train)
| Factor | Accuracy | Unique Values |
|--------|----------|---------------|
| SHIPTOPARTY | 66.36% | 16,115 |
| SOLDTOPARTY | 63.83% | 13,155 |
| SHIPPINGPOINT | 47.38% | 88 |
| SALESDOCUMENTTYPE | 43.88% | 11 |

### 2. Best Composite Keys
| Combination | Accuracy | Coverage |
|-------------|----------|----------|
| (SOLDTO, DT, SP) 3-factor | 71.98% | 90% |
| (SOLDTO, DT) 2-factor | 64.12% | 93% |

### 3. Hardest Case: 98 vs 99
- 41K errors are 98↔99 confusion
- Mostly in ZMUN documents at ORG 0010
- SOLDTOPARTY overlap is 50%+ → hard to distinguish

---

## Optimization History

### Iteration 0 - Initial (2026-02-04 16:07)
- **Accuracy**: 56.90%
- **Strategy**: SHIPPINGPOINT → SALESORG → mode

### Iteration 3 - SOLDTOPARTY (2026-02-04 21:05)
- **Accuracy**: 59.45%
- **Strategy**: SOLDTOPARTY → SHIPPINGPOINT → ORG

### Iteration 4 - Multi-Factor (2026-02-04 21:28)
- **Accuracy**: 69.65%
- **Strategy**: 7-level lookup
  1. (SOLDTO, DT, SP) 3-factor
  2. (SOLDTO, DT)
  3. (SHIPTO, DT)
  4. SHIPTOPARTY
  5. SOLDTOPARTY
  6. DOCTYPE
  7. SHIPPINGPOINT

---
