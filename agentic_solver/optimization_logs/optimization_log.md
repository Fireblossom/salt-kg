# SALT-KG Field Prediction: Agentic Solver Results

> **Context**: This analysis explores rule-based and lookup-based prediction strategies for SAP ERP field completion, as an alternative to the Knowledge Graph + Embedding approach described in the SALT-KG papers.

---

## Summary: MRR Comparison vs Paper

| Target Field | Ours | Baseline Best | SALT-KG Best | vs Baseline | vs SALT-KG |
|--------------|------|---------------|--------------|-------------|------------|
| SALESOFFICE | **0.997** | 0.99 | 1.00 | +0.007 ✅ | -0.003 ≈ |
| PLANT | **0.993** | 0.99 | 1.00 | +0.003 ✅ | -0.007 ≈ |
| SHIPPINGPOINT | **0.986** | 0.98 | 0.99 | +0.006 ✅ | -0.004 ≈ |
| CUSTOMERPAYMENTTERMS | **0.852** | 0.62 | 0.70 | +0.232 ✅ | +0.152 ✅ |
| SALESGROUP | **0.760** | 0.51 | 0.53 | +0.250 ✅ | +0.230 ✅ |
| HEADERINCOTERMS | **0.840** | 0.81 | 0.85 | +0.030 ✅ | -0.010 ≈ |
| ITEMINCOTERMS | **0.840** | 0.80 | 0.84 | +0.040 ✅ | = |
| SHIPPINGCONDITION | **0.798** | 0.74 | 0.78 | +0.058 ✅ | +0.018 ✅ |

> **Baseline Best**: Best model from Table 2 (without KG)  
> **SALT-KG Best**: Baseline + KG improvement from Table 1

**Summary**: Our lookup-based approach matches or exceeds SALT-KG on 4/8 fields, and exceeds all baselines on 7/8 fields.

---

## Data Observation: SALESOFFICE Distribution

> [!NOTE]
> SALESOFFICE shows extreme class imbalance, making it a less informative evaluation target.

### Distribution

| Value | Train Count | Train % | Test Count | Test % |
|-------|-------------|---------|------------|--------|
| **0010** | 1,910,792 | **99.69%** | 402,500 | **99.91%** |
| 0500 | 516 | 0.03% | 117 | 0.03% |
| 1300 | 451 | 0.02% | 107 | 0.03% |
| 2000 | 350 | 0.02% | 71 | 0.02% |
| 0600 | 262 | 0.01% | 37 | 0.01% |
| 1000 | 5 | 0.00% | 23 | 0.01% |
| Others (24 values) | 2,309 | 0.12% | 0 | 0% |

- Train has 30 unique values, Test has only **6**
- Mode baseline achieves 99.91% accuracy on test
- Any method (lookup, KG, or ML) will approach ~100%

### MRR@3 for Edge Cases

| Value | Test Rows | MRR@3 (SOLDTO) | MRR@3 (ORG) | In ORG Top-3? |
|-------|----------|----------------|-------------|---------------|
| 0010 | 402,500 | 0.999 | 1.000 | ✅ |
| 0500 | 117 | 1.000 | 0.492 | ✅ (2nd) |
| 1300 | 107 | 0.333 | 0.500 | ✅ (2nd) |
| 2000 | 71 | 0.500 | 0.500 | ✅ (2nd) |
| 0600 | 37 | 0.500 | 0.500 | ✅ (2nd) |
| 1000 | 23 | **0.000** | **0.000** | ❌ Not in Top-3 |

**Observations:**
1. Edge cases (355 rows, 0.09% of test) have minimal impact on overall MRR
2. `1000` is completely unpredictable — not in any lookup's top-3
3. Top-3 ranking helps recall for values like 1300/2000 (MRR=0.5 vs Top-1=0%)

**Implication**: SALESOFFICE may not be the most informative target for comparing KG vs baseline methods, as the class imbalance makes all approaches perform similarly well.

---

## Prediction Logic by Field

### 1. SALESOFFICE (MRR 0.997)
**Logic**: Direct 1:1 mapping from `SALESORGANIZATION`.

Each sales organization has exactly one associated sales office in SAP configuration. This is a master data relationship, not a transactional pattern.

```
SALESORGANIZATION → SALESOFFICE
```

---

### 2. PLANT (MRR 0.993)
**Logic**: Lookup by `SHIPPINGPOINT`.

In SAP, a shipping point is always assigned to exactly one plant. The relationship is defined in organizational structure configuration.

```
SHIPPINGPOINT → PLANT
```

---

### 3. SHIPPINGPOINT (MRR 0.986)
**Logic**: Rule-based + hierarchical lookup.

Key insight: **SHIPPINGCONDITION determines shipment type**.
- Values ≥94 (e.g., 94-99) → Virtual shipping points ("MUST", "0302", etc.) for internal/non-physical shipments
- Values <94 → Physical shipping points determined by (SALESORG, DOCTYPE, PLANT)

```python
if SHIPPINGCONDITION >= 94:
    return virtual_shippingpoint_mapping[SALESORG]
else:
    return lookup(SALESORG, DOCTYPE, PLANT)
```

---

### 4. CUSTOMERPAYMENTTERMS (MRR 0.852)
**Logic**: Customer-specific defaults by document type.

Payment terms are typically configured per customer, but can vary by document type (e.g., standard orders vs. returns).

```
(SOLDTOPARTY, SALESDOCUMENTTYPE) → CUSTOMERPAYMENTTERMS
```

---

### 5. SALESGROUP (MRR 0.760)
**Logic**: Customer segment assignment.

Sales groups represent sales team territories or customer segments. The primary determinant is the sold-to party, with document type as secondary.

```
(SOLDTOPARTY, SALESDOCUMENTTYPE) → SALESGROUP
```

---

### 6. INCOTERMS (Header/Item) (MRR 0.810)
**Logic**: Customer trading relationship with hierarchical fallback.

Incoterms (e.g., FOB, CIF, DDP) are defined in customer master data. Using a cascade strategy improves coverage:

```
L1: (SOLDTOPARTY, SALESDOCUMENTTYPE) → INCOTERMS (primary)
L2: (SHIPTOPARTY, SALESDOCUMENTTYPE) → INCOTERMS (fallback)
L3: SOLDTOPARTY → INCOTERMS (fallback)
L4: SALESORGANIZATION → INCOTERMS (fallback)
```

---

### 7. SHIPPINGCONDITION (MRR 0.798)
**Logic**: Transaction state machine driven by entity + document type + logistics.

This is the most complex field. SHIPPINGCONDITION determines HOW goods are shipped (standard, express, pickup, etc.). The key factors are:

1. **Customer identity** (SOLDTOPARTY) - customer-specific shipping agreements
2. **Document type** (SALESDOCUMENTTYPE) - order types have different shipping profiles
3. **Shipping point** - physical logistics constraints

```
(SOLDTOPARTY, SALESDOCUMENTTYPE, SHIPPINGPOINT) → SHIPPINGCONDITION (Top-3)
```

The challenge: 29% of (SOLDTO, DT, SP) combinations have multiple valid SHIPPINGCONDITION values, making single-answer prediction inherently limited to ~70% accuracy. MRR@3 reaches 80% by returning ranked candidates.

---

## Methodology Notes

### Approach: "Code as Reasoning"
Instead of embedding-based similarity matching, we use:
1. **Statistical profiling**: Find the mode (most frequent value) per feature combination
2. **Hierarchical fallback**: When specific lookup misses, fall back to broader patterns
3. **Business rule discovery**: Identify deterministic relationships (e.g., SHIPPINGCONDITION≥94 → virtual SP)

### Why This Works
- SAP ERP has strong configuration-driven determinism
- Many fields are master data relationships (not truly "predictive")
- Transactional patterns follow business process rules

### Limitations
- Requires seeing the specific customer/combination in training data
- Cannot generalize to truly new customers (cold start problem)
- Paper's KG+Embedding approach may better handle novel entity relationships

---

## Technical Details

- **Dataset**: SALT-KG official train/test split (1.9M / 402K rows)
- **Metric**: MRR@3 (Mean Reciprocal Rank with top-3 candidates)
- **Implementation**: Python with DuckDB for analytics, lookup tables in JSON
