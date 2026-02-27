# ITEMINCOTERMSCLASSIFICATION Optimization Log

## Overview
- **Target Field**: ITEMINCOTERMSCLASSIFICATION
- **Primary Key**: SOLDTOPARTY
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.840** |
| SALT Baseline Best | 0.80 |
| SALT-KG Best | 0.84 |

## Script Location
- `agentic_solver/saved_scripts/itemincotermsclassification.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 77.15%
- **Strategy**: SOLDTOPARTY lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

Same 5-level cascade as HEADERINCOTERMSCLASSIFICATION:

```sql
-- L0: 4-factor (SOLDTOPARTY, DOCTYPE, ORG, SHIPPINGCONDITION)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" || '|' || "SHIPPINGCONDITION" AS key,
       MODE("ITEMINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L1: 3-factor (SOLDTOPARTY, DOCTYPE, ORG)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" AS key,
       MODE("ITEMINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L2: 2-factor (SOLDTOPARTY, DOCTYPE)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" AS key,
       MODE("ITEMINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY key

-- L3: SOLDTOPARTY only
SELECT "SOLDTOPARTY",
       MODE("ITEMINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY "SOLDTOPARTY"

-- L4: SALESORGANIZATION only
SELECT "SALESORGANIZATION",
       MODE("ITEMINCOTERMSCLASSIFICATION") AS incoterms
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("ITEMINCOTERMSCLASSIFICATION") FROM train
```

### Sample Results

Same mapping data as HEADERINCOTERMSCLASSIFICATION (uses shared JSON file). See [headerincotermsclassification_log.md](headerincotermsclassification_log.md) for sample query outputs.
