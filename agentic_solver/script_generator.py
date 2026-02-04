"""
Script Generator - LLM-based Python Code Generator

Uses an LLM (OpenAI/Anthropic) to generate Python prediction functions
based on business knowledge from the Knowledge Graph.

This is the "compiler" that translates natural language business rules
into executable Python code.
"""

import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Try to import LLM clients
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class GeneratedScript:
    """Container for a generated prediction script"""
    code: str
    function_name: str
    target_field: str
    explanation: str
    confidence: float  # 0-1, how confident the LLM is in the logic
    required_columns: List[str]

    def __str__(self):
        return f"GeneratedScript(target={self.target_field}, func={self.function_name})"


SYSTEM_PROMPT = """You are an expert SAP/ERP business analyst, data scientist, and Python programmer.

Your task is to generate SOPHISTICATED Python prediction functions that combine:
1. Business domain knowledge from SAP Knowledge Graph
2. Statistical patterns learned from the sample data
3. Hybrid rule-based + data-driven approaches

## YOUR APPROACH SHOULD BE:

### For CATEGORICAL fields (like SALESGROUP, PAYMENTTERMS):
1. **Analyze the value distribution** - identify dominant values and their conditions
2. **Build decision trees** based on multiple factors (not just one if/else)
3. **Create lookup tables** mapping combinations of input fields to outputs
4. **Use hierarchical rules**: Organization → Division → Channel → Customer Type
5. **Include fallback logic** based on most common value per segment

### For NUMERICAL fields (like amounts, quantities, dates):
1. **Embed simple regression coefficients** directly in the code
2. **Use weighted averages** based on similar records
3. **Apply business formulas** (e.g., NetAmount = GrossAmount * (1 - DiscountRate))
4. **Include bounds checking** based on observed min/max values

### For DATE fields:
1. **Calculate based on related dates** (e.g., DeliveryDate = OrderDate + LeadTime)
2. **Use business calendar logic** (skip weekends, holidays)
3. **Apply SLA rules** from the Knowledge Graph

## CODE STRUCTURE REQUIREMENTS:

```python
def predict_FIELDNAME(row):
    \"\"\"
    Multi-factor prediction for FIELDNAME.

    Decision Factors:
    - Factor 1: Description
    - Factor 2: Description

    Learned Patterns:
    - Pattern 1 from data analysis
    - Pattern 2 from data analysis
    \"\"\"
    import pandas as pd
    import numpy as np
    from collections import defaultdict

    # ========== HELPER FUNCTIONS ==========
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default

    def safe_numeric(field, default=0.0):
        val = row.get(field)
        try:
            return float(val) if pd.notna(val) else default
        except:
            return default

    # ========== LEARNED LOOKUP TABLES ==========
    # Built from analyzing sample data patterns
    COMBO_LOOKUP = {
        ('value1', 'value2'): 'result1',
        ('value3', 'value4'): 'result2',
    }

    # ========== BUSINESS RULES FROM KG ==========
    # Rule 1: Description from KG
    # Rule 2: Description from KG

    # ========== MULTI-FACTOR DECISION LOGIC ==========
    # Extract all relevant fields
    field1 = safe_get('FIELD1')
    field2 = safe_get('FIELD2')
    numeric_field = safe_numeric('NUMERIC_FIELD')

    # Try exact combination lookup first
    combo_key = (field1, field2)
    if combo_key in COMBO_LOOKUP:
        return COMBO_LOOKUP[combo_key]

    # Hierarchical decision tree
    if condition1:
        if sub_condition:
            return value1
        else:
            return value2
    elif condition2:
        # Numeric threshold logic
        if numeric_field > threshold:
            return value3
        else:
            return value4

    # ========== FALLBACK: STATISTICAL DEFAULT ==========
    # Based on overall distribution analysis
    return most_common_value
```

## CRITICAL REQUIREMENTS:
1. **NO EXTERNAL MODEL FILES** - embed all learned parameters directly in code
2. **HANDLE ALL EDGE CASES** - None values, empty strings, type mismatches
3. **USE MULTIPLE FACTORS** - never rely on just one field
4. **INCLUDE CONFIDENCE SCORING** - if logic is weak, return None instead of guessing
5. **ADD DETAILED COMMENTS** - explain each decision branch

## OUTPUT FORMAT:
Return your response as JSON:
{
    "function_name": "predict_<target_field>",
    "code": "def predict_xxx(row):\\n    ...",
    "explanation": "Detailed explanation of the multi-factor logic",
    "confidence": 0.8,
    "required_columns": ["COL1", "COL2", "COL3"]
}
"""

USER_PROMPT_TEMPLATE = """
Generate a Python prediction function for: {target_field}

## KEY INSIGHT - READ CAREFULLY:
**SALESORGANIZATION is the PRIMARY predictor.** SALESOFFICE is nearly useless (99.7% of values are '0010').
The mapping is: SALESORGANIZATION -> TARGET_VALUE

## MAPPING TABLE (from data analysis):
{target_distribution}

## REQUIRED CODE STRUCTURE:
```python
def predict_{target_field_lower}(row):
    import pandas as pd
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # Primary lookup: SALESORGANIZATION -> TARGET
    ORG_LOOKUP = {{
        # COPY THE MAPPING FROM ABOVE - example entries:
        # '0010': '999',  # most common for org 0010
        # '0400': 'AG',   # most common for org 0400
        # ... add ALL mappings from the table above
    }}
    
    sales_org = safe_get('SALESORGANIZATION')
    
    if sales_org in ORG_LOOKUP:
        return ORG_LOOKUP[sales_org]
    
    # Fallback: most common overall value
    return '999'
```

## YOUR TASK:
1. **Copy ALL entries** from the "SALESORGANIZATION -> Default TARGET" mapping above into ORG_LOOKUP
2. **Use the most common fallback value** shown in the distribution
3. **Keep the code simple** - just a dictionary lookup

## SAMPLE DATA (for reference):
{sample_data}

## BUSINESS CONTEXT:
{kg_context}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""


# Special prompt template for DATE/TIME fields (time series prediction)
TIME_SERIES_PROMPT_TEMPLATE = """
Generate a Python prediction function for DATE field: {target_field}

## CRITICAL: THIS IS A TIME SERIES PREDICTION TASK
- The target field "{target_field}" is a DATE/DATETIME
- You MUST predict a FUTURE date, not return historical dates
- Training data is from: {train_date_range}
- Test data will be AFTER the training period

## PREDICTION STRATEGY FOR DATES:
1. **Customer Purchase Cycle**: Calculate each customer's average purchase interval
2. **Predict Next Purchase**: last_purchase_date + average_interval
3. **Handle New Customers**: Use global average interval

## DATA STATISTICS:
{target_distribution}

## REQUIRED CODE STRUCTURE:
```python
def predict_{target_field_lower}(row):
    import pandas as pd
    from datetime import datetime, timedelta
    
    def safe_get(field, default=''):
        val = row.get(field)
        return str(val).strip() if pd.notna(val) else default
    
    # Customer's last known purchase date (from training data lookups)
    # This should be populated with SOLDTOPARTY -> last_date mapping
    CUSTOMER_LAST_DATE = {{
        # 'CUSTOMER_ID': 'YYYY-MM-DD',
    }}
    
    # Customer's average purchase interval in days
    CUSTOMER_INTERVAL = {{
        # 'CUSTOMER_ID': avg_interval_days,
    }}
    
    GLOBAL_AVG_INTERVAL = {global_interval}  # days
    TRAIN_END_DATE = '{train_end_date}'
    
    party = safe_get('SOLDTOPARTY')
    
    # Get customer-specific data
    last_date_str = CUSTOMER_LAST_DATE.get(party)
    interval = CUSTOMER_INTERVAL.get(party, GLOBAL_AVG_INTERVAL)
    
    if last_date_str:
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
        predicted = last_date + timedelta(days=interval)
    else:
        # New customer: predict from training end date
        train_end = datetime.strptime(TRAIN_END_DATE, '%Y-%m-%d')
        predicted = train_end + timedelta(days=GLOBAL_AVG_INTERVAL)
    
    return predicted.strftime('%Y-%m-%d %H:%M:%S')
```

## YOUR TASK:
1. Use SOLDTOPARTY to look up customer-specific purchase patterns
2. Calculate predicted date = last_date + average_interval
3. For unknown customers, use global average from training end date
4. Return date as string in format 'YYYY-MM-DD HH:MM:SS'

## SAMPLE DATA:
{sample_data}

## BUSINESS CONTEXT:
{kg_context}

Return JSON with: function_name, code, explanation, confidence, required_columns
"""

# List of fields that should use time series prediction
TIME_SERIES_FIELDS = ['CREATIONDATE', 'CREATIONTIME', 'DELIVERYDATE', 'BILLINGDATE']


class ScriptGenerator:
    """
    Generates prediction scripts using LLM based on KG knowledge.

    This class acts as a "compiler" that translates business rules from
    natural language into executable Python code.
    """

    # Default configuration for Antigravity proxy
    DEFAULT_BASE_URL = "http://127.0.0.1:8045"
    DEFAULT_API_KEY = "sk-6a821caf985142dab343fa7e031459c1"
    DEFAULT_MODEL = "gemini-3-pro-low"

    def __init__(self,
                 provider: str = "anthropic",
                 model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        Initialize the script generator.

        Args:
            provider: "openai" or "anthropic" (default: anthropic with Antigravity proxy)
            model: Model name. 
            api_key: API key. If None, uses default Antigravity key.
            base_url: Base URL for API. If None, uses default Antigravity proxy.
        """
        self.provider = provider.lower()

        if self.provider == "openai":
            if not HAS_OPENAI:
                raise ImportError("openai package not installed. Run: pip install openai")
            self.model = model or "gpt-4o"
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

        elif self.provider == "anthropic":
            if not HAS_ANTHROPIC:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.model = model or self.DEFAULT_MODEL
            self.client = anthropic.Anthropic(
                base_url=base_url or self.DEFAULT_BASE_URL,
                api_key=api_key or self.DEFAULT_API_KEY
            )

        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'anthropic'")

        self._cache: Dict[str, GeneratedScript] = {}
        self._debug_history: List[Dict[str, str]] = []  # Track conversation for debugging

    def generate(self,
                 target_field: str,
                 kg_context: str,
                 available_columns: List[str],
                 sample_data: str,
                 target_distribution: str,
                 use_cache: bool = True,
                 max_debug_iterations: int = 3,
                 sample_rows: Optional[List[Any]] = None) -> GeneratedScript:
        """
        Generate a prediction script with automatic debugging loop.

        Args:
            target_field: The field to predict
            kg_context: Business knowledge from the KG
            available_columns: List of column names available in the data
            sample_data: String representation of sample data
            target_distribution: Value distribution of the target field
            use_cache: Whether to use cached scripts
            max_debug_iterations: Maximum number of debug attempts (default 3)
            sample_rows: Optional sample rows for testing (list of pandas Series)

        Returns:
            GeneratedScript containing the prediction function
        """
        # Check cache
        cache_key = f"{target_field}_{hash(kg_context)}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Import target-specific prompts
        from .prompts import get_prompt_for_target, TARGET_PROMPT_REGISTRY
        
        # Get the appropriate prompt template for this target
        target_upper = target_field.upper()
        prompt_template = get_prompt_for_target(target_field)
        
        # Check if using a specialized prompt
        if target_upper in TARGET_PROMPT_REGISTRY:
            print(f"    [Generator] Using specialized prompt for {target_field}")
            # Format with available parameters
            try:
                user_prompt = prompt_template.format(
                    target_field=target_field,
                    target_field_lower=target_field.lower(),
                    target_distribution=target_distribution,
                    sample_data=sample_data,
                    kg_context=kg_context,
                    mode_value=self._extract_mode(target_distribution),
                )
            except KeyError:
                # Some prompts don't need all parameters
                user_prompt = prompt_template.format(
                    target_field=target_field,
                    target_field_lower=target_field.lower(),
                    target_distribution=target_distribution,
                    sample_data=sample_data,
                )
        else:
            # Use generic prompt
            print(f"    [Generator] Using generic prompt for {target_field}")
            user_prompt = prompt_template.format(
                target_field=target_field,
                target_field_lower=target_field.lower(),
                kg_context=kg_context,
                available_columns=', '.join(available_columns[:50]),
                sample_data=sample_data,
                target_distribution=target_distribution
            )

        # Reset debug history for new generation
        self._debug_history = []

        # Initial generation
        print(f"    [Generator] Generating initial code...")
        response = self._call_llm(user_prompt)
        script = self._parse_response(response, target_field)

        # Debug loop
        for iteration in range(max_debug_iterations):
            # Test the script
            test_result = self._test_script(script, sample_rows)

            if test_result['success']:
                print(f"    [Generator] ✓ Code validated successfully!")
                break

            print(f"    [Generator] Debug iteration {iteration + 1}/{max_debug_iterations}: {test_result['error_type']}")

            # Ask LLM to fix the error
            script = self._debug_and_fix(
                script=script,
                error_info=test_result,
                target_field=target_field,
                kg_context=kg_context,
                sample_data=sample_data,
                iteration=iteration + 1
            )

        # Cache the final result
        self._cache[cache_key] = script

        return script

    def _test_script(self, script: GeneratedScript, sample_rows: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Test the generated script for compilation and runtime errors.

        Returns:
            Dict with 'success', 'error_type', 'error_message', 'traceback'
        """
        import traceback as tb
        import pandas as pd

        # Step 1: Try to compile the code
        try:
            compile(script.code, '<generated>', 'exec')
        except SyntaxError as e:
            return {
                'success': False,
                'error_type': 'SyntaxError',
                'error_message': f"Line {e.lineno}: {e.msg}",
                'traceback': tb.format_exc(),
                'code': script.code
            }

        # Step 2: Try to execute the code to define the function
        sandbox = {'__builtins__': __builtins__}
        try:
            exec(script.code, sandbox)
        except Exception as e:
            return {
                'success': False,
                'error_type': type(e).__name__,
                'error_message': str(e),
                'traceback': tb.format_exc(),
                'code': script.code
            }

        # Step 3: Check if the function exists
        func_name = script.function_name
        if func_name not in sandbox:
            return {
                'success': False,
                'error_type': 'FunctionNotFound',
                'error_message': f"Function '{func_name}' not defined in the generated code",
                'traceback': '',
                'code': script.code
            }

        func = sandbox[func_name]

        # Step 4: Test with sample rows if provided
        if sample_rows:
            non_null_count = 0
            last_result = None
            for i, row in enumerate(sample_rows[:5]):  # Test first 5 rows
                try:
                    result = func(row)
                    # Check if result is reasonable (not an exception)
                    if result is not None:
                        non_null_count += 1
                        last_result = result
                except Exception as e:
                    return {
                        'success': False,
                        'error_type': f'RuntimeError (row {i})',
                        'error_message': str(e),
                        'traceback': tb.format_exc(),
                        'code': script.code,
                        'sample_row': str(dict(row))[:500]  # Truncate for context
                    }

            # If ALL results are None, that's a problem - the logic is wrong
            if non_null_count == 0:
                return {
                    'success': False,
                    'error_type': 'AllNullPredictions',
                    'error_message': f"Function returned None for all {min(5, len(sample_rows))} test rows. The prediction logic is not matching any conditions.",
                    'traceback': '',
                    'code': script.code,
                    'sample_row': str(dict(sample_rows[0]))[:500]
                }

            return {'success': True, 'sample_result': last_result, 'non_null_count': non_null_count}

        # If no sample rows, just check compilation passed
        return {'success': True}

    def _debug_and_fix(self,
                       script: GeneratedScript,
                       error_info: Dict[str, Any],
                       target_field: str,
                       kg_context: str,
                       sample_data: str,
                       iteration: int) -> GeneratedScript:
        """
        Ask the LLM to fix the error in the generated code.
        """
        debug_prompt = f"""
## DEBUG REQUEST - Iteration {iteration}

The previously generated code has an error. Please fix it.

### ERROR INFORMATION:
- Error Type: {error_info['error_type']}
- Error Message: {error_info['error_message']}
- Traceback:
```
{error_info.get('traceback', 'N/A')}
```

### PROBLEMATIC CODE:
```python
{script.code}
```

### SAMPLE ROW THAT CAUSED ERROR (if applicable):
{error_info.get('sample_row', 'N/A')}

### COMMON FIXES TO CONSIDER:
1. **SyntaxError**: Check for missing colons, parentheses, quotes, or indentation issues
2. **NameError**: Make sure all variables are defined before use; import required modules (pd, np) inside the function
3. **KeyError/AttributeError**: Use .get() method with defaults instead of direct access; check if row is a dict or Series
4. **TypeError**: Ensure proper type conversions; handle None values
5. **IndentationError**: Ensure consistent use of spaces (4 spaces per level)

### REQUIREMENTS:
1. Fix the specific error mentioned above
2. Keep the same overall logic and structure
3. Make the code more robust against edge cases
4. Ensure all imports (pandas, numpy) are INSIDE the function
5. Use defensive programming: check for None, use .get() with defaults

### OUTPUT FORMAT:
Return ONLY a JSON object with the fixed code:
{{
    "function_name": "predict_{target_field}",
    "code": "def predict_...(row):\\n    ...",
    "explanation": "What was fixed and why",
    "confidence": 0.7,
    "required_columns": [...]
}}
"""

        # Call LLM for fix
        print(f"    [Generator] Asking LLM to fix: {error_info['error_type']}")
        response = self._call_llm(debug_prompt)

        # Parse the fixed script
        fixed_script = self._parse_response(response, target_field)

        # Update explanation to include debug info
        fixed_script = GeneratedScript(
            code=fixed_script.code,
            function_name=fixed_script.function_name,
            target_field=fixed_script.target_field,
            explanation=f"[Fixed after {iteration} debug iteration(s)] {fixed_script.explanation}",
            confidence=fixed_script.confidence,
            required_columns=fixed_script.required_columns
        )

        return fixed_script

    def _extract_mode(self, target_distribution: str) -> str:
        """Extract the mode (most common) value from target distribution string."""
        import re
        # Try to find pattern like "Most common value is 'XXX'" or "'XXX': NN.N%"
        mode_match = re.search(r"Most common value is ['\"]([^'\"]+)['\"]", target_distribution)
        if mode_match:
            return mode_match.group(1)
        
        # Try to find first percentage entry
        pct_match = re.search(r"['\"]([^'\"]+)['\"]:\s*[\d.]+%", target_distribution)
        if pct_match:
            return pct_match.group(1)
        
        return "DEFAULT"

    def _call_llm(self, user_prompt: str) -> str:
        """Call the LLM API and return the response"""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Low temperature for more deterministic code
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content

        elif self.provider == "anthropic":
            # Check if using a thinking model
            is_thinking_model = "thinking" in self.model.lower()

            create_params = {
                "model": self.model,
                "max_tokens": 16000 if is_thinking_model else 4096,
                "messages": [
                    {"role": "user", "content": SYSTEM_PROMPT + "\n\n" + user_prompt}
                ]
            }

            # Add budget_tokens for thinking models
            if is_thinking_model:
                create_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 10000
                }

            response = self.client.messages.create(**create_params)

            # Extract text from response (handle thinking models)
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text

            # Fallback
            return response.content[-1].text if response.content else "{}"

    def _parse_response(self, response: str, target_field: str) -> GeneratedScript:
        """Parse the LLM response into a GeneratedScript"""
        try:
            # Try to parse as JSON
            data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    data = None
            else:
                data = None

            if data is None:
                # Fallback: create a basic script
                data = {
                    "function_name": f"predict_{target_field.lower()}",
                    "code": f"def predict_{target_field.lower()}(row):\n    return None  # Could not parse LLM response",
                    "explanation": "Failed to parse LLM response",
                    "confidence": 0.0,
                    "required_columns": []
                }

        # Clean up the generated code
        code = data.get("code", "")
        code = self._clean_code(code)

        return GeneratedScript(
            code=code,
            function_name=data.get("function_name", f"predict_{target_field.lower()}"),
            target_field=target_field,
            explanation=data.get("explanation", ""),
            confidence=float(data.get("confidence", 0.5)),
            required_columns=data.get("required_columns", [])
        )

    def _clean_code(self, code: str) -> str:
        """Clean up generated code - fix indentation and common issues"""
        import textwrap

        if not code:
            return code

        # Remove leading/trailing whitespace from the whole code block
        code = code.strip()

        # Fix common issue: code wrapped in markdown code blocks
        if code.startswith("```python"):
            code = code[9:]
        if code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()

        # Use textwrap.dedent to remove common leading whitespace
        code = textwrap.dedent(code)

        # Ensure the code starts with 'def '
        lines = code.split('\n')
        if lines and not lines[0].startswith('def '):
            # Find the first line that starts with 'def'
            for i, line in enumerate(lines):
                if line.strip().startswith('def '):
                    # Calculate the indentation to remove
                    indent = len(line) - len(line.lstrip())
                    if indent > 0:
                        # Remove this indentation from all lines
                        cleaned_lines = []
                        for l in lines[i:]:
                            if l.startswith(' ' * indent):
                                cleaned_lines.append(l[indent:])
                            elif l.strip() == '':
                                cleaned_lines.append('')
                            else:
                                cleaned_lines.append(l)
                        code = '\n'.join(cleaned_lines)
                    else:
                        code = '\n'.join(lines[i:])
                    break

        return code

    def generate_batch(self,
                       targets: List[Tuple[str, str, List[str], str, str]]) -> List[GeneratedScript]:
        """
        Generate scripts for multiple target fields.

        Args:
            targets: List of (target_field, kg_context, available_columns, sample_data, target_dist)

        Returns:
            List of GeneratedScript objects
        """
        return [
            self.generate(t[0], t[1], t[2], t[3], t[4])
            for t in targets
        ]


class MockScriptGenerator(ScriptGenerator):
    """
    A mock generator for testing without API calls.
    Returns pre-defined scripts based on common SAP fields.
    """

    MOCK_SCRIPTS = {
        "SALESORGANIZATION": GeneratedScript(
            code='''def predict_salesorganization(row):
    """
    Predict Sales Organization based on business rules.
    Logic: Sales org is typically determined by the sold-to party's region
    and the distribution channel.
    """
    # Get customer country if available
    country = row.get('COUNTRY') or row.get('SOLDTOPARTYCOUNTRY')

    if country in ['DE', 'AT', 'CH']:
        return '1000'  # DACH region
    elif country in ['US', 'CA']:
        return '2000'  # North America
    elif country in ['GB', 'FR', 'IT', 'ES']:
        return '3000'  # Western Europe
    elif country in ['CN', 'JP', 'KR']:
        return '4000'  # Asia Pacific
    else:
        return '1000'  # Default
''',
            function_name="predict_salesorganization",
            target_field="SALESORGANIZATION",
            explanation="Sales organization determined by customer's country/region",
            confidence=0.7,
            required_columns=["COUNTRY", "SOLDTOPARTYCOUNTRY"]
        ),

        "SALESGROUP": GeneratedScript(
            code='''def predict_salesgroup(row):
    """
    Predict Sales Group based on business rules.
    Logic: Sales groups are assigned based on customer type and sales org.
    """
    sales_org = row.get('SALESORGANIZATION')
    customer_group = row.get('CUSTOMERGROUP') or row.get('ADDITIONALCUSTOMERGROUP1')

    # Basic mapping based on organization and customer type
    if sales_org == '1000':
        if customer_group in ['01', '02']:
            return '100'  # Key accounts
        else:
            return '110'  # Standard accounts
    elif sales_org == '2000':
        return '200'  # US sales group
    else:
        return '100'  # Default
''',
            function_name="predict_salesgroup",
            target_field="SALESGROUP",
            explanation="Sales group based on sales organization and customer type",
            confidence=0.6,
            required_columns=["SALESORGANIZATION", "CUSTOMERGROUP", "ADDITIONALCUSTOMERGROUP1"]
        ),

        "PAYMENTTERMS": GeneratedScript(
            code='''def predict_paymentterms(row):
    """
    Predict Payment Terms based on business rules.
    Logic: Payment terms depend on customer creditworthiness and order value.
    """
    # Check credit status
    credit_status = row.get('TOTALCREDITCHECKSTATUS')
    net_value = row.get('TOTALNETTAMOUNT') or row.get('NETAMOUNT') or 0
    customer_group = row.get('CUSTOMERACCOUNTASSIGNMENTGROUP')

    # Blocked customers get strict terms
    if credit_status in ['B', 'R']:  # Blocked or Rejected
        return 'Z001'  # Immediate payment

    # Large orders may need different terms
    try:
        net_value = float(net_value)
    except (ValueError, TypeError):
        net_value = 0

    if net_value > 100000:
        return 'Z002'  # Net 30 for large orders
    elif net_value > 10000:
        return 'Z003'  # Net 45
    else:
        return 'Z004'  # Net 60 for smaller orders
''',
            function_name="predict_paymentterms",
            target_field="PAYMENTTERMS",
            explanation="Payment terms based on credit status and order value",
            confidence=0.65,
            required_columns=["TOTALCREDITCHECKSTATUS", "TOTALNETTAMOUNT", "NETAMOUNT", "CUSTOMERACCOUNTASSIGNMENTGROUP"]
        ),

        "CREATIONDATE": GeneratedScript(
            code='''def predict_creationdate(row):
    """
    Predict Creation Date - typically this is the current date.
    This is a simple field that represents when the document was created.
    """
    from datetime import datetime

    # If there's a reference to billing or delivery date, use that as context
    billing_date = row.get('BILLINGDOCUMENTDATE')
    if billing_date:
        # Creation typically happens before billing
        return billing_date  # Approximate

    # Default to extracting from other date fields if available
    return None  # Cannot reliably predict historical dates
''',
            function_name="predict_creationdate",
            target_field="CREATIONDATE",
            explanation="Creation date is typically the current date at document creation",
            confidence=0.3,
            required_columns=["BILLINGDOCUMENTDATE"]
        )
    }

    def __init__(self, **kwargs):
        """Initialize without API connection"""
        self.provider = "mock"
        self.model = "mock"
        self._cache = {}
        self._debug_history = []

    def _call_llm(self, user_prompt: str) -> str:
        """Mock LLM call - not used"""
        return "{}"

    def generate(self,
                 target_field: str,
                 kg_context: str,
                 available_columns: List[str],
                 sample_data: str,
                 target_distribution: str,
                 use_cache: bool = True,
                 max_debug_iterations: int = 3,
                 sample_rows: Optional[List[Any]] = None) -> GeneratedScript:
        """Return mock script if available"""
        target_upper = target_field.upper()

        if target_upper in self.MOCK_SCRIPTS:
            return self.MOCK_SCRIPTS[target_upper]

        # Generate a generic fallback script
        return GeneratedScript(
            code=f'''def predict_{target_field.lower()}(row):
    """
    Generic prediction for {target_field}.
    No specific business rules found - returns most common value or None.
    """
    # TODO: Implement specific business logic
    return None
''',
            function_name=f"predict_{target_field.lower()}",
            target_field=target_field,
            explanation=f"No specific rules found for {target_field}",
            confidence=0.1,
            required_columns=[]
        )
