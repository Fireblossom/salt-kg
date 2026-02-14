# SALESGROUP Optimization Log

## Overview
- **Target Field**: SALESGROUP
- **Primary Key**: SOLDTOPARTY
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.760** |
| SALT Baseline Best | 0.51 |
| SALT-KG Best | 0.53 |

## Script Location
- `agentic_solver/saved_scripts/salesgroup.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 78.80%
- **Strategy**: SOLDTOPARTY lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

```sql
-- L1: SOLDTOPARTY + CUSTOMERPAYMENTTERMS -> SALESGROUP (17,616 keys)
SELECT "SOLDTOPARTY" || '|' || "CUSTOMERPAYMENTTERMS" AS key,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY key

-- L2: SOLDTOPARTY -> SALESGROUP (fallback, 13,155 keys)
SELECT "SOLDTOPARTY",
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY "SOLDTOPARTY"

-- Global mode (fallback): '999'
SELECT MODE("SALESGROUP") FROM train
```

### Sample Results

**L1** (SOLDTOPARTY+PAYMENT → SALESGROUP, 17,616 keys, top 10):

| Key (SOLDTO\|PAYMENT) | SALESGROUP | Rows | % |
|------------------------|------------|------|---|
| 6726809660\|32 | 999 | 22,234 | 1.2% |
| 3143487067\|54 | 999 | 17,879 | 0.9% |
| 5300596642\|32 | 999 | 15,474 | 0.8% |
| 0851548071\|32 | 789 | 13,868 | 0.7% |
| 4742731422\|32 | 705 | 13,440 | 0.7% |
| 6700514882\|00 | 999 | 12,266 | 0.6% |
| 8383348969\|33 | 301 | 10,872 | 0.6% |
| 9458338227\|96 | 726 | 10,252 | 0.5% |

**L2** (SOLDTOPARTY → SALESGROUP, 13,155 keys, top 10):

| SOLDTOPARTY | SALESGROUP | Rows | % |
|-------------|------------|------|---|
| 3143487067 | 999 | 25,677 | 1.3% |
| 6726809660 | 999 | 22,236 | 1.2% |
| 5300596642 | 999 | 15,508 | 0.8% |
| 0851548071 | 789 | 13,868 | 0.7% |
| 4742731422 | 705 | 13,546 | 0.7% |
| 6700514882 | 999 | 12,286 | 0.6% |
| 8383348969 | 301 | 10,886 | 0.6% |
| 9458338227 | 726 | 10,252 | 0.5% |

**Global mode**: `'999'`

> Script flow: L1 adds CUSTOMERPAYMENTTERMS for finer segmentation (e.g., same customer may have different SalesGroup for different payment terms). L2 falls back to SOLDTOPARTY alone. `'999'` is the catch-all default group.
