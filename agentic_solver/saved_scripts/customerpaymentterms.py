"""
CUSTOMERPAYMENTTERMS Prediction - Anti-overfitting cascade
Cascade: SOLDTO+DT (ms≥3) → SOLDTO (ms≥2) → DT+ORG → ORG → mode
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'customerpaymentterms_mapping.json').read_text())
L0 = _m['L0_SOLDTO_DT']
L1 = _m['L1_SOLDTO']
L2 = _m['L2_DT_ORG']
L3 = _m['L3_ORG']
MODE = _m['mode']

def predict_customerpaymentterms(row):
    def g(f):
        v = row.get(f)
        return str(v).strip() if pd.notna(v) else ''

    soldto = g('SOLDTOPARTY')
    dt = g('SALESDOCUMENTTYPE')
    org = g('SALESORGANIZATION')

    # L0: SOLDTOPARTY + DOCTYPE (min_support=3)
    k0 = f"{soldto}|{dt}"
    if k0 in L0: return L0[k0]

    # L1: SOLDTOPARTY (min_support=2)
    if soldto in L1: return L1[soldto]

    # L2: DOCTYPE + ORG (structural fallback)
    k2 = f"{dt}|{org}"
    if k2 in L2: return L2[k2]

    # L3: ORG only
    if org in L3: return L3[org]

    return MODE
