"""
SHIPPINGCONDITION Prediction - Plant-enhanced hybrid cascade
Cascade:
  SOLDTO+DT+SP (ms>=3) ->
  SHIPTO+DT+SP (ms>=3) ->
  DT+PLANT+SP ->
  DT+SP ->
  SP ->
  SOLDTO+DT (ms>=2) ->
  mode
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'shippingcondition_mapping_simple.json').read_text())
L0 = _m['L0_SOLDTO_DT_SP']
L1 = _m['L1_SHIPTO_DT_SP']
L2 = _m['L2_DT_PLANT_SP']
L3 = _m['L3_DT_SP']
L4 = _m['L4_SP']
L5 = _m['L5_SOLDTO_DT']
MODE = _m['mode']

def predict_shippingcondition(row):
    def g(f):
        v = row.get(f)
        return str(v).strip() if pd.notna(v) else ''

    soldto = g('SOLDTOPARTY')
    shipto = g('SHIPTOPARTY')
    dt = g('SALESDOCUMENTTYPE')
    sp = g('SHIPPINGPOINT')
    plant = g('PLANT')

    # L0: SOLDTOPARTY + DOCTYPE + SHIPPINGPOINT (min_support=3)
    k0 = f"{soldto}|{dt}|{sp}"
    if k0 in L0: return L0[k0]

    # L1: SHIPTOPARTY + DOCTYPE + SHIPPINGPOINT (min_support=3)
    k1 = f"{shipto}|{dt}|{sp}"
    if k1 in L1: return L1[k1]

    # L2: DOCTYPE + PLANT + SHIPPINGPOINT (operational structural fallback)
    k2 = f"{dt}|{plant}|{sp}"
    if k2 in L2: return L2[k2]

    # L3: DOCTYPE + SHIPPINGPOINT
    k3 = f"{dt}|{sp}"
    if k3 in L3: return L3[k3]

    # L4: SHIPPINGPOINT
    if sp in L4: return L4[sp]

    # L5: SOLDTOPARTY + DOCTYPE (customer fallback)
    k5 = f"{soldto}|{dt}"
    if k5 in L5: return L5[k5]

    return MODE
