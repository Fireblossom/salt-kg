"""
SALESGROUP Prediction - Drift-robust cascade with Sales Area signals
Cascade:
  SOLDTO+DT+ORG+CHANNEL+DIV (L0) →
  SOLDTO+DT (L1) →
  SOLDTO (L2) →
  DT+ORG+CHANNEL+DIV (L3) →
  ORG+CHANNEL+DIV (L4) →
  ORG (L5) →
  mode
"""
import pandas as pd
import json
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'salesgroup_mapping.json').read_text())
L0 = _m['L0_SOLDTO_DT_SA']
L1 = _m['L1_SOLDTO_DT']
L2 = _m['L2_SOLDTO']
L3 = _m['L3_DT_SA']
L4 = _m['L4_SA']
L5 = _m['L5_ORG']
MODE = _m['mode']

def predict_salesgroup(row):
    def g(f):
        v = row.get(f)
        return str(v).strip() if pd.notna(v) else ''

    soldto = g('SOLDTOPARTY')
    dt = g('SALESDOCUMENTTYPE')
    org = g('SALESORGANIZATION')
    channel = g('DISTRIBUTIONCHANNEL')
    div = g('ORGANIZATIONDIVISION')

    # L0: SOLDTOPARTY + DOCTYPE + SALES AREA
    k0 = f"{soldto}|{dt}|{org}|{channel}|{div}"
    if k0 in L0: return L0[k0]

    # L1: SOLDTOPARTY + DOCTYPE
    k1 = f"{soldto}|{dt}"
    if k1 in L1: return L1[k1]

    # L2: SOLDTOPARTY
    if soldto in L2: return L2[soldto]

    # L3: DOCTYPE + SALES AREA
    k3 = f"{dt}|{org}|{channel}|{div}"
    if k3 in L3: return L3[k3]

    # L4: SALES AREA
    k4 = f"{org}|{channel}|{div}"
    if k4 in L4: return L4[k4]

    # L5: ORG
    if org in L5: return L5[org]

    return MODE
