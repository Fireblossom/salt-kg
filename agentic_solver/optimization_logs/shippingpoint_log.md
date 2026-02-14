# SHIPPINGPOINT Optimization Log

## Overview
- **Target Field**: SHIPPINGPOINT
- **Primary Keys**: PLANT + SHIPPINGCONDITION + SALESDOCUMENTTYPE
- **Strategy**: Multi-factor composite lookup

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.986** |
| SALT Baseline Best | 0.98 |
| SALT-KG Best | 0.99 |

## Script Location
- `agentic_solver/saved_scripts/shippingpoint.py`
- `agentic_solver/saved_scripts/shippingpoint_mapping.json`

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

## Lookup SQL Queries

```sql
-- Composite: (PLANT, is_service) -> SHIPPINGPOINT (59 keys)
-- is_service = SHIPPINGCONDITION >= 94 OR DOCTYPE IN ('ZMUN', 'ZMUT')
SELECT "PLANT" || '|' ||
       CASE WHEN CAST("SHIPPINGCONDITION" AS INT) >= 94
            OR "SALESDOCUMENTTYPE" IN ('ZMUN', 'ZMUT')
       THEN '1' ELSE '0' END AS key,
       MODE("SHIPPINGPOINT") AS shippingpoint,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY key

-- SC=18 special case: PLANT -> SHIPPINGPOINT
SELECT "PLANT",
       MODE("SHIPPINGPOINT") AS shippingpoint,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
WHERE CAST("SHIPPINGCONDITION" AS INT) = 18
GROUP BY "PLANT"

-- Variant: SHIPPINGCONDITION 18-20 by PLANT
SELECT "PLANT",
       MODE("SHIPPINGPOINT") AS shippingpoint,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
WHERE CAST("SHIPPINGCONDITION" AS INT) BETWEEN 18 AND 20
GROUP BY "PLANT"

-- Global mode (fallback)
SELECT MODE("SHIPPINGPOINT") FROM train
```

### Sample Results (Composite: top 15 by frequency)

| Key (PLANT\|is_service) | SHIPPINGPOINT | Rows | % |
|-------------------------|---------------|------|---|
| 0001\|1 | MUST | 978,285 | 51.0% |
| 0001\|0 | 0001 | 246,423 | 12.9% |
| 2500\|1 | 2502 | 73,255 | 3.8% |
| 0700\|1 | 0702 | 72,659 | 3.8% |
| 0310\|0 | 0300 | 54,270 | 2.8% |
| 0310\|1 | 0302 | 53,289 | 2.8% |
| 1500\|1 | 1502 | 46,179 | 2.4% |
| 5900\|1 | 5902 | 41,896 | 2.2% |
| 4200\|0 | 4200 | 35,585 | 1.9% |
| 0400\|1 | 0401 | 33,918 | 1.8% |

> `is_service=1` (SC>=94 or ZMUN/ZMUT) routes to virtual shipping points (MUST, x02 suffix). `is_service=0` routes to physical points. Only 59 unique keys needed. Top 10 keys cover 85.4% of data.
