# SHIPPINGCONDITION Optimization Log

## Overview
- **Target Field**: SHIPPINGCONDITION
- **Primary Keys**: (SOLDTOPARTY, SALESDOCUMENTTYPE, SHIPPINGPOINT)
- **Strategy**: 7-level composite lookup

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.798** |
| SALT Baseline Best | 0.74 |
| SALT-KG Best | 0.78 |

## Script Location
- `agentic_solver/saved_scripts/shippingcondition.py`
- `agentic_solver/saved_scripts/shippingcondition_mapping_simple.json`

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

## Lookup SQL Queries

Final script uses a simplified 2-level strategy:

```sql
-- L1: (SOLDTOPARTY, SALESDOCUMENTTYPE, SHIPPINGPOINT) -> SHIPPINGCONDITION (32,967 keys)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' || "SHIPPINGPOINT" AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition
FROM train
GROUP BY key

-- L2: (SHIPTOPARTY, SALESDOCUMENTTYPE, SHIPPINGPOINT) -> SHIPPINGCONDITION
SELECT "SHIPTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' || "SHIPPINGPOINT" AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition
FROM train
GROUP BY key

-- Global mode (fallback)
SELECT MODE("SHIPPINGCONDITION") FROM train
```

### Sample Results (L1: top 10 by frequency)

| Key (SOLDTO\|DT\|SP) | SC | Rows | % |
|-----------------------|------|------|---|
| 3143487067\|ZMUT\|MUST | 95 | 25,676 | 1.3% |
| 6726809660\|ZMUN\|MUST | 95 | 17,790 | 0.9% |
| 9458338227\|ZMUN\|MUST | 98 | 9,837 | 0.5% |
| 3356660324\|TA\|0001 | 01 | 9,165 | 0.5% |
| 2635055107\|ZMUN\|MUST | 98 | 8,846 | 0.5% |
| 6700514882\|ZMUN\|MUST | 95 | 7,953 | 0.4% |
| 0851548071\|TA\|0001 | 05 | 7,533 | 0.4% |
| 0212677443\|ZMUN\|0702 | 99 | 7,308 | 0.4% |
| 7481075268\|ZMUN\|MUST | 99 | 7,281 | 0.4% |
| 6259385027\|ZMUN\|MUST | 99 | 7,160 | 0.4% |

> ZMUN/ZMUT (virtual orders) with SHIPPINGPOINT=MUST typically get SC=95/98/99. Physical orders (TA) with real shipping points get SC=01/05.
