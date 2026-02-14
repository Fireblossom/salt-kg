# CUSTOMERPAYMENTTERMS Optimization Log

## Overview
- **Target Field**: CUSTOMERPAYMENTTERMS
- **Primary Key**: SOLDTOPARTY
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.852** |
| SALT Baseline Best | 0.62 |
| SALT-KG Best | 0.70 |

## Script Location
- `agentic_solver/saved_scripts/customerpaymentterms.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 79.60%
- **Strategy**: SOLDTOPARTY lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

```sql
-- LOOKUP1: SOLDTOPARTY -> CUSTOMERPAYMENTTERMS (primary key, 13,155 keys)
SELECT "SOLDTOPARTY",
       MODE("CUSTOMERPAYMENTTERMS") AS payment_terms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY "SOLDTOPARTY"

-- LOOKUP2: SALESORGANIZATION -> CUSTOMERPAYMENTTERMS (fallback, 31 keys)
SELECT "SALESORGANIZATION",
       MODE("CUSTOMERPAYMENTTERMS") AS payment_terms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("CUSTOMERPAYMENTTERMS") FROM train
```

### Sample Results

**LOOKUP1** (SOLDTOPARTY → PT, top 10 by frequency):

| SOLDTOPARTY | Payment Terms | Rows | % |
|-------------|---------------|------|---|
| 3143487067 | 54 | 25,677 | 1.3% |
| 6726809660 | 32 | 22,236 | 1.2% |
| 5300596642 | 32 | 15,508 | 0.8% |
| 0851548071 | 32 | 13,868 | 0.7% |
| 4742731422 | 32 | 13,546 | 0.7% |
| 6700514882 | 00 | 12,286 | 0.6% |
| 8383348969 | 33 | 10,886 | 0.6% |
| 9458338227 | 96 | 10,252 | 0.5% |

**LOOKUP2** (SALESORGANIZATION → PT, all 31 keys, top shown):

| SALESORGANIZATION | Payment Terms | Rows | % |
|-------------------|---------------|------|---|
| 0010 | 32 | 1,224,825 | 63.9% |
| 0300 | 32 | 108,243 | 5.6% |
| 0700 | 33 | 100,574 | 5.2% |
| 2500 | 54 | 73,255 | 3.8% |
| 5900 | 32 | 62,163 | 3.2% |
| 1500 | 03 | 46,183 | 2.4% |
| 4200 | 32 | 39,859 | 2.1% |
| 0400 | 03 | 38,333 | 2.0% |

**Global mode**: `'32'`

> Script flow: For each row, first try SOLDTOPARTY (customer-specific terms). If unseen customer, fall back to SALESORGANIZATION (regional default). If both miss, return `'32'`.
