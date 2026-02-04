"""
PLANT Prediction - Lookup based
Primary: SHIPPINGPOINT, Fallback: SALESORGANIZATION
"""
import pandas as pd
import json
from pathlib import Path

_mapping = json.loads((Path(__file__).parent / 'plant_mapping.json').read_text())
LOOKUP1 = _mapping['LOOKUP1']
LOOKUP2 = _mapping['LOOKUP2']
MODE = _mapping['mode']

def predict_plant(row):
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    k1 = safe_get('SHIPPINGPOINT')
    if k1 in LOOKUP1:
        return LOOKUP1[k1]
    
    k2 = safe_get('SALESORGANIZATION')
    if k2 in LOOKUP2:
        return LOOKUP2[k2]
    
    return MODE
