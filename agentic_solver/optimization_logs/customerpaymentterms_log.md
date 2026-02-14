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
       MODE("CUSTOMERPAYMENTTERMS") AS payment_terms
FROM train
GROUP BY "SOLDTOPARTY"

-- LOOKUP2: SALESORGANIZATION -> CUSTOMERPAYMENTTERMS (fallback, 31 keys)
SELECT "SALESORGANIZATION",
       MODE("CUSTOMERPAYMENTTERMS") AS payment_terms
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("CUSTOMERPAYMENTTERMS") FROM train
```

### Sample Results

**LOOKUP1** (SOLDTOPARTY → PT, top 10 by frequency):

| SOLDTOPARTY | Payment Terms | Rows |
|-------------|---------------|------|
| 3143487067 | 54 | 25,677 |
| 6726809660 | 32 | 22,236 |
| 5300596642 | 32 | 15,508 |
| 0851548071 | 32 | 13,868 |
| 4742731422 | 32 | 13,546 |
| 6700514882 | 00 | 12,286 |
| 8383348969 | 33 | 10,886 |
| 9458338227 | 96 | 10,252 |

**LOOKUP2** (SALESORGANIZATION → PT, all 31 keys, top shown):

| SALESORGANIZATION | Payment Terms | Rows |
|-------------------|---------------|------|
| 0010 | 32 | 1,224,825 |
| 0300 | 32 | 108,243 |
| 0700 | 33 | 100,574 |
| 2500 | 54 | 73,255 |
| 5900 | 32 | 62,163 |
| 1500 | 03 | 46,183 |
| 4200 | 32 | 39,859 |
| 0400 | 03 | 38,333 |

**Global mode**: `'32'`

> Script flow: For each row, first try SOLDTOPARTY (customer-specific terms). If unseen customer, fall back to SALESORGANIZATION (regional default). If both miss, return `'32'`.
