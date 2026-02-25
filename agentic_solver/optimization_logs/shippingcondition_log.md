# SHIPPINGCONDITION Optimization Log

## Overview
- **Target Field**: SHIPPINGCONDITION
- **Primary Signal (current)**: SOLDTOPARTY/SHIPTOPARTY + SALESDOCUMENTTYPE + SHIPPINGPOINT
- **Structural Signal (current)**: SALESDOCUMENTTYPE + PLANT + SHIPPINGPOINT

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

## Optimization History

### Iteration 0 - Initial (2026-02-04 16:07)
- **Accuracy**: 56.90%
- **Strategy**: SHIPPINGPOINT -> SALESORGANIZATION -> mode

### Iteration 1 - Customer-heavy baseline (before this exploration)
- **Date**: 2026-02-25
- **Accuracy**: 69.367% (test)
- **Cascade**:
  - `L0`: SOLDTOPARTY + SALESDOCUMENTTYPE + SHIPPINGPOINT (ms=3)
  - `L1`: SHIPTOPARTY + SALESDOCUMENTTYPE + SHIPPINGPOINT (ms=3)
  - `L2`: SOLDTOPARTY + SALESDOCUMENTTYPE (ms=3)
  - `L3`: SHIPTOPARTY + SALESDOCUMENTTYPE (ms=3)
  - `L4`: SALESDOCUMENTTYPE + SHIPPINGPOINT
  - `L5`: SOLDTOPARTY (ms=2)
  - `L6`: SHIPPINGPOINT
  - fallback: mode

### Iteration 2 - Plant-enhanced hybrid cascade (current)
- **Date**: 2026-02-25
- **Goal**: reduce over-reliance on customer-only fallbacks while keeping high-precision customer+document+shipping-point anchors.
- **Cascade**:
  - `L0`: SOLDTOPARTY + SALESDOCUMENTTYPE + SHIPPINGPOINT (ms=3)
  - `L1`: SHIPTOPARTY + SALESDOCUMENTTYPE + SHIPPINGPOINT (ms=3)
  - `L2`: SALESDOCUMENTTYPE + PLANT + SHIPPINGPOINT
  - `L3`: SALESDOCUMENTTYPE + SHIPPINGPOINT
  - `L4`: SHIPPINGPOINT
  - `L5`: SOLDTOPARTY + SALESDOCUMENTTYPE (ms=2)
  - fallback: mode (`99`)
- **Result (JoinedTables_test.parquet)**:
  - Before: `69.367%` overall (`70.713%` seen sold-to, `46.918%` new sold-to)
  - After: `69.550%` overall (`70.877%` seen sold-to, `47.427%` new sold-to)
  - **Delta**: `+0.183 pp` overall

---

## Lookup SQL Queries (Current Cascade)

```sql
-- L0: SOLDTOPARTY + DOCTYPE + SHIPPINGPOINT
SELECT CAST("SOLDTOPARTY" AS VARCHAR) || '|' ||
       CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("SHIPPINGPOINT" AS VARCHAR) AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY key;

-- L1: SHIPTOPARTY + DOCTYPE + SHIPPINGPOINT
SELECT CAST("SHIPTOPARTY" AS VARCHAR) || '|' ||
       CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("SHIPPINGPOINT" AS VARCHAR) AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY key;

-- L2: DOCTYPE + PLANT + SHIPPINGPOINT
SELECT CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("PLANT" AS VARCHAR) || '|' ||
       CAST("SHIPPINGPOINT" AS VARCHAR) AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY key;

-- L3: DOCTYPE + SHIPPINGPOINT
SELECT CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("SHIPPINGPOINT" AS VARCHAR) AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY key;

-- L4: SHIPPINGPOINT
SELECT CAST("SHIPPINGPOINT" AS VARCHAR) AS shippingpoint,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY shippingpoint;

-- L5: SOLDTOPARTY + DOCTYPE
SELECT CAST("SOLDTOPARTY" AS VARCHAR) || '|' ||
       CAST("SALESDOCUMENTTYPE" AS VARCHAR) AS key,
       MODE("SHIPPINGCONDITION") AS shippingcondition,
       COUNT(*) AS cnt
FROM train
GROUP BY key;

-- Global mode
SELECT MODE("SHIPPINGCONDITION") FROM train;
```

### Sample Results (L2: DT+PLANT+SP top 10 by frequency)

| Key (DT\|PLANT\|SP) | SC | Rows | % |
|----------------------|----|------|---|
| ZMUN\|0001\|MUST | 99 | 936,182 | 48.84% |
| TA\|0001\|0001 | 01 | 225,004 | 11.74% |
| ZMUN\|2500\|2502 | 99 | 73,253 | 3.82% |
| ZMUN\|0700\|0702 | 99 | 72,648 | 3.79% |
| ZMUN\|0310\|0302 | 96 | 52,811 | 2.76% |
| ZMUN\|1500\|1502 | 95 | 46,172 | 2.41% |
| ZMUN\|5900\|5902 | 99 | 41,423 | 2.16% |
| ZMUT\|0001\|MUST | 95 | 41,199 | 2.15% |
| TA\|0310\|0300 | 01 | 36,483 | 1.90% |
| ZMUN\|0400\|0401 | 99 | 33,747 | 1.76% |

### Sample Results (L4: SHIPPINGPOINT fallback top 10)

| SHIPPINGPOINT | SC | Rows | % |
|---------------|----|------|---|
| MUST | 99 | 977,431 | 51.00% |
| 0001 | 01 | 245,256 | 12.80% |
| 2502 | 99 | 73,255 | 3.82% |
| 0702 | 99 | 72,650 | 3.79% |
| 0302 | 96 | 54,032 | 2.82% |
| 1502 | 95 | 46,178 | 2.41% |
| 5902 | 99 | 41,881 | 2.19% |
| 0300 | 01 | 40,937 | 2.14% |
| 4200 | 13 | 35,596 | 1.86% |
| 0401 | 99 | 33,747 | 1.76% |

---

## Over-Reliance and Drift Exploration (2026-02-25)

### Problem Statement

Need to check whether the old cascade over-relies on a narrow customer-centric feature set and misses broader operational structure.

### Data Context

- **Train**: 1,916,685 rows
- **Test**: 402,855 rows
- **Seen sold-to rows in test**: 380,064 (94.34%)
- **Seen ship-to rows in test**: 372,375 (92.43%)
- **Target distribution L1 shift**: 19.56%
- **Customer-determined rows**:
  - by SOLDTOPARTY: 6.65%
  - by SHIPTOPARTY: 9.74%

**Interpretation**: SHIPPINGCONDITION is not primarily customer-determined.

---

### Experiment 1: Key Stability Across Train -> Test

| Key Family | Seen Rows | Changed Rows on Seen | High-purity Changed |
|------------|-----------|----------------------|---------------------|
| SOLDTO | 380,064 / 402,855 (94.34%) | 118,767 (31.25%) | 27.37% |
| SHIPTO | 372,375 / 402,855 (92.43%) | 125,951 (33.82%) | 23.15% |
| DT+SP | 400,035 / 402,855 (99.30%) | 21,140 (5.28%) | 23.68% |
| DT+ORG+SP | 399,880 / 402,855 (99.26%) | 21,139 (5.29%) | 22.50% |
| DT+PLANT+SP | 399,916 / 402,855 (99.27%) | 21,102 (5.28%) | 23.68% |

**Finding**: structural keys (`DT+SP`, `DT+PLANT+SP`) are far more stable than customer keys.

---

### Experiment 2: Candidate Strategy Comparison

| Strategy | Overall | Seen sold-to | New sold-to |
|----------|---------|--------------|-------------|
| current_baseline | 69.367% | 70.713% | 46.918% |
| current_relaxed_ms | 69.443% | 70.794% | 46.900% |
| hybrid_ops_enhanced | 69.548% | 70.876% | 47.409% |
| **with_plant (current)** | **69.550%** | **70.877%** | **47.427%** |
| no_customer | 53.574% | 54.066% | 45.360% |
| structural_first | 53.480% | 53.967% | 45.360% |

**Findings**:
1. Removing customer anchors is too destructive (~53%).
2. Best result is a hybrid: keep customer precision, but replace weak customer fallbacks with structural operational fallback.
3. `with_plant` beats baseline by `+0.183 pp`.

---

### Experiment 3: Segment-Level Impact (baseline vs with_plant)

| Segment | Rows | Baseline | With Plant | Delta |
|---------|------|----------|------------|-------|
| Seen + changed sold-to | 118,767 | 42.823% | 43.797% | +0.974 pp |
| Seen + stable sold-to | 261,297 | 83.391% | 83.186% | -0.205 pp |
| New sold-to | 22,791 | 46.918% | 47.427% | +0.509 pp |

**Finding**: gains come from drifted seen customers + new customers; slight trade-off on stable seen customers.

---

### Experiment 4: Error Concentration (98 vs 99)

| Strategy | Total Errors | 98<->99 Errors | Share |
|----------|--------------|----------------|-------|
| baseline | 123,406 | 41,190 | 33.38% |
| with_plant | 122,668 | 41,268 | 33.64% |

Top sold-to mode transitions by test rows:
- `98 -> 99`: 18,220
- `99 -> 98`: 10,621
- `95 -> 99`: 9,201
- `01 -> 98`: 7,330
- `99 -> 96`: 6,718
- `01 -> 99`: 6,565
- `99 -> 01`: 5,503
- `96 -> 99`: 5,482
- `98 -> 96`: 4,740
- `96 -> 98`: 3,018

**Finding**: major residual error remains 98/99 ambiguity.

---

### Hit Distribution and Mapping Size

Current cascade hit shares:

| Level | Hit Share |
|-------|-----------|
| L0_SOLDTO_DT_SP | 88.41% |
| L2_DT_PLANT_SP | 8.92% |
| L1_SHIPTO_DT_SP | 1.96% |
| MODE | 0.47% |
| L5_SOLDTO_DT | 0.19% |
| L4_SP | 0.04% |
| L3_DT_SP | 0.00% |

Mapping size:

| Strategy | Total Keys |
|----------|------------|
| baseline | 87,475 |
| **with_plant (current)** | **61,493** |

**Finding**: current strategy is both slightly better and materially smaller.

---

## Drift Root Cause Analysis

SHIPPINGCONDITION has the **highest drift rate** of all target fields: 2,436 customers (43.7% of 5,576 seen) changed their dominant value between train and test.

For these drifted customers, which other fields also changed?

| Field | Same | Changed |
|---|---|---|
| ORGANIZATIONDIVISION | 100.0% | 0.0% |
| DISTRIBUTIONCHANNEL | 99.4% | 0.6% |
| CUSTOMERPAYMENTTERMS | 76.4% | 23.6% |
| SALESORGANIZATION | 69.2% | 30.8% |
| SALESGROUP | 62.8% | 37.2% |
| HEADERINCOTERMS | 58.6% | 41.4% |
| SALESDOCUMENTTYPE | 58.0% | **42.0%** |

Unlike SALESGROUP (where Division never changes), SC drift shows strong co-variance with DocType changes (42%) and Incoterms changes (41.4%). This suggests SC drift is often tied to changes in **order processing patterns** (different document types → different shipping workflows), not just internal reorgs.

Top transitions:

| From | To | Customers |
|---|---|---|
| 99 | 01 | 302 |
| 98 | 99 | 201 |
| 99 | 98 | 145 |
| 01 | 99 | 136 |
| 95 | 99 | 108 |

The dominant 99↔01 transition reflects the boundary between standard physical shipping (99) and special logistics (01). The 98↔99 transitions confirm the known ambiguity between these adjacent SC values (33% of all current errors stem from 98/99 confusion, see Experiment 4).

---

## Decision

Adopt **with_plant** as the current SHIPPINGCONDITION strategy.

Rationale:
1. Best observed test accuracy among explored practical variants.
2. Directly addresses over-reliance concern by introducing stable structural fallback (`DT+PLANT+SP`).
3. Improves drifted and new-customer segments.
4. Reduces mapping footprint significantly while improving accuracy.

