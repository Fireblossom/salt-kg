# SHIPPINGPOINT Optimization Log

## Overview
- **Target Field**: SHIPPINGPOINT
- **Primary Keys**: PLANT + SHIPPINGCONDITION + SALESDOCUMENTTYPE
- **Strategy**: Multi-factor composite lookup

## Current Performance
| Metric | Value |
|--------|-------|
| Accuracy | 98.65% |
| MRR (Top-1) | ≥0.9865 |
| Baseline (mode) | 43.40% |
| Paper Baseline MRR | 0.97 |
| Improvement | +55.25pp |

## Script Location
- `agentic_solver/saved_scripts/shippingpoint.py`
- `agentic_solver/saved_scripts/shippingpoint_mapping_v2.json`

---

## Key Discoveries

### 1. SHIPPINGCONDITION is the Critical Discriminator
| SHIPPINGCONDITION | SHIPPINGPOINT Type |
|-------------------|-------------------|
| 01-42 (low) | Base values (0001, 0300, 0700...) |
| 18-20 | Special variants (0301, 1301, 1302...) |
| 94-99 (high) | "02" suffix (0302, 0702, MUST...) |

### 2. SALESDOCUMENTTYPE Correlation
| DOCTYPE | Shipping Type |
|---------|--------------|
| TA, ZIA | Physical shipping |
| ZMUN, ZMUT | Virtual/Service (→ 02 suffix or MUST) |

### 3. PLANT 0001 Special Case
- `SC<94 + DOCTYPE=TA` → **0001**
- `SC>=94 or DOCTYPE=ZMUN` → **MUST**

---

## Optimization History

### Iteration 0 - Initial Script (2026-02-04 16:07)
- **Accuracy**: 75.90%
- **Strategy**: SALESORGANIZATION lookup → PLANT fallback → mode

### Iteration 1 - Multi-Factor Lookup (2026-02-04 21:02)
- **Accuracy**: 98.10%
- **Strategy**: (PLANT, is_service) composite key
- **Key change**: Added SHIPPINGCONDITION >=94 and SALESDOCUMENTTYPE check

### Iteration 2 - SC=18 Special Handling (2026-02-04 21:04)
- **Accuracy**: 98.65%
- **Strategy**: Added SC=18 specific lookup for variant cases (0301, 1302...)
- **Remaining errors**: 5,456 (rare values, edge cases)

---
