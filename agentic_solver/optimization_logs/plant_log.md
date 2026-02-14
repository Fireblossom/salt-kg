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

| SHIPPINGPOINT | PLANT | Rows | % |
|---------------|-------|------|---|
| MUST | 0001 | 977,431 | 51.0% |
| 0001 | 0001 | 245,256 | 12.8% |
| 2502 | 2500 | 73,255 | 3.8% |
| 0702 | 0700 | 72,650 | 3.8% |
| 0302 | 0310 | 54,032 | 2.8% |
| 1502 | 1500 | 46,178 | 2.4% |
| 5902 | 5900 | 41,881 | 2.2% |
| 0300 | 0310 | 40,937 | 2.1% |
| 4200 | 4200 | 35,596 | 1.9% |
| 0401 | 0400 | 33,747 | 1.8% |

**LOOKUP2** (SALESORGANIZATION → PLANT, 31 keys, top shown):

| SALESORGANIZATION | PLANT | Rows | % |
|-------------------|-------|------|---|
| 0010 | 0001 | 1,224,825 | 63.9% |
| 0300 | 0310 | 108,243 | 5.6% |
| 0700 | 0700 | 100,574 | 5.2% |
| 2500 | 2500 | 73,255 | 3.8% |
| 5900 | 5900 | 62,163 | 3.2% |
| 1500 | 1500 | 46,183 | 2.4% |

**Global mode**: `'0001'`

> Nearly 1:1 mapping. SAP organizational structure determines PLANT from SHIPPINGPOINT. SALESORGANIZATION provides a reliable regional fallback.
