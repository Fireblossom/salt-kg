"""
HEADERINCOTERMSCLASSIFICATION Prediction - Anti-overfitting cascade with SHIPTOPARTY
Cascade: SOLDTO+DT+ORG+SC (ms≥5) → SOLDTO+DT+ORG (ms≥3) → SHIPTO+DT+ORG (ms≥3)
       → SOLDTO+SC (ms≥3) → SOLDTO (ms≥2) → SHIPTO (ms≥2)
       → DT+ORG+SC → DT+ORG → ORG → mode
Key insight: SHIPTOPARTY added because Incoterms relate to delivery destination,
and 35% of rows have SHIPTO ≠ SOLDTO
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'headerincotermsclassification_mapping.json').read_text())
L0 = _m['L0_SOLDTO_DT_ORG_SC']
L1 = _m['L1_SOLDTO_DT_ORG']
L2 = _m['L2_SHIPTO_DT_ORG']
L3 = _m['L3_SOLDTO_SC']
L4 = _m['L4_SOLDTO']
L5 = _m['L5_SHIPTO']
L6 = _m['L6_DT_ORG_SC']
L7 = _m['L7_DT_ORG']
L8 = _m['L8_ORG']
MODE = _m['mode']

def predict_headerincotermsclassification(row):
    def g(f):
        v = row.get(f)
        return str(v).strip() if pd.notna(v) else ''

    soldto = g('SOLDTOPARTY')
    shipto = g('SHIPTOPARTY')
    dt = g('SALESDOCUMENTTYPE')
    org = g('SALESORGANIZATION')
    sc = g('SHIPPINGCONDITION')

    # L0: SOLDTO+DT+ORG+SC (min_support=5)
    k0 = f"{soldto}|{dt}|{org}|{sc}"
    if k0 in L0: return L0[k0]

    # L1: SOLDTO+DT+ORG (min_support=3)
    k1 = f"{soldto}|{dt}|{org}"
    if k1 in L1: return L1[k1]

    # L2: SHIPTO+DT+ORG (min_support=3) — delivery destination anchor
    k2 = f"{shipto}|{dt}|{org}"
    if k2 in L2: return L2[k2]

    # L3: SOLDTO+SC (min_support=3)
    k3 = f"{soldto}|{sc}"
    if k3 in L3: return L3[k3]

    # L4: SOLDTO only (min_support=2)
    if soldto in L4: return L4[soldto]

    # L5: SHIPTO only (min_support=2)
    if shipto in L5: return L5[shipto]

    # L6: DT+ORG+SC (structural — no entity dependency)
    k6 = f"{dt}|{org}|{sc}"
    if k6 in L6: return L6[k6]

    # L7: DT+ORG
    k7 = f"{dt}|{org}"
    if k7 in L7: return L7[k7]

    # L8: ORG
    if org in L8: return L8[org]

    return MODE
