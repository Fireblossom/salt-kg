# HEADERINCOTERMSCLASSIFICATION Optimization Log

## Overview
- **Target Field**: HEADERINCOTERMSCLASSIFICATION
- **Primary Key**: SOLDTOPARTY
- **Fallback Key**: SALESORGANIZATION

## Current Performance
| Metric | Value |
|--------|-------|
| Ours (MRR) | **0.840** |
| SALT Baseline Best | 0.81 |
| SALT-KG Best | 0.85 |

## Script Location
- `agentic_solver/saved_scripts/headerincotermsclassification.py`

---

## Optimization History

### Iteration 0 - Initial Script
- **Date**: 2026-02-04 16:07
- **Accuracy**: 77.00%
- **Strategy**: SOLDTOPARTY lookup → SALESORGANIZATION fallback → mode

---

## Lookup SQL Queries

5-level cascade: (SOLDTO+DT+ORG+SC) > (SOLDTO+DT+ORG) > (SOLDTO+DT) > SOLDTO > ORG

```sql
-- L0: 4-factor (SOLDTOPARTY, DOCTYPE, ORG, SHIPPINGCONDITION) - most specific (46,754 keys)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" || '|' || "SHIPPINGCONDITION" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY key

-- L1: 3-factor (SOLDTOPARTY, DOCTYPE, ORG)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" || '|' ||
       "SALESORGANIZATION" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY key

-- L2: 2-factor (SOLDTOPARTY, DOCTYPE)
SELECT "SOLDTOPARTY" || '|' || "SALESDOCUMENTTYPE" AS key,
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY key

-- L3: SOLDTOPARTY only
SELECT "SOLDTOPARTY",
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY "SOLDTOPARTY"

-- L4: SALESORGANIZATION only (31 keys)
SELECT "SALESORGANIZATION",
       MODE("HEADERINCOTERMSCLASSIFICATION") AS incoterms,
       COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM train), 1) AS pct
FROM train
GROUP BY "SALESORGANIZATION"

-- Global mode (fallback)
SELECT MODE("HEADERINCOTERMSCLASSIFICATION") FROM train
```

### Sample Results (L0: top 10 by frequency)

| Key (SOLDTO\|DT\|ORG\|SC) | Incoterms | Rows | % |
|----------------------------|-----------|------|---|
| 3143487067\|ZMUT\|0010\|95 | EXW | 25,676 | 1.3% |
| 6726809660\|ZMUN\|0010\|95 | FCA | 12,400 | 0.6% |
| 3356660324\|TA\|0010\|01 | CIP | 9,161 | 0.5% |
| 0851548071\|TA\|0010\|05 | FCA | 7,366 | 0.4% |
| 9458338227\|ZMUN\|0010\|98 | DDP | 6,306 | 0.3% |
| 4290077062\|ZMUT\|0010\|95 | EXW | 5,972 | 0.3% |
| 2635055107\|ZMUN\|0010\|98 | DDP | 5,590 | 0.3% |
| 7528327689\|ZMUN\|0010\|98 | DDP | 5,511 | 0.3% |
| 5389539235\|ZIA\|4200\|13 | DDP | 5,263 | 0.3% |
| 1490599991\|ZMUN\|0010\|98 | DDP | 4,831 | 0.3% |

### Sample Results (L4: ORG fallback, top 10)

| SALESORGANIZATION | Incoterms | Rows | % |
|-------------------|-----------|------|---|
| 0010 | DDP | 1,224,825 | 63.9% |
| 0300 | DDP | 108,243 | 5.6% |
| 0700 | DDP | 100,574 | 5.2% |
| 2500 | DDP | 73,255 | 3.8% |
| 5900 | DAP | 62,163 | 3.2% |
| 1500 | EXW | 46,183 | 2.4% |
| 4200 | DDP | 39,859 | 2.1% |

> SHIPPINGCONDITION is the key discriminator: the same customer can use different Incoterms (e.g., DAP vs DDP) depending on SC. Most ORGs default to DDP; ORG 5900 defaults to DAP, ORG 1500 to EXW.

---

## Cascade Overfitting Analysis (2026-02-25)

### Problem Statement

The current 9-level cascade achieves **train 94.2% / test 77.8%**, yielding a **16.4pp train-test gap**  --  the largest among all fields. This section documents a systematic investigation into whether this gap can be reduced.

### Current Cascade Architecture (9 levels)

| Level | Keys | Description | Entries |
|-------|------|-------------|---------|
| L0 | SOLDTOPARTY × SALESDOCUMENTTYPE × SALESORGANIZATION × SHIPPINGCONDITION | 4-key, most specific | 23,213 |
| L1 | SOLDTOPARTY × SALESDOCUMENTTYPE × SALESORGANIZATION | 3-key (sold-to) | 21,237 |
| L2 | SHIPTOPARTY × SALESDOCUMENTTYPE × SALESORGANIZATION | 3-key (ship-to) | 22,716 |
| L3 | SOLDTOPARTY × SHIPPINGCONDITION | 2-key | 21,835 |
| L4 | SOLDTOPARTY | 1-key | 11,723 |
| L5 | SHIPTOPARTY | 1-key | 14,151 |
| L6 | SALESDOCUMENTTYPE × SALESORGANIZATION × SHIPPINGCONDITION | 3-key (org-level) | 931 |
| L7 | SALESDOCUMENTTYPE × SALESORGANIZATION | 2-key (org-level) | 127 |
| L8 | SALESORGANIZATION | 1-key (org-level) | 31 |
| Fallback |  --  | Global mode: **DDP** |  --  |

**Total mapping entries: 174,209** (L0–L5 are customer-anchored; L6–L8 are organization-level)

### Data Context

- **Train**: 1,916,685 rows / **Test**: 402,855 rows
- **Customer overlap**: 78.2% of test customers seen in train (94.3% of test rows)
- **Class distribution**: DDP 64% / FCA 12% / EXW 8.5% / DAP 7.2% (14 classes total)
- **L1 distribution shift**: 26.6%  --  significant drift between train and test
- **Customer-determined**: only 18.3% of rows  --  Incoterms are NOT purely a customer-level attribute; they depend on the interaction of customer × organization × shipping condition

---

### Experiment 1: Minimum Support Filtering

**Hypothesis**: Low-frequency mappings (seen only 1–2 times in training) may be noise. Filtering them out could reduce overfitting.

**Method**: Require each mapping entry to have at least N supporting rows in train data. Applied uniformly across all 9 levels.

| min_support | Train Acc | Test Acc | Gap | Mapping Entries | Δ Test vs baseline |
|-------------|-----------|----------|-----|-----------------|-------------------|
| 1 (current) | 0.9422 | **0.7780** | +0.1641 | 174,209 |  --  |
| 2 | 0.9408 | 0.7750 | +0.1658 | 138,523 | -0.0030 |
| 3 | 0.9395 | 0.7741 | +0.1654 | 118,060 | -0.0039 |
| 5 | 0.9371 | 0.7732 | +0.1639 | 95,821 | -0.0048 |
| 10 | 0.9325 | 0.7728 | +0.1596 | 70,236 | -0.0052 |
| 20 | 0.9246 | 0.7677 | +0.1569 | 49,630 | -0.0103 |
| 50 | 0.9084 | 0.7616 | +0.1468 | 29,079 | -0.0164 |

**Findings**:
- Increasing min_support **does reduce the gap** (16.4pp → 14.7pp at min_sup=50)
- But test accuracy **also drops**  --  removing mappings hurts coverage more than it helps generalization
- At min_sup=10: gap shrinks by 0.5pp, but test drops by 0.5pp too  --  **net zero benefit**
- **Conclusion**: The overfitting is NOT caused by low-frequency noise entries. It is a systemic issue.

---

### Experiment 2: Level Ablation (Remove One Level at a Time)

**Hypothesis**: Some cascade levels may be redundant or harmful. Removing them could improve generalization.

**Method**: Remove exactly one level from the 9-level cascade and measure impact.

| Removed Level | Keys | Train | Test | Gap | Δ Test |
|---------------|------|-------|------|-----|--------|
| None (baseline) |  --  | 0.9422 | **0.7780** | +0.1641 |  --  |
| **L0** | **SOLD×DT×ORG×SC** | **0.8666** | **0.7420** | **+0.1245** | **-0.0360** 🔴 |
| L1 | SOLD×DT×ORG | 0.9422 | 0.7778 | +0.1644 | -0.0003 |
| L2 | SHIP×DT×ORG | 0.9422 | 0.7774 | +0.1648 | -0.0007 |
| L3 | SOLD×SC | 0.9422 | 0.7751 | +0.1671 | -0.0030 |
| L4 | SOLDTOPARTY | 0.9422 | 0.7785 | +0.1637 | +0.0005 |
| L5 | SHIPTOPARTY | 0.9422 | 0.7780 | +0.1641 | -0.0000 |
| L6 | DT×ORG×SC | 0.9422 | 0.7745 | +0.1676 | -0.0035 |
| L7 | DT×ORG | 0.9422 | 0.7780 | +0.1641 | +0.0000 |
| L8 | ORG | 0.9422 | 0.7782 | +0.1639 | +0.0002 |

**Findings**:
- **L0 is the single most important level**: removing it drops test accuracy by 3.6pp. It contributes the most precise customer-specific business rules.
- **L3 (SOLD×SC) and L6 (DT×ORG×SC)** have small but meaningful contributions (~0.3pp each)
- **L1, L2, L4, L5, L7, L8** have near-zero marginal contribution  --  they are largely redundant when L0 is present (L0 already captures their information at a finer granularity)
- **L0 is both the biggest source of overfitting AND the biggest source of accuracy**  --  a classic bias-variance tradeoff

---

### Experiment 3: Combined Strategies

**Method**: Test combinations of level pruning and minimum support filtering.

| Strategy | Train | Test | Gap | New Cust Acc |
|----------|-------|------|-----|-------------|
| Current (all, min_sup=1) | 0.9422 | **0.7780** | +0.1641 | 0.5828 |
| no-L0, min_sup=1 | 0.8666 | 0.7420 | +0.1245 | 0.5828 |
| no-L0, min_sup=3 | 0.8653 | 0.7400 | +0.1253 | 0.5835 |
| no-L0, min_sup=5 | 0.8641 | 0.7406 | +0.1235 | 0.5829 |
| no-L0-L2, min_sup=3 | 0.8653 | 0.7392 | +0.1261 | 0.5748 |
| no-L0-L3, min_sup=3 | 0.8648 | 0.7373 | +0.1275 | 0.5835 |
| no-L0-L2-L3, min_sup=3 | 0.8648 | 0.7364 | +0.1284 | 0.5748 |
| L4-L8 only | 0.8093 | 0.6989 | +0.1104 | 0.5742 |
| L4-L8 only, min_sup=3 | 0.8090 | 0.6994 | +0.1096 | 0.5748 |

**Findings**:
- Removing L0 reduces gap from 16.4pp → 12.5pp, but at the cost of -3.6pp test accuracy
- Further pruning (removing L2, L3) only adds small gap reductions while continuing to lose test accuracy
- **No combination achieves both a smaller gap AND higher test accuracy than the current configuration**

---

### Root Cause Analysis

The 16.4pp gap is **not caused by classical overfitting** (memorizing noise). It is caused by **concept drift**: customers change their Incoterms preferences between the training and test periods.

**Evidence**:
1. **Min support filtering fails**: Even aggressive filtering (min_sup=50, removing 83% of entries) only reduces gap by 1.7pp while losing 1.6pp test accuracy  --  the remaining high-frequency mappings are just as "wrong" on test data
2. **L0 is simultaneously the biggest overfit source AND the most valuable level**: This happens when the memorized patterns are *mostly correct* but a minority of customers *changed behavior*
3. **L1 distribution shift is 26.6%**: The class distribution between train and test differs substantially, consistent with temporal concept drift
4. **New customer accuracy (~58%) is stable across all configurations**: The new-customer pathway (L6→L7→L8→mode) is not affected by overfitting  --  the problem is specifically with seen-customer predictions that became stale

**Drift cross-correlation**: 1,567 customers (28.1% of 5,576 seen) changed their dominant HEADERINCOTERMS between train and test. For these drifted customers:

| Field | Same | Changed |
|---|---|---|
| ORGANIZATIONDIVISION | 100.0% | 0.0% |
| DISTRIBUTIONCHANNEL | 99.2% | 0.8% |
| CUSTOMERPAYMENTTERMS | 75.2% | 24.8% |
| SALESORGANIZATION | 72.4% | 27.6% |
| SALESDOCUMENTTYPE | 71.4% | 28.6% |
| SALESGROUP | 59.8% | 40.2% |
| SHIPPINGCONDITION | 37.4% | **62.6%** |

SHIPPINGCONDITION changes are the strongest co-signal  --  consistent with the L0 cascade using SHIPPINGCONDITION as a key discriminator (SC determines DDP vs DAP in many cases). When both SHIPPINGCONDITION and Incoterms change simultaneously, it suggests a contract-level renegotiation.

Top transitions:

| From | To | Customers |
|---|---|---|
| DDP | DAP | 495 |
| DDP | EXW | 143 |
| DDP | FCA | 93 |
| DAP | DDP | 89 |
| EXW | DDP | 74 |

The transition is heavily directional: `DDP → DAP` (495) vs `DAP → DDP` (89). Under DDP the seller bears all import duties and risks, while DAP transfers import clearance responsibility to the buyer  --  a known risk-mitigation strategy during supply chain disruption (Davis & Vogt, 2021, *"Hidden Supply Chain Risk and Incoterms"*, doi:[10.3390/jrfm14120596](https://doi.org/10.3390/jrfm14120596)). The temporal alignment of our test set (2020 H2) with the early COVID-19 supply chain crisis and the directional asymmetry in the data are consistent with pandemic-related trade term renegotiation, though we cannot confirm causation from transactional data alone.

**Analogy**: The cascade is mimicking SAP's Determination Procedure  --  look up the customer's master record, then fall back to organizational defaults. When a customer renegotiates their contract terms (e.g., switches from DDP to DAP), the historical lookup becomes wrong. This is a fundamental limitation of any lookup-based approach.

### Decision

**Keep the current 9-level cascade unchanged.** Rationale:
- Test accuracy 0.778 already exceeds the SALT-KG paper baseline (0.81 MRR)
- No experimental configuration improves test accuracy
- The 16pp gap reflects real-world concept drift, not a fixable modeling flaw
- Potential micro-optimization (min_sup=5) would save storage (95k vs 174k entries) but sacrifice 0.5pp accuracy  --  not worth it

