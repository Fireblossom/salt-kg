# SALESOFFICE Optimization Log

## Overview
- **Target Field**: SALESOFFICE
- **Primary Key**: N/A (mode only)
- **Fallback Key**: N/A

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.997** |
| SALT Baseline Best | 0.99 |
| SALT-KG Best | 1.00 |

## Script Location
- `agentic_solver/saved_scripts/salesoffice.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 99.80%
- **Strategy**: Mode prediction

---

## Lookup SQL Queries

No lookup table needed. The script returns the global mode value directly.

```sql
-- Global mode (result: '0010', covering 99.69% of training data)
SELECT MODE("SALESOFFICE") FROM train
```

Sample result: `'0010'` (1,910,792 / 1,916,685 rows)
