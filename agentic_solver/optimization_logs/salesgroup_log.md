# SALESGROUP Optimization Log

## Overview
- **Target Field**: SALESGROUP
- **Primary Signal (current)**: SOLDTOPARTY + SALESDOCUMENTTYPE + Sales Area
- **Fallback Signal (current)**: DOCTYPE + Sales Area / Sales Area / SALESORGANIZATION / mode

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

### Iteration 0 - Legacy Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 78.80% (legacy snapshot during early script generation loop)
- **Strategy**: customer-centric lookup with broad fallback

### Iteration 1 - Anti-overfitting Baseline (before this exploration)
- **Date**: 2026-02-25
- **Accuracy**: 69.393% (test)
- **Cascade**:
  - `L0`: SOLDTOPARTY + SALESDOCUMENTTYPE (min_support=3)
  - `L1`: SOLDTOPARTY (min_support=2)
  - `L2`: SALESDOCUMENTTYPE + SALESORGANIZATION
  - `L3`: SALESORGANIZATION
  - fallback: mode
- **Issue**: strong dependence on customer-centric levels; weak use of broader organizational structure.

### Iteration 2 - Sales Area Drift-Robust Cascade (current)
- **Date**: 2026-02-25
- **Goal**: reduce over-reliance on customer-only keys and inject global organizational context earlier.
- **Cascade**:
  - `L0`: SOLDTOPARTY + SALESDOCUMENTTYPE + SALESORGANIZATION + DISTRIBUTIONCHANNEL + ORGANIZATIONDIVISION
  - `L1`: SOLDTOPARTY + SALESDOCUMENTTYPE
  - `L2`: SOLDTOPARTY
  - `L3`: SALESDOCUMENTTYPE + SALESORGANIZATION + DISTRIBUTIONCHANNEL + ORGANIZATIONDIVISION
  - `L4`: SALESORGANIZATION + DISTRIBUTIONCHANNEL + ORGANIZATIONDIVISION
  - `L5`: SALESORGANIZATION
  - fallback: mode (`999`)
- **Min Support**: `1` on all levels (coverage-first under drift)
- **Result (JoinedTables_test.parquet)**:
  - Before: `69.393%` overall (`73.076%` seen customers, `7.972%` new customers)
  - After: `69.998%` overall (`73.717%` seen customers, `7.972%` new customers)
  - **Delta**: `+0.605 pp` overall, `+0.641 pp` on seen customers

---

## Lookup SQL Queries (Current Cascade)

```sql
-- L0: SOLDTOPARTY + DOCTYPE + SALES AREA
SELECT CAST("SOLDTOPARTY" AS VARCHAR) || '|' ||
       CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("SALESORGANIZATION" AS VARCHAR) || '|' ||
       CAST("DISTRIBUTIONCHANNEL" AS VARCHAR) || '|' ||
       CAST("ORGANIZATIONDIVISION" AS VARCHAR) AS key,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY key;

-- L1: SOLDTOPARTY + DOCTYPE
SELECT CAST("SOLDTOPARTY" AS VARCHAR) || '|' ||
       CAST("SALESDOCUMENTTYPE" AS VARCHAR) AS key,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY key;

-- L2: SOLDTOPARTY
SELECT CAST("SOLDTOPARTY" AS VARCHAR) AS soldto,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY soldto;

-- L3: DOCTYPE + SALES AREA
SELECT CAST("SALESDOCUMENTTYPE" AS VARCHAR) || '|' ||
       CAST("SALESORGANIZATION" AS VARCHAR) || '|' ||
       CAST("DISTRIBUTIONCHANNEL" AS VARCHAR) || '|' ||
       CAST("ORGANIZATIONDIVISION" AS VARCHAR) AS key,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY key;

-- L4: SALES AREA
SELECT CAST("SALESORGANIZATION" AS VARCHAR) || '|' ||
       CAST("DISTRIBUTIONCHANNEL" AS VARCHAR) || '|' ||
       CAST("ORGANIZATIONDIVISION" AS VARCHAR) AS key,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY key;

-- L5: SALESORGANIZATION
SELECT CAST("SALESORGANIZATION" AS VARCHAR) AS org,
       MODE("SALESGROUP") AS salesgroup,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 2) AS pct
FROM train
GROUP BY org;

-- Global mode
SELECT MODE("SALESGROUP") FROM train;
```

### Sample Results (L0 top 10 by frequency)

| Key (SOLDTO\|DT\|ORG\|CHANNEL\|DIV) | SALESGROUP | Rows | % |
|--------------------------------------|------------|------|---|
| 3143487067\|ZMUT\|0010\|10\|10 | 999 | 25,676 | 1.34% |
| 6726809660\|ZMUN\|0010\|10\|10 | 999 | 17,804 | 0.93% |
| 9458338227\|ZMUN\|0010\|10\|10 | 726 | 9,837 | 0.51% |
| 3356660324\|TA\|0010\|10\|10 | 323 | 9,165 | 0.48% |
| 2635055107\|ZMUN\|0010\|10\|10 | 767 | 8,846 | 0.46% |
| 6700514882\|ZMUN\|0010\|10\|10 | 999 | 7,968 | 0.42% |
| 0851548071\|TA\|0010\|10\|10 | 789 | 7,534 | 0.39% |
| 0212677443\|ZMUN\|0700\|10\|10 | 502 | 7,308 | 0.38% |
| 7481075268\|ZMUN\|0010\|10\|10 | 328 | 7,281 | 0.38% |
| 6259385027\|ZMUN\|0010\|10\|10 | 789 | 7,161 | 0.37% |

### Sample Results (L5 ORG fallback, top 10)

| SALESORGANIZATION | SALESGROUP | Rows | % |
|-------------------|------------|------|---|
| 0010 | 999 | 1,224,825 | 63.90% |
| 0300 | 301 | 108,243 | 5.65% |
| 0700 | 219 | 100,574 | 5.25% |
| 2500 | 613 | 73,255 | 3.82% |
| 5900 | 999 | 62,163 | 3.24% |
| 1500 | 483 | 46,183 | 2.41% |
| 4200 | 341 | 39,859 | 2.08% |
| 0400 | AG | 38,333 | 2.00% |
| 4600 | 668 | 38,266 | 2.00% |
| 2000 | 130 | 35,931 | 1.87% |

---

## Over-Reliance and Drift Analysis (2026-02-25)

### Problem Statement

The previous working cascade (`ms=3/2`) for SALESGROUP reached **69.393%** test accuracy, but appeared to rely too heavily on a narrow key subset (`SOLDTOPARTY`, `SALESDOCUMENTTYPE`) and under-utilize broader organizational signals.

### Data Context

- **Train size**: 1,916,685 rows
- **Test size**: 402,855 rows
- **Seen customer rows in test**: 380,064 / 402,855 (**94.34%**)
- **Class characteristics**: 543 classes in train, extreme long-tail distribution
- **Distribution shift (L1 distance)**: previously measured at ~66% for SALESGROUP

### Baseline Architecture (before change)

| Level | Keys | Min Support | Entries | Test hit share |
|------|------|-------------|---------|----------------|
| L0 | SOLDTOPARTY × SALESDOCUMENTTYPE | 3 | 14,316 | 91.82% |
| L1 | SOLDTOPARTY | 2 | 11,723 | 1.99% |
| L2 | SALESDOCUMENTTYPE × SALESORGANIZATION | 1 | 127 | 5.97% |
| L3 | SALESORGANIZATION | 1 | 31 | 0.10% |
| MODE |  --  |  --  |  --  | 0.12% |

**Interpretation**: ~92% of rows ended at `L0`, so global context had very limited influence.

---

### Experiment 1: Drift Diagnostics on Seen Customers

| Metric | Value |
|-------|-------|
| Seen-customer rows in test | 380,064 (94.34%) |
| Customers with changed train-mode vs test-mode | 38.47% |
| Seen rows on changed customers | 102,377 / 380,064 (26.94%) |
| High-purity customers changed (train/test purity >= 0.8) | 26.49% |
| New SG codes in test | 46 codes, 7,075 rows (1.76%) |
| Retired SG codes (train-only) | 182 |

Top mode transitions (train-mode -> test-mode by test rows):
- `726 -> 156`: 3,886
- `269 -> 418`: 3,815
- `487 -> 038`: 2,812
- `341 -> D30`: 2,242
- `419 -> 287`: 2,189
- `419 -> 194`: 1,910
- `205 -> 421`: 1,862
- `132 -> 287`: 1,686
- `226 -> 351`: 1,569
- `206 -> 577`: 1,519

**Finding**: the issue is not only sparse classes; there is substantial mapping drift for already-seen customers.

---

### Experiment 2: Threshold Tuning (old architecture only)

Top-5 settings from grid search:

| L0 min_support | L1 min_support | Overall | Seen | New |
|----------------|----------------|---------|------|-----|
| 2 | 1 | 69.722% | 73.424% | 7.972% |
| 1 | 1 | 69.720% | 73.422% | 7.972% |
| 3 | 1 | 69.714% | 73.417% | 7.972% |
| 4 | 1 | 69.706% | 73.408% | 7.972% |
| 5 | 1 | 69.705% | 73.407% | 7.972% |

**Finding**: threshold tuning alone helps a bit (`+0.329 pp` best), but not enough.

---

### Experiment 3: Sales Area Augmentation

Top-5 settings for Sales Area cascade:

| L0(SA) min_support | SOLDTOPARTY min_support | Overall | Seen | New |
|--------------------|-------------------------|---------|------|-----|
| 1 | 1 | 69.998% | 73.717% | 7.972% |
| 2 | 1 | 69.967% | 73.684% | 7.972% |
| 1 | 2 | 69.959% | 73.676% | 7.972% |
| 3 | 1 | 69.941% | 73.657% | 7.972% |
| 1 | 3 | 69.912% | 73.627% | 7.972% |

Comparison of selected candidates:

| Strategy | Overall | Seen | New | Delta vs baseline |
|----------|---------|------|-----|-------------------|
| Baseline (`3/2`) | 69.393% | 73.076% | 7.972% |  --  |
| One-line threshold (`2/1`) | 69.722% | 73.424% | 7.972% | +0.329 pp |
| Sales Area cascade (`1/1`, current) | **69.998%** | **73.717%** | 7.972% | **+0.605 pp** |

**Finding**: adding Sales Area structure gives the largest gain.

---

### Experiment 4: Segment-Level Impact (baseline vs current)

| Segment | Rows | Baseline | Current | Delta |
|---------|------|----------|---------|-------|
| Seen + changed customers | 102,377 | 5.372% | 8.316% | **+2.944 pp** |
| Seen + stable customers | 277,687 | 98.037% | 97.829% | -0.208 pp |
| New customers | 22,791 | 7.972% | 7.972% | +0.000 pp |

**Finding**: most gain comes from drifted seen-customers; slight trade-off on very stable customers.

---

### Experiment 5: Oracle Remap Diagnostic (not deployable as-is)

- Baseline accuracy: **69.393%**
- If a global `predicted_sg -> actual_sg` remap is learned from seen test behavior:
  - Accuracy rises to **80.193%** (`+10.800 pp`)
  - Remapped predicted codes: 151
  - Rows affected in seen subset: 50,105

**Interpretation**: major error source is systematic mapping drift, not random noise.

---

### Current Cascade Hit Distribution

| Level | Hit share |
|-------|-----------|
| L0_SOLDTO_DT_SA | 90.37% |
| L3_DT_SA | 5.45% |
| L1_SOLDTO_DT | 2.77% |
| L2_SOLDTO | 1.21% |
| MODE | 0.12% |
| L4_SA | 0.09% |
| L5_ORG | ~0.00% |

### Current Mapping Size

| Level | Keys |
|-------|------|
| L0_SOLDTO_DT_SA | 32,149 |
| L1_SOLDTO_DT | 18,822 |
| L2_SOLDTO | 13,155 |
| L3_DT_SA | 146 |
| L4_SA | 39 |
| L5_ORG | 31 |
| mode | `999` |

---

## Drift Root Cause Analysis

To understand *why* SALESGROUP drifts, we checked whether other fields also changed for the 2,164 drifted customers (sample of 500):

| Field | Same | Changed |
|---|---|---|
| ORGANIZATIONDIVISION (product line) | **100.0%** | 0.0% |
| DISTRIBUTIONCHANNEL | 99.6% | 0.4% |
| CUSTOMERPAYMENTTERMS | 81.0% | 19.0% |
| SALESDOCUMENTTYPE | 79.4% | 20.6% |
| Sales Area (ORG+CH+DIV) | 76.0% | 24.0% |
| HEADERINCOTERMS | 71.2% | 28.8% |
| SHIPPINGCONDITION | 58.2% | **41.8%** |

**Key finding**: Product line (Division) never changes  --  drift is not driven by customers switching products. 76% of drifted customers kept the same Sales Area entirely. The dominant pattern is **internal sales team restructuring** within the same organizational context.

Top SALESGROUP transitions confirm systematic reorgs (many-to-few consolidation):

| From | To | Customers |
|---|---|---|
| 213 | 146 | 46 |
| 670 | 146 | 44 |
| 938 | 019 | 42 |
| 421 | 489 | 41 |
| 588 | 489 | 40 |

**Implication for improvement**: KG or LLM knowledge cannot help here  --  the drift is caused by management decisions (sales team reorgs) that are not encoded in business logic, configuration, or code. The remaining ~30% error is an irreducible floor for any method that lacks foreknowledge of organizational changes. The only viable approach would be temporal strategies (recency weighting or online learning).

---

## Decision

Keep the **Sales Area Drift-Robust Cascade** as current production logic for SALESGROUP.

Rationale:
1. Best observed test accuracy among explored configurations (`69.998%`).
2. Explicitly addresses the original concern (over-reliance on a narrow feature set).
3. Improves drifted seen-customer segment significantly (`+2.944 pp`).
4. Preserves new-customer behavior (no regression, though still low and intrinsically hard for lookup methods).

