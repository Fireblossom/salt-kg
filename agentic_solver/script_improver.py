"""
Script Improver - Self-improving agent for prediction scripts

This module implements an agentic loop where the LLM:
1. Evaluates existing scripts on validation data
2. Analyzes error patterns
3. Proposes improvements
4. Tests and saves improved versions
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from .duckdb_analyzer import DataAnalyzer, create_analyzer


@dataclass
class EvaluationResult:
    """Result of evaluating a prediction script"""
    target_field: str
    accuracy: float
    baseline_accuracy: float
    total_samples: int
    error_samples: List[Dict]  # Sample of incorrect predictions
    error_analysis: str  # LLM-generated analysis


class ScriptImprover:
    """
    Agent that evaluates and improves prediction scripts.
    
    Workflow:
    1. Load existing saved_script
    2. Evaluate on validation data
    3. Analyze errors
    4. Generate improved version
    5. Test and save if better
    """
    
    def __init__(self, generator, executor=None, verbose: bool = True):
        """
        Args:
            generator: ScriptGenerator instance (for LLM access)
            executor: ScriptExecutor instance (optional)
            verbose: Print progress
        """
        self.generator = generator
        self.executor = executor
        self.verbose = verbose
        self.saved_scripts_dir = Path(__file__).parent / 'saved_scripts'
        self.analyzer: Optional[DataAnalyzer] = None  # Lazy init
    
    def _log(self, msg: str):
        if self.verbose:
            print(f"[ScriptImprover] {msg}")
    
    def _ensure_analyzer(self, train_df: Optional[pd.DataFrame] = None) -> DataAnalyzer:
        """Ensure DataAnalyzer is initialized, optionally with training data."""
        if self.analyzer is None:
            self.analyzer = DataAnalyzer()
        if train_df is not None:
            self.analyzer.load_dataframe('train', train_df)
        return self.analyzer
    
    def evaluate_script(self, 
                        target_field: str,
                        train_df: pd.DataFrame,
                        val_df: pd.DataFrame,
                        n_error_samples: int = 20) -> EvaluationResult:
        """
        Evaluate a saved script and collect error samples.
        
        Args:
            target_field: Target field name
            train_df: Training data (for context)
            val_df: Validation data (for testing)
            n_error_samples: Number of error samples to collect
            
        Returns:
            EvaluationResult with accuracy and error analysis
        """
        script_path = self.saved_scripts_dir / f'{target_field.lower()}.py'
        
        if not script_path.exists():
            raise FileNotFoundError(f"No saved script for {target_field}")
        
        self._log(f"Evaluating {script_path.name}...")
        
        # Load and execute the script
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"saved_{target_field}", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func_name = f'predict_{target_field.lower()}'
        predict_func = getattr(module, func_name)
        
        # Run predictions
        predictions = []
        for _, row in val_df.iterrows():
            try:
                pred = predict_func(row)
                predictions.append(pred)
            except Exception as e:
                predictions.append(None)
        
        predictions = pd.Series(predictions, index=val_df.index)
        actuals = val_df[target_field]
        
        # Calculate accuracy
        accuracy = (predictions == actuals).mean()
        
        # Baseline (mode)
        mode_val = train_df[target_field].mode().iloc[0]
        baseline = (actuals == mode_val).mean()
        
        self._log(f"Accuracy: {accuracy:.2%} (Baseline: {baseline:.2%})")
        
        # Collect error samples
        errors_mask = predictions != actuals
        error_df = val_df[errors_mask].head(n_error_samples)
        
        error_samples = []
        for idx, row in error_df.iterrows():
            error_samples.append({
                'predicted': predictions.loc[idx],
                'actual': actuals.loc[idx],
                'features': {col: str(row[col]) for col in row.index[:10]}  # First 10 cols
            })
        
        self._log(f"Collected {len(error_samples)} error samples")
        
        return EvaluationResult(
            target_field=target_field,
            accuracy=accuracy,
            baseline_accuracy=baseline,
            total_samples=len(val_df),
            error_samples=error_samples,
            error_analysis=""
        )
    
    def analyze_errors(self, eval_result: EvaluationResult, script_code: str) -> str:
        """
        Use LLM to analyze error patterns.
        
        Args:
            eval_result: Evaluation result with error samples
            script_code: Current script code
            
        Returns:
            LLM analysis of error patterns
        """
        self._log("Analyzing error patterns with LLM...")
        
        # Format error samples for LLM
        error_str = json.dumps(eval_result.error_samples[:10], indent=2)
        
        prompt = f"""
Analyze why this prediction script is making errors.

## Current Script:
```python
{script_code}
```

## Performance:
- Accuracy: {eval_result.accuracy:.2%}
- Baseline (mode): {eval_result.baseline_accuracy:.2%}

## Sample Errors (predicted vs actual):
{error_str}

## Task:
1. Identify patterns in the errors
2. Explain WHY the current logic fails for these cases
3. Suggest specific improvements to the prediction logic

Be specific and actionable.
"""
        
        analysis = self.generator._call_llm(prompt)
        self._log("Error analysis complete")
        
        return analysis
    
    def analyze_patterns_with_sql(self,
                                   target_field: str,
                                   train_df: pd.DataFrame,
                                   available_columns: List[str],
                                   max_iterations: int = 3) -> Dict[str, Any]:
        """
        Use LLM to generate and execute SQL queries for data pattern analysis.
        
        The LLM can iteratively explore the data using SQL queries to understand
        patterns and optimize prediction logic.
        
        Args:
            target_field: Target field to analyze
            train_df: Training data
            available_columns: List of available columns
            max_iterations: Maximum SQL query iterations
            
        Returns:
            Dict with 'insights', 'queries_executed', 'lookup_recommendations'
        """
        self._log(f"Analyzing patterns for {target_field} using SQL...")
        
        # Initialize analyzer with training data
        analyzer = self._ensure_analyzer(train_df)
        
        # Get schema info for LLM context
        schema_info = analyzer.get_schema_info()
        
        # Get target distribution
        target_dist = analyzer.get_value_distribution('train', target_field)
        dist_str = target_dist.to_string() if len(target_dist) > 0 else "No distribution data"
        
        # Initial prompt for pattern discovery
        prompt = f"""
You have access to a DuckDB database with training data. Write SQL queries to discover patterns 
for predicting: {target_field}

## Database Schema:
{schema_info}

## Target Distribution (top values):
{dist_str}

## Available Columns (potential predictors):
{', '.join(available_columns[:30])}

## Task:
Generate 1-3 SQL queries to understand:
1. Which columns are most predictive of {target_field}?
2. What are the key value mappings (lookup patterns)?
3. Are there any conditional rules based on multiple columns?

Return your queries in this format:
```sql
-- Query 1: [description]
SELECT ...

-- Query 2: [description]  
SELECT ...
```

Focus on finding the MOST PREDICTIVE features for building lookup tables.
"""
        
        all_results = []
        queries_executed = []
        
        for iteration in range(max_iterations):
            self._log(f"SQL analysis iteration {iteration + 1}/{max_iterations}")
            
            response = self.generator._call_llm(prompt)
            
            # Extract SQL queries from response
            queries = self._extract_sql_queries(response)
            
            if not queries:
                break
            
            # Execute queries
            iteration_results = []
            for i, query in enumerate(queries[:5]):  # Limit to 5 queries per iteration
                result = analyzer.execute_sql_safe(query)
                queries_executed.append({
                    'iteration': iteration + 1,
                    'query': query,
                    'success': result['success'],
                    'row_count': result.get('row_count', 0)
                })
                
                if result['success']:
                    # Truncate large results for context
                    data = result['data']
                    if len(data) > 20:
                        data = data.head(20)
                    iteration_results.append({
                        'query': query,
                        'result': data.to_string()
                    })
            
            all_results.extend(iteration_results)
            
            # If we got good results, ask for synthesis
            if iteration_results:
                results_str = "\n\n".join([
                    f"Query: {r['query']}\nResult:\n{r['result']}" 
                    for r in iteration_results
                ])
                
                prompt = f"""
Based on these SQL query results for predicting {target_field}:

{results_str}

Either:
1. Write MORE SQL queries to dig deeper into patterns you've identified
2. If you have enough information, respond with "SYNTHESIS:" followed by your findings

If synthesizing, include:
- Top predictive columns ranked by accuracy
- Recommended lookup table structure
- Any conditional rules you discovered
"""
                
                # Check if LLM wants to synthesize
                if iteration < max_iterations - 1:
                    check_response = self.generator._call_llm(prompt)
                    if 'SYNTHESIS:' in check_response:
                        all_results.append({'synthesis': check_response.split('SYNTHESIS:')[1]})
                        break
                    # Otherwise continue with new queries in prompt
        
        # Final synthesis
        self._log("Generating final SQL analysis synthesis...")
        
        # Find best lookup columns using built-in method
        best_keys = analyzer.find_best_lookup_keys(
            'train', target_field, 
            [c for c in available_columns if c != target_field][:20]
        )
        
        return {
            'insights': all_results,
            'queries_executed': queries_executed,
            'best_lookup_columns': best_keys.to_dict('records') if len(best_keys) > 0 else [],
            'target_distribution': target_dist.to_dict('records') if len(target_dist) > 0 else []
        }
    
    def _extract_sql_queries(self, response: str) -> List[str]:
        """Extract SQL queries from LLM response."""
        queries = []
        
        # Try to extract from code blocks
        if '```sql' in response:
            parts = response.split('```sql')
            for part in parts[1:]:
                if '```' in part:
                    sql = part.split('```')[0].strip()
                    # Split multiple queries
                    for q in sql.split(';'):
                        q = q.strip()
                        if q and q.upper().startswith('SELECT'):
                            queries.append(q)
        elif '```' in response:
            parts = response.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Inside code block
                    for q in part.split(';'):
                        q = q.strip()
                        if q and q.upper().startswith('SELECT'):
                            queries.append(q)
        
        return queries
    
    def improve_script(self,
                       target_field: str,
                       eval_result: EvaluationResult,
                       current_code: str,
                       error_analysis: str,
                       train_df: pd.DataFrame,
                       sql_patterns: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate an improved version of the script.
        
        Args:
            target_field: Target field
            eval_result: Current evaluation result
            current_code: Current script code
            error_analysis: LLM analysis of errors
            train_df: Training data for building mappings
            sql_patterns: Optional SQL-derived pattern analysis
            
        Returns:
            Improved script code
        """
        self._log("Generating improved script...")
        
        # Get distribution info
        target_dist = train_df[target_field].value_counts(normalize=True).head(20)
        dist_str = '\n'.join([f"  '{v}': {p:.2%}" for v, p in target_dist.items()])
        
        # Build SQL insights section if available
        sql_insights_str = ""
        if sql_patterns:
            best_cols = sql_patterns.get('best_lookup_columns', [])
            if best_cols:
                sql_insights_str = "\n## SQL-Derived Best Lookup Columns:\n"
                for col in best_cols[:5]:
                    sql_insights_str += f"  - {col.get('lookup_column')}: {col.get('accuracy_pct', 0):.1f}% accuracy with {col.get('unique_keys', 0)} keys\n"
            
            # Add synthesis if available
            for insight in sql_patterns.get('insights', []):
                if isinstance(insight, dict) and 'synthesis' in insight:
                    sql_insights_str += f"\n## Pattern Analysis:\n{insight['synthesis'][:2000]}\n"
        
        prompt = f"""
Improve this prediction script based on error analysis and data patterns.

## Current Script (Accuracy: {eval_result.accuracy:.2%}):
```python
{current_code}
```

## Error Analysis:
{error_analysis}

## Target Distribution:
{dist_str}
{sql_insights_str}
## Requirements:
1. Generate a COMPLETE, WORKING Python script
2. The function must be named `predict_{target_field.lower()}`
3. Include all necessary imports at the top
4. If using JSON files, they should be in the same directory
5. Focus on fixing the specific issues identified in error analysis
6. Use the SQL-derived lookup column rankings to prioritize which features to use

Return ONLY the improved Python code, no explanations.
"""
        
        response = self.generator._call_llm(prompt)
        
        # Extract code from response
        if '```python' in response:
            code = response.split('```python')[1].split('```')[0]
        elif '```' in response:
            code = response.split('```')[1].split('```')[0]
        else:
            code = response
        
        return code.strip()
    
    def improve_and_save(self,
                         target_field: str,
                         train_df: pd.DataFrame,
                         val_df: pd.DataFrame,
                         max_iterations: int = 3,
                         use_sql_analysis: bool = True) -> Tuple[float, float]:
        """
        Full improvement loop: evaluate → analyze → improve → test → save.
        
        Args:
            target_field: Target to improve
            train_df: Training data
            val_df: Validation data
            max_iterations: Maximum improvement attempts
            use_sql_analysis: Whether to use DuckDB SQL analysis for patterns
            
        Returns:
            (initial_accuracy, final_accuracy)
        """
        script_path = self.saved_scripts_dir / f'{target_field.lower()}.py'
        
        if not script_path.exists():
            self._log(f"No existing script for {target_field}, generating new one...")
            # TODO: Generate from scratch
            return (0.0, 0.0)
        
        current_code = script_path.read_text()
        
        # Initial evaluation
        eval_result = self.evaluate_script(target_field, train_df, val_df)
        initial_accuracy = eval_result.accuracy
        best_accuracy = initial_accuracy
        best_code = current_code
        
        # Run SQL pattern analysis once at the start
        sql_patterns = None
        if use_sql_analysis:
            try:
                sql_patterns = self.analyze_patterns_with_sql(
                    target_field, train_df, list(train_df.columns)
                )
                self._log(f"SQL analysis found {len(sql_patterns.get('best_lookup_columns', []))} candidate lookup columns")
            except Exception as e:
                self._log(f"SQL analysis failed: {e}, continuing without it")
        
        for i in range(max_iterations):
            self._log(f"\n=== Improvement iteration {i+1}/{max_iterations} ===")
            
            # Analyze errors
            error_analysis = self.analyze_errors(eval_result, current_code)
            
            # Generate improved version (now with SQL patterns)
            improved_code = self.improve_script(
                target_field, eval_result, current_code, error_analysis, train_df,
                sql_patterns=sql_patterns
            )
            
            # Test improved version
            try:
                # Write temp file
                temp_path = self.saved_scripts_dir / f'{target_field.lower()}_temp.py'
                temp_path.write_text(improved_code)
                
                # Evaluate
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"temp_{target_field}", temp_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                func_name = f'predict_{target_field.lower()}'
                predict_func = getattr(module, func_name)
                
                predictions = []
                for _, row in val_df.iterrows():
                    try:
                        pred = predict_func(row)
                        predictions.append(pred)
                    except:
                        predictions.append(None)
                
                new_accuracy = (pd.Series(predictions, index=val_df.index) == val_df[target_field]).mean()
                
                self._log(f"Improved accuracy: {new_accuracy:.2%} (was {best_accuracy:.2%})")
                
                if new_accuracy > best_accuracy:
                    self._log("✓ Improvement found!")
                    best_accuracy = new_accuracy
                    best_code = improved_code
                    current_code = improved_code
                else:
                    self._log("✗ No improvement, keeping previous version")
                
                temp_path.unlink()  # Clean up
                
            except Exception as e:
                self._log(f"✗ Error testing improved script: {e}")
                continue
            
            # Early stop if accuracy is very high
            if best_accuracy > 0.95:
                self._log("Reached >95% accuracy, stopping early")
                break
        
        # Save best version
        if best_accuracy > initial_accuracy:
            script_path.write_text(best_code)
            self._log(f"\n✓ Saved improved script: {initial_accuracy:.2%} → {best_accuracy:.2%}")
        else:
            self._log(f"\nNo improvement found, keeping original")
        
        return (initial_accuracy, best_accuracy)
