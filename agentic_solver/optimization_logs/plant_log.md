# PLANT Optimization Log

## Overview
- **Target Field**: PLANT
- **Primary Key**: SHIPPINGPOINT
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.993** |
| SALT Baseline Best | 0.99 |
| SALT-KG Best | 1.00 |

## Script Location
- `agentic_solver/saved_scripts/plant.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 99.90%
- **Strategy**: SHIPPINGPOINT lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

```sql
-- LOOKUP1: SHIPPINGPOINT -> PLANT (primary key, 88 keys)
SELECT "SHIPPINGPOINT",
       MODE("PLANT") AS plant
FROM train
GROUP BY "SHIPPINGPOINT"

-- LOOKUP2: SALESORGANIZATION -> PLANT (fallback, 31 keys)
SELECT "SALESORGANIZATION",
       MODE("PLANT") AS plant
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("PLANT") FROM train
```

### Sample Results

**LOOKUP1** (SHIPPINGPOINT → PLANT, 88 keys, top 10):

| SHIPPINGPOINT | PLANT | Rows |
|---------------|-------|------|
| MUST | 0001 | 977,431 |
| 0001 | 0001 | 245,256 |
| 2502 | 2500 | 73,255 |
| 0702 | 0700 | 72,650 |
| 0302 | 0310 | 54,032 |
| 1502 | 1500 | 46,178 |
| 5902 | 5900 | 41,881 |
| 0300 | 0310 | 40,937 |
| 4200 | 4200 | 35,596 |
| 0401 | 0400 | 33,747 |

**LOOKUP2** (SALESORGANIZATION → PLANT, 31 keys, top shown):

| SALESORGANIZATION | PLANT | Rows |
|-------------------|-------|------|
| 0010 | 0001 | 1,224,825 |
| 0300 | 0310 | 108,243 |
| 0700 | 0700 | 100,574 |
| 2500 | 2500 | 73,255 |
| 5900 | 5900 | 62,163 |
| 1500 | 1500 | 46,183 |

**Global mode**: `'0001'`

> Nearly 1:1 mapping. SAP organizational structure determines PLANT from SHIPPINGPOINT. SALESORGANIZATION provides a reliable regional fallback.
