"""
SHIPPINGPOINT Prediction - Multi-Factor Lookup
Uses SHIPPINGCONDITION and SALESDOCUMENTTYPE for discrimination
"""
import pandas as pd
import json
from pathlib import Path

_mapping = json.loads((Path(__file__).parent / 'shippingpoint_mapping.json').read_text())
COMPOSITE = _mapping['composite']
VARIANT = _mapping['variant']
SC18 = _mapping.get('sc18', {})
MODE = _mapping['mode']

def predict_shippingpoint(row):
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    def safe_int(val, default=0):
        try:
            return int(val) if val and str(val).isdigit() else default
        except:
            return default
    
    plant = safe_get('PLANT')
    ship_cond = safe_int(safe_get('SHIPPINGCONDITION'))
    doc_type = safe_get('SALESDOCUMENTTYPE')
    
    # Special handling: SHIPPINGCONDITION=18 has specific mappings
    if ship_cond == 18 and plant in SC18:
        return SC18[plant]
    
    # Determine if this is a "service" type (virtual shipping point)
    is_service = (ship_cond >= 94) or (doc_type in ['ZMUN', 'ZMUT'])
    
    # Composite lookup: (PLANT, is_service)
    key = f"{plant}|{int(is_service)}"
    if key in COMPOSITE:
        result = COMPOSITE[key]
        if result:  # Non-empty result
            return result
    
    # Special handling for SHIPPINGCONDITION 18-20 (variant cases)
    if 18 <= ship_cond <= 20:
        if plant in VARIANT:
            return VARIANT[plant]
    
    # Fallback: check if plant has any mapping
    for is_svc in [1, 0]:
        fallback_key = f"{plant}|{is_svc}"
        if fallback_key in COMPOSITE:
            result = COMPOSITE[fallback_key]
            if result:
                return result
    
    return MODE
