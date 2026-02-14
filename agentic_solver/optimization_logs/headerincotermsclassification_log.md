# HEADERINCOTERMSCLASSIFICATION Optimization Log

## Overview
- **Target Field**: HEADERINCOTERMSCLASSIFICATION
- **Primary Key**: SOLDTOPARTY
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.840** |
| SALT Baseline Best | 0.81 |
| SALT-KG Best | 0.85 |

## Script Location
- `agentic_solver/saved_scripts/headerincotermsclassification.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 77.00%
- **Strategy**: SOLDTOPARTY lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

5-level cascade: (SOLDTO+DT+ORG+SC) > (SOLDTO+DT+ORG) > (SOLDTO+DT) > SOLDTO > ORG

```sql
-- L0: 4-factor (SOLDTOPARTY, DOCTYPE, ORG, SHIPPINGCONDITION) - most specific (46,754 keys)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" || '|' || "SHIPPINGCONDITION" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L1: 3-factor (SOLDTOPARTY, DOCTYPE, ORG)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L2: 2-factor (SOLDTOPARTY, DOCTYPE)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L3: SOLDTOPARTY only
SELECT "SOLDTOPARTY",
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY "SOLDTOPARTY"

-- L4: SALESORGANIZATION only (31 keys)
SELECT "SALESORGANIZATION",
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("HEADERINCOTERMSCLASSIFICATION") FROM train
```

### Sample Results (L0: top 10 by frequency)

| Key (SOLDTO\|DT\|ORG\|SC) | Incoterms | Rows |
|----------------------------|-----------|------|
| 3143487067\|ZMUT\|0010\|95 | EXW | 25,676 |
| 6726809660\|ZMUN\|0010\|95 | FCA | 12,400 |
| 3356660324\|TA\|0010\|01 | CIP | 9,161 |
| 0851548071\|TA\|0010\|05 | FCA | 7,366 |
| 9458338227\|ZMUN\|0010\|98 | DDP | 6,306 |
| 4290077062\|ZMUT\|0010\|95 | EXW | 5,972 |
| 2635055107\|ZMUN\|0010\|98 | DDP | 5,590 |
| 7528327689\|ZMUN\|0010\|98 | DDP | 5,511 |
| 5389539235\|ZIA\|4200\|13 | DDP | 5,263 |
| 1490599991\|ZMUN\|0010\|98 | DDP | 4,831 |

### Sample Results (L4: ORG fallback, top 10)

| SALESORGANIZATION | Incoterms | Rows |
|-------------------|-----------|------|
| 0010 | DDP | 1,224,825 |
| 0300 | DDP | 108,243 |
| 0700 | DDP | 100,574 |
| 2500 | DDP | 73,255 |
| 5900 | DAP | 62,163 |
| 1500 | EXW | 46,183 |
| 4200 | DDP | 39,859 |

> SHIPPINGCONDITION is the key discriminator: the same customer can use different Incoterms (e.g., DAP vs DDP) depending on SC. Most ORGs default to DDP; ORG 5900 defaults to DAP, ORG 1500 to EXW.
