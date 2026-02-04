"""
Target-Specific Prompt Templates for SALT-KG Prediction Tasks

Based on the SALT paper, there are 8 target fields:
1. SalesOffice - Physical location for sales (very imbalanced, 99% dominated)
2. SalesGroup - Group of salespeople (high cardinality: 589 unique values)
3. CustomerPaymentTerms - Payment conditions (158 unique values)
4. ShippingCondition - Logistics terms (56 unique values)
5. Plant - Production/storage facility (39 unique values)
6. ShippingPoint - Dispatch location (97 unique values)
7. IncotermsClassification (Header) - International commercial terms (14 unique values)
8. IncotermsClassification (Item) - International commercial terms (14 unique values)
"""

# ==============================================================================
# GENERIC PROMPT TEMPLATE
# ==============================================================================
GENERIC_PROMPT_TEMPLATE = """
Generate a Python prediction function for: {target_field}

## DATA ANALYSIS:
{target_distribution}

## SAMPLE DATA:
{sample_data}

## BUSINESS CONTEXT:
{kg_context}

## REQUIRED CODE STRUCTURE:
```python
def predict_{target_field_lower}(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # Your prediction logic here
    # Use lookup tables based on the most predictive features
    
    return 'default_value'
```

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# SALESOFFICE - Dominated by single value (99%)
# ==============================================================================
SALESOFFICE_PROMPT = """
Generate a Python prediction function for: SALESOFFICE

## CRITICAL INSIGHT:
- SALESOFFICE is EXTREMELY imbalanced: one value dominates 99%+ of data
- The baseline (majority class) achieves MRR 0.99 according to the paper
- Simple majority prediction is nearly optimal

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
- Return the mode (most common value) for almost all cases
- Only use minimal lookup for edge cases

## REQUIRED CODE:
```python
def predict_salesoffice(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # SALESOFFICE is dominated by one value
    # Simple mode prediction achieves 99%+ accuracy
    MODE_VALUE = '{mode_value}'  # Fill from analysis
    
    return MODE_VALUE
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# SALESGROUP - High cardinality (589 unique), hardest to predict (MRR 0.46)
# ==============================================================================
SALESGROUP_PROMPT = """
Generate a Python prediction function for: SALESGROUP

## CRITICAL INSIGHT:
- SALESGROUP has HIGH CARDINALITY: 589 unique values
- Best predictor: SALESORGANIZATION (see ORG_LOOKUP below)
- You MUST copy the EXACT ORG_LOOKUP from the DATA ANALYSIS section!

## DATA ANALYSIS (COPY THIS LOOKUP TABLE INTO YOUR CODE!):
{target_distribution}

## MANDATORY: YOUR CODE MUST USE THE ORG_LOOKUP FROM ABOVE!
The ORG_LOOKUP table in the DATA ANALYSIS section maps SALESORGANIZATION → SALESGROUP.
You MUST copy this exact dictionary into your code. DO NOT make up values!

## REQUIRED CODE STRUCTURE:
```python
def predict_salesgroup(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # IMPORTANT: Copy the EXACT ORG_LOOKUP from DATA ANALYSIS above!
    ORG_LOOKUP = {{
        '0010': '999',  # Copy all entries from above!
        '0300': '301',
        '0700': '219',
        # ... (COPY ALL ENTRIES FROM THE DATA ANALYSIS SECTION!)
    }}
    
    org = safe_get('SALESORGANIZATION')
    
    if org in ORG_LOOKUP:
        return ORG_LOOKUP[org]
    
    return '999'  # Global mode (from "Most common value")
```

## YOUR TASK:
1. COPY ALL entries from the ORG_LOOKUP in DATA ANALYSIS into your code
2. Use SALESORGANIZATION as the lookup key
3. Return '999' as fallback (the global mode)

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# CUSTOMERPAYMENTTERMS - 158 unique values
# ==============================================================================
PAYMENTTERMS_PROMPT = """
Generate a Python prediction function for: CUSTOMERPAYMENTTERMS

## CRITICAL INSIGHT:
- CUSTOMERPAYMENTTERMS has 158 unique values
- Best predictor: SOLDTOPARTY - customers have preferred payment terms
- Secondary: SALESORGANIZATION + TRANSACTIONCURRENCY

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
1. SOLDTOPARTY → typical payment terms
2. SALESORGANIZATION → default terms for org
3. Global mode fallback

## REQUIRED CODE:
```python
def predict_customerpaymentterms(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    PARTY_LOOKUP = {{
        # 'SOLDTOPARTY': 'PAYMENTTERMS'
    }}
    
    ORG_LOOKUP = {{
        # 'SALESORGANIZATION': 'PAYMENTTERMS'
    }}
    
    party = safe_get('SOLDTOPARTY')
    org = safe_get('SALESORGANIZATION')
    
    if party in PARTY_LOOKUP:
        return PARTY_LOOKUP[party]
    if org in ORG_LOOKUP:
        return ORG_LOOKUP[org]
    
    return 'NT30'  # Common default
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# SHIPPINGCONDITION - 56 unique values
# ==============================================================================
SHIPPINGCONDITION_PROMPT = """
Generate a Python prediction function for: SHIPPINGCONDITION

## CRITICAL INSIGHT:
- SHIPPINGCONDITION has 56 unique values
- Best predictors: SALESORGANIZATION, SHIPPINGPOINT
- Geography-related: linked to logistics infrastructure

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
1. SHIPPINGPOINT → determines shipping condition
2. SALESORGANIZATION → regional defaults
3. Global mode fallback

## REQUIRED CODE:
```python
def predict_shippingcondition(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    SP_LOOKUP = {{
        # 'SHIPPINGPOINT': 'SHIPPINGCONDITION'
    }}
    
    ORG_LOOKUP = {{
        # 'SALESORGANIZATION': 'SHIPPINGCONDITION'
    }}
    
    sp = safe_get('SHIPPINGPOINT')
    org = safe_get('SALESORGANIZATION')
    
    if sp in SP_LOOKUP:
        return SP_LOOKUP[sp]
    if org in ORG_LOOKUP:
        return ORG_LOOKUP[org]
    
    return '01'  # Standard
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# PLANT - 39 unique values (near-perfect prediction: MRR 0.99)
# ==============================================================================
PLANT_PROMPT = """
Generate a Python prediction function for: PLANT

## CRITICAL INSIGHT:
- PLANT has only 39 unique values
- HIGHLY PREDICTABLE: MRR 0.99 in paper
- Best predictor: SHIPPINGPOINT → PLANT is direct SAP organizational mapping

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
- SHIPPINGPOINT directly determines PLANT in SAP
- This is a deterministic organizational relationship

## REQUIRED CODE:
```python
def predict_plant(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # Direct organizational mapping: SHIPPINGPOINT → PLANT
    SP_TO_PLANT = {{
        # 'SHIPPINGPOINT': 'PLANT'
        # Copy mapping from training data
    }}
    
    sp = safe_get('SHIPPINGPOINT')
    
    if sp in SP_TO_PLANT:
        return SP_TO_PLANT[sp]
    
    return '1000'  # Default plant
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# SHIPPINGPOINT - 97 unique values (MRR 0.97)
# ==============================================================================
SHIPPINGPOINT_PROMPT = """
Generate a Python prediction function for: SHIPPINGPOINT

## CRITICAL INSIGHT:
- SHIPPINGPOINT has 97 unique values
- HIGHLY PREDICTABLE: MRR 0.97 in paper
- Best predictors: PLANT, SALESORGANIZATION (organizational structure)

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
- PLANT → SHIPPINGPOINT (reverse of Plant prediction)
- SALESORGANIZATION provides regional context

## REQUIRED CODE:
```python
def predict_shippingpoint(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # PLANT → SHIPPINGPOINT mapping
    PLANT_TO_SP = {{
        # 'PLANT': 'SHIPPINGPOINT'
    }}
    
    ORG_TO_SP = {{
        # 'SALESORGANIZATION': 'SHIPPINGPOINT'
    }}
    
    plant = safe_get('PLANT')
    org = safe_get('SALESORGANIZATION')
    
    if plant in PLANT_TO_SP:
        return PLANT_TO_SP[plant]
    if org in ORG_TO_SP:
        return ORG_TO_SP[org]
    
    return '0001'  # Default
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# INCOTERMSCLASSIFICATION - 14 unique values (MRR 0.75-0.77)
# ==============================================================================
INCOTERMS_PROMPT = """
Generate a Python prediction function for: INCOTERMSCLASSIFICATION

## CRITICAL INSIGHT:
- INCOTERMSCLASSIFICATION has only 14 unique values
- International commercial terms (ICC standard)
- Best predictors: SOLDTOPARTY (customer), SHIPTO country/region

## DATA ANALYSIS:
{target_distribution}

## PREDICTION STRATEGY:
1. SOLDTOPARTY → Customer's typical incoterms
2. SHIPTOCOUNTRY → Country-based defaults
3. SALESORGANIZATION → Regional defaults

## REQUIRED CODE:
```python
def predict_incotermsclassification(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # Customer → typical Incoterms
    PARTY_LOOKUP = {{
        # 'SOLDTOPARTY': 'INCOTERMS'
    }}
    
    # Country → default Incoterms
    COUNTRY_LOOKUP = {{
        # 'COUNTRY': 'INCOTERMS'
    }}
    
    party = safe_get('SOLDTOPARTY')
    country = safe_get('SHIPTOCOUNTRY')
    
    if party in PARTY_LOOKUP:
        return PARTY_LOOKUP[party]
    if country in COUNTRY_LOOKUP:
        return COUNTRY_LOOKUP[country]
    
    return 'EXW'  # Ex Works (common default)
```

## SAMPLE DATA:
{sample_data}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# ==============================================================================
# PROMPT REGISTRY - Maps target field to specific prompt
# ==============================================================================
TARGET_PROMPT_REGISTRY = {
    'SALESOFFICE': SALESOFFICE_PROMPT,
    'SALESGROUP': SALESGROUP_PROMPT,
    'CUSTOMERPAYMENTTERMS': PAYMENTTERMS_PROMPT,
    'SHIPPINGCONDITION': SHIPPINGCONDITION_PROMPT,
    'PLANT': PLANT_PROMPT,
    'SHIPPINGPOINT': SHIPPINGPOINT_PROMPT,
    'INCOTERMSCLASSIFICATION': INCOTERMS_PROMPT,
    # Aliases
    'PAYMENTTERMS': PAYMENTTERMS_PROMPT,
    'INCOTERMS': INCOTERMS_PROMPT,
}


def get_prompt_for_target(target_field: str) -> str:
    """
    Get the appropriate prompt template for a target field.
    
    Args:
        target_field: Name of the target field (case-insensitive)
        
    Returns:
        Prompt template string
    """
    target_upper = target_field.upper()
    
    if target_upper in TARGET_PROMPT_REGISTRY:
        return TARGET_PROMPT_REGISTRY[target_upper]
    
    # Default to generic prompt
    return GENERIC_PROMPT_TEMPLATE
