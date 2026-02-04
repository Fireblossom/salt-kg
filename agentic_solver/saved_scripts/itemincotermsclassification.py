"""
ITEMINCOTERMSCLASSIFICATION Prediction - 5-level cascade with SHIPPINGCONDITION
MRR: 0.840 (same as HEADER)
Strategy: (SOLDTO+DT+ORG+SC) > (SOLDTO+DT+ORG) > (SOLDTO+DT) > SOLDTO > ORG
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'itemincotermsclassification_mapping.json').read_text())
L0, L1, L2, L3, L4, MODE = _m['L0'], _m['L1'], _m['L2'], _m['L3'], _m['L4'], _m['mode']

def predict_itemincotermsclassification(row):
    def g(f): v = row.get(f); return str(v).strip() if pd.notna(v) else ''
    
    soldto, dt, org, sc = g('SOLDTOPARTY'), g('SALESDOCUMENTTYPE'), g('SALESORGANIZATION'), g('SHIPPINGCONDITION')
    
    k0 = f"{soldto}|{dt}|{org}|{sc}"
    if k0 in L0: return L0[k0]
    
    k1 = f"{soldto}|{dt}|{org}"
    if k1 in L1: return L1[k1]
    
    k2 = f"{soldto}|{dt}"
    if k2 in L2: return L2[k2]
    
    if soldto in L3: return L3[soldto]
    if org in L4: return L4[org]
    
    return MODE
