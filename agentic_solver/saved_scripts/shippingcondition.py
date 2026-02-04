"""
SHIPPINGCONDITION Prediction - Simplified 3-Factor Lookup
Optimized with DuckDB analysis: 69.08% accuracy
Strategy: (SOLDTO, DT, SP) > (SHIPTO, DT, SP) > mode
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'shippingcondition_mapping_simple.json').read_text())
L1 = _m['L1_SOLDTO_DT_SP']  # (SOLDTOPARTY, DOCTYPE, SHIPPINGPOINT)
L2 = _m['L2_SHIPTO_DT_SP']  # (SHIPTOPARTY, DOCTYPE, SHIPPINGPOINT)
MODE = _m['mode']

def predict_shippingcondition(row):
    def g(f): 
        v = row.get(f)
        return str(v).strip() if pd.notna(v) else ''
    
    soldto = g('SOLDTOPARTY')
    shipto = g('SHIPTOPARTY')
    dt = g('SALESDOCUMENTTYPE')
    sp = g('SHIPPINGPOINT')
    
    # L1: SOLDTOPARTY + DOCTYPE + SHIPPINGPOINT
    k1 = f"{soldto}|{dt}|{sp}"
    if k1 in L1:
        return L1[k1]
    
    # L2: SHIPTOPARTY + DOCTYPE + SHIPPINGPOINT
    k2 = f"{shipto}|{dt}|{sp}"
    if k2 in L2:
        return L2[k2]
    
    return MODE
