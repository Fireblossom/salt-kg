"""
Agentic Predictor - Main Interface

Combines KG loading, script generation, and execution into a unified
prediction interface that can replace traditional ML models.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
import json

from .kg_loader import KGLoader, FieldMetadata
from .script_generator import ScriptGenerator, MockScriptGenerator, GeneratedScript
from .script_executor import ScriptExecutor, ReactExecutor, ExecutionResult


@dataclass
class PredictionReport:
    """Report on prediction quality and coverage"""
    target_field: str
    total_rows: int
    predicted_count: int
    null_count: int
    accuracy: Optional[float]  # If ground truth available
    unique_predictions: int
    execution_errors: int
    avg_execution_time_ms: float


class AgenticPredictor:
    """
    Main interface for agentic prediction on SALT-KG data.

    This class orchestrates the entire "Code as Reasoning" pipeline:
    1. Load business knowledge from the Knowledge Graph
    2. Generate prediction scripts using an LLM
    3. Execute scripts to make predictions
    4. Evaluate and report results

    Example usage:
        predictor = AgenticPredictor()
        predictor.fit('SALESORGANIZATION', train_df)
        predictions = predictor.predict(test_df)
    """

    def __init__(self,
                 kg_path: Optional[str] = None,
                 llm_provider: str = "mock",
                 llm_model: Optional[str] = None,
                 api_key: Optional[str] = None,
                 use_react: bool = True,
                 verbose: bool = True):
        """
        Initialize the agentic predictor.

        Args:
            kg_path: Path to salt-kg.json. Uses default if None.
            llm_provider: "openai", "anthropic", or "mock" for testing
            llm_model: Specific model to use
            api_key: API key for LLM provider
            use_react: Whether to use ReAct pattern for error recovery
            verbose: Whether to print progress messages
        """
        self.verbose = verbose

        # Load Knowledge Graph
        self._log("Loading Knowledge Graph...")
        self.kg = KGLoader(kg_path)

        # Initialize script generator
        self._log(f"Initializing script generator ({llm_provider})...")
        if llm_provider == "mock":
            self.generator = MockScriptGenerator()
        else:
            self.generator = ScriptGenerator(
                provider=llm_provider,
                model=llm_model,
                api_key=api_key
            )

        # Initialize executor
        if use_react:
            self.executor = ReactExecutor(script_generator=self.generator)
        else:
            self.executor = ScriptExecutor()

        # State
        self._fitted_scripts: Dict[str, GeneratedScript] = {}
        self._target_field: Optional[str] = None

    def _log(self, message: str):
        """Print log message if verbose"""
        if self.verbose:
            print(f"[AgenticPredictor] {message}")

    def fit(self, target_field: str,
            train_df: pd.DataFrame,
            related_fields: Optional[List[str]] = None,
            force_regenerate: bool = False) -> 'AgenticPredictor':
        """
        "Fit" the predictor by generating prediction scripts.

        Unlike traditional ML, this doesn't learn from the data statistically.
        Instead, it:
        1. Analyzes the KG for business rules about the target field
        2. Uses the LLM to generate prediction logic
        3. Compiles and validates the generated script

        Args:
            target_field: The column to predict
            train_df: Training data (used for context, not statistical learning)
            related_fields: Optional list of fields that might influence the target
            force_regenerate: If True, regenerate even if cached

        Returns:
            self (for method chaining)
        """
        self._target_field = target_field
        self._log(f"Fitting predictor for: {target_field}")

        # Check if already fitted
        if target_field in self._fitted_scripts and not force_regenerate:
            self._log("Using cached script")
            script = self._fitted_scripts[target_field]
            self._current_script = script
            return self
        
        # NEW: Check for pre-saved scripts in saved_scripts directory
        saved_script_path = Path(__file__).parent / 'saved_scripts' / f'{target_field.lower()}.py'
        if saved_script_path.exists() and not force_regenerate:
            self._log(f"Loading pre-saved script from {saved_script_path.name}")
            try:
                # Read and compile the saved script
                script_code = saved_script_path.read_text()
                func_name = f'predict_{target_field.lower()}'
                
                # Import the module dynamically
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"saved_{target_field.lower()}", saved_script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get the predict function
                if hasattr(module, func_name):
                    self._predict_func = getattr(module, func_name)
                    self._log(f"✓ Loaded saved script with function: {func_name}")
                    
                    # Create a GeneratedScript wrapper for compatibility
                    from .script_generator import GeneratedScript
                    self._current_script = GeneratedScript(
                        code=script_code,
                        function_name=func_name,
                        target_field=target_field,
                        explanation="Pre-saved optimized script",
                        confidence=0.9,
                        required_columns=[]
                    )
                    self._fitted_scripts[target_field] = self._current_script
                    return self
            except Exception as e:
                self._log(f"Warning: Failed to load saved script: {e}. Will generate new one.")

        # No saved script found or failed to load - generate new one
        # Gather context from KG
        self._log("Gathering business context from Knowledge Graph...")
        kg_context = self.kg.get_context_for_field(target_field, related_fields)

        # Prepare sample data context
        sample_data = self._prepare_sample_context(train_df, target_field)
        target_dist = self._get_target_distribution(train_df, target_field)

        # Prepare sample rows for testing during generation
        sample_rows = [train_df.iloc[i] for i in range(min(5, len(train_df)))]

        # Generate script with debug loop
        self._log("Generating prediction script with LLM...")
        script = self.generator.generate(
            target_field=target_field,
            kg_context=kg_context,
            available_columns=list(train_df.columns),
            sample_data=sample_data,
            target_distribution=target_dist,
            sample_rows=sample_rows,  # Pass sample rows for runtime testing
            max_debug_iterations=3
        )

        self._fitted_scripts[target_field] = script

        self._log(f"Script confidence: {script.confidence:.0%}")
        self._log(f"Required columns: {script.required_columns}")

        # Compile the script
        self._log("Compiling script...")
        success, error = self.executor.compile_script(script.code, script.function_name)

        if not success:
            self._log(f"⚠️  Compilation failed: {error}")
            raise RuntimeError(f"Script compilation failed: {error}")

        # Test on a few rows
        self._log("Testing on sample rows...")
        test_rows = [train_df.iloc[i] for i in range(min(3, len(train_df)))]
        results = self.executor.test_function(script.function_name, test_rows)

        success_count = sum(1 for r in results if r.success)
        self._log(f"Test results: {success_count}/{len(results)} successful")

        return self

    def predict(self, df: pd.DataFrame,
                show_progress: bool = True) -> pd.Series:
        """
        Make predictions on new data.

        Args:
            df: DataFrame to predict on
            show_progress: Whether to show progress updates

        Returns:
            Series of predictions
        """
        if self._target_field is None:
            raise RuntimeError("Predictor not fitted. Call fit() first.")

        self._log(f"Predicting {len(df)} rows...")

        # Check if we have a direct predict function (from saved scripts)
        if hasattr(self, '_predict_func') and self._predict_func is not None:
            # Use the directly loaded function
            progress_cb = None
            if show_progress:
                def progress_cb(current, total):
                    if current % 1000 == 0:
                        self._log(f"Progress: {current}/{total}")
            
            predictions = []
            for i, (_, row) in enumerate(df.iterrows()):
                try:
                    pred = self._predict_func(row)
                    predictions.append(pred)
                except Exception as e:
                    predictions.append(None)
                
                if progress_cb and i % 1000 == 0:
                    progress_cb(i, len(df))
            
            predictions = pd.Series(predictions, index=df.index)
        else:
            # Use executor (for LLM-generated scripts)
            script = self._fitted_scripts[self._target_field]
            
            progress_cb = None
            if show_progress:
                def progress_cb(current, total):
                    if current % 1000 == 0:
                        self._log(f"Progress: {current}/{total}")

            predictions = self.executor.execute_on_dataframe(
                script.function_name, df, progress_callback=progress_cb
            )

        self._log(f"Done. Non-null predictions: {predictions.notna().sum()}")

        return predictions

    def evaluate(self, df: pd.DataFrame,
                 ground_truth_column: Optional[str] = None) -> PredictionReport:
        """
        Evaluate prediction quality.

        Args:
            df: DataFrame with data to predict
            ground_truth_column: Column containing actual values (defaults to target_field)

        Returns:
            PredictionReport with metrics
        """
        if self._target_field is None:
            raise RuntimeError("Predictor not fitted. Call fit() first.")

        ground_truth_column = ground_truth_column or self._target_field

        predictions = self.predict(df, show_progress=False)

        # Calculate metrics
        accuracy = None
        if ground_truth_column in df.columns:
            actual = df[ground_truth_column]
            matches = (predictions == actual)
            accuracy = matches.sum() / len(matches)

        return PredictionReport(
            target_field=self._target_field,
            total_rows=len(df),
            predicted_count=predictions.notna().sum(),
            null_count=predictions.isna().sum(),
            accuracy=accuracy,
            unique_predictions=predictions.nunique(),
            execution_errors=0,  # TODO: track this
            avg_execution_time_ms=0.0  # TODO: track this
        )

    def get_generated_code(self, target_field: Optional[str] = None) -> str:
        """Get the generated prediction code for inspection"""
        target = target_field or self._target_field
        if target and target in self._fitted_scripts:
            return self._fitted_scripts[target].code
        return ""

    def get_explanation(self, target_field: Optional[str] = None) -> str:
        """Get the LLM's explanation of the prediction logic"""
        target = target_field or self._target_field
        if target and target in self._fitted_scripts:
            return self._fitted_scripts[target].explanation
        return ""

    def _prepare_sample_context(self, df: pd.DataFrame, target_field: str,
                                  n_samples: int = 50) -> str:
        """Prepare sample data string for LLM context with stratified sampling"""
        # Select relevant columns (target + a few others)
        cols = [target_field] if target_field in df.columns else []

        # Add some other columns
        other_cols = [c for c in df.columns if c != target_field][:15]
        cols.extend(other_cols)

        # Use stratified sampling to get diverse examples
        if target_field in df.columns:
            # Get samples from each unique value of the target
            unique_values = df[target_field].value_counts().head(20).index.tolist()
            samples = []
            samples_per_value = max(2, n_samples // len(unique_values))

            for val in unique_values:
                subset = df[df[target_field] == val].head(samples_per_value)
                samples.append(subset)

            if samples:
                sample_df = pd.concat(samples, ignore_index=True).head(n_samples)
            else:
                sample_df = df[cols].head(n_samples)
        else:
            sample_df = df[cols].head(n_samples)

        sample_df = sample_df[cols]
        return sample_df.to_string()

    def _get_target_distribution(self, df: pd.DataFrame, target_field: str,
                                   top_n: int = 30) -> str:
        """Get clean, LLM-friendly distribution with ready-to-use mappings"""
        if target_field not in df.columns:
            return "Target field not in training data"

        lines = []
        
        # 1. Overall statistics
        mode_value = df[target_field].mode()[0]
        mode_pct = (df[target_field] == mode_value).mean() * 100
        lines.append(f"## Overall: Most common value is '{mode_value}' ({mode_pct:.1f}% of data)")
        lines.append("")

        # 2. Build SALESORGANIZATION -> TARGET mapping (Python dict format)
        lines.append("## SALESORGANIZATION -> TARGET Mapping")
        lines.append("Copy this dict directly into your code:")
        lines.append("```python")
        lines.append("ORG_LOOKUP = {")
        
        if 'SALESORGANIZATION' in df.columns:
            org_data = df.groupby('SALESORGANIZATION').agg({
                target_field: lambda x: x.value_counts().index[0]
            }).reset_index()
            org_counts = df.groupby('SALESORGANIZATION').size()
            org_data['count'] = org_data['SALESORGANIZATION'].map(org_counts)
            org_data = org_data.sort_values('count', ascending=False).head(top_n)
            
            for _, row in org_data.iterrows():
                org = row['SALESORGANIZATION']
                target = row[target_field]
                count = row['count']
                lines.append(f"    '{org}': '{target}',  # {count} rows")
        
        lines.append("}")
        lines.append("```")
        lines.append("")

        # 3. Top target values for reference
        lines.append("## Target Value Frequencies (top 10):")
        for val, count in df[target_field].value_counts().head(10).items():
            pct = count / len(df) * 100
            lines.append(f"  '{val}': {pct:.1f}%")

        return '\n'.join(lines)

    def save(self, path: str):
        """Save fitted scripts to disk"""
        data = {
            target: {
                "code": script.code,
                "function_name": script.function_name,
                "target_field": script.target_field,
                "explanation": script.explanation,
                "confidence": script.confidence,
                "required_columns": script.required_columns
            }
            for target, script in self._fitted_scripts.items()
        }

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str, **kwargs) -> 'AgenticPredictor':
        """Load a saved predictor"""
        predictor = cls(**kwargs)

        with open(path, 'r') as f:
            data = json.load(f)

        for target, script_data in data.items():
            script = GeneratedScript(**script_data)
            predictor._fitted_scripts[target] = script

            # Compile
            predictor.executor.compile_script(script.code, script.function_name)

        return predictor


def compare_with_ml(agentic_predictor: AgenticPredictor,
                    ml_predictions: pd.Series,
                    df: pd.DataFrame,
                    target_field: str) -> Dict[str, Any]:
    """
    Compare agentic predictions with traditional ML predictions.

    Args:
        agentic_predictor: Fitted AgenticPredictor
        ml_predictions: Predictions from a traditional ML model
        df: DataFrame with ground truth
        target_field: The target column

    Returns:
        Dictionary with comparison metrics
    """
    agentic_preds = agentic_predictor.predict(df)
    actual = df[target_field]

    agentic_acc = (agentic_preds == actual).mean()
    ml_acc = (ml_predictions == actual).mean()

    # Find cases where agentic is right and ML is wrong
    agentic_wins = ((agentic_preds == actual) & (ml_predictions != actual)).sum()
    ml_wins = ((ml_predictions == actual) & (agentic_preds != actual)).sum()

    return {
        "agentic_accuracy": agentic_acc,
        "ml_accuracy": ml_acc,
        "agentic_wins": agentic_wins,
        "ml_wins": ml_wins,
        "agentic_coverage": agentic_preds.notna().mean(),
        "agreement_rate": (agentic_preds == ml_predictions).mean()
    }
