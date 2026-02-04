"""
Script Executor - Safe Execution Environment for Generated Code

Provides a sandboxed environment to execute LLM-generated prediction scripts.
Includes safety checks, error handling, and ReAct-style iterative debugging.
"""

import sys
import traceback
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from io import StringIO
import pandas as pd


@dataclass
class ExecutionResult:
    """Result of script execution"""
    success: bool
    value: Any
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float = 0.0


class ScriptExecutor:
    """
    Safely executes generated prediction scripts.

    Features:
    - Sandboxed execution with limited builtins
    - Error capture and reporting
    - Support for ReAct-style iterative debugging
    """

    # Safe builtins for execution
    SAFE_BUILTINS = {
        'abs': abs,
        'all': all,
        'any': any,
        'bool': bool,
        'dict': dict,
        'enumerate': enumerate,
        'filter': filter,
        'float': float,
        'format': format,
        'frozenset': frozenset,
        'hasattr': hasattr,
        'hash': hash,
        'int': int,
        'isinstance': isinstance,
        'issubclass': issubclass,
        'iter': iter,
        'len': len,
        'list': list,
        'map': map,
        'max': max,
        'min': min,
        'next': next,
        'None': None,
        'True': True,
        'False': False,
        'ord': ord,
        'pow': pow,
        'print': print,
        'range': range,
        'repr': repr,
        'reversed': reversed,
        'round': round,
        'set': set,
        'slice': slice,
        'sorted': sorted,
        'str': str,
        'sum': sum,
        'tuple': tuple,
        'type': type,
        'zip': zip,
        '__import__': __import__,  # Allow imports inside functions
    }

    # Allowed imports
    ALLOWED_IMPORTS = {
        'datetime': __import__('datetime'),
        'math': __import__('math'),
        're': __import__('re'),
        'json': __import__('json'),
        'collections': __import__('collections'),
    }

    def __init__(self, allow_pandas: bool = True):
        """
        Initialize the executor.

        Args:
            allow_pandas: Whether to allow pandas operations in scripts
        """
        self.allow_pandas = allow_pandas
        self._compiled_functions: Dict[str, Callable] = {}

    def compile_script(self, code: str, function_name: str) -> Tuple[bool, Optional[str]]:
        """
        Compile a script and extract the prediction function.

        Args:
            code: The Python code containing the prediction function
            function_name: The name of the function to extract

        Returns:
            (success, error_message)
        """
        # Create sandboxed globals
        sandbox_globals = {
            '__builtins__': self.SAFE_BUILTINS,
            **self.ALLOWED_IMPORTS
        }

        if self.allow_pandas:
            sandbox_globals['pd'] = pd

        try:
            # Compile and execute to define the function
            exec(compile(code, '<generated>', 'exec'), sandbox_globals)

            # Extract the function
            if function_name not in sandbox_globals:
                return False, f"Function '{function_name}' not found in generated code"

            func = sandbox_globals[function_name]
            if not callable(func):
                return False, f"'{function_name}' is not callable"

            self._compiled_functions[function_name] = func
            return True, None

        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Compilation error: {type(e).__name__}: {str(e)}"

    def execute_on_row(self, function_name: str, row: pd.Series) -> ExecutionResult:
        """
        Execute a compiled prediction function on a single row.

        Args:
            function_name: Name of the compiled function
            row: A pandas Series representing a data row

        Returns:
            ExecutionResult with the prediction or error info
        """
        import time

        if function_name not in self._compiled_functions:
            return ExecutionResult(
                success=False,
                value=None,
                error_message=f"Function '{function_name}' not compiled",
                error_type="NotCompiled"
            )

        func = self._compiled_functions[function_name]

        start_time = time.time()
        try:
            result = func(row)
            elapsed_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=True,
                value=result,
                execution_time_ms=elapsed_ms
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                value=None,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_ms=elapsed_ms
            )

    def execute_on_dataframe(self, function_name: str, df: pd.DataFrame,
                              progress_callback: Optional[Callable[[int, int], None]] = None) -> pd.Series:
        """
        Execute a compiled function on all rows of a DataFrame.

        Args:
            function_name: Name of the compiled function
            df: The DataFrame to process
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            A pandas Series with predictions for each row
        """
        if function_name not in self._compiled_functions:
            raise ValueError(f"Function '{function_name}' not compiled")

        func = self._compiled_functions[function_name]
        results = []
        total = len(df)

        for idx, (_, row) in enumerate(df.iterrows()):
            try:
                result = func(row)
            except Exception:
                result = None
            results.append(result)

            if progress_callback and idx % 100 == 0:
                progress_callback(idx, total)

        return pd.Series(results, index=df.index)

    def test_function(self, function_name: str, test_rows: List[pd.Series]) -> List[ExecutionResult]:
        """
        Test a compiled function on multiple sample rows.

        Args:
            function_name: Name of the compiled function
            test_rows: List of sample rows to test

        Returns:
            List of ExecutionResult for each test row
        """
        return [self.execute_on_row(function_name, row) for row in test_rows]

    def get_function_info(self, function_name: str) -> Dict[str, Any]:
        """Get information about a compiled function"""
        if function_name not in self._compiled_functions:
            return {"exists": False}

        func = self._compiled_functions[function_name]
        return {
            "exists": True,
            "name": func.__name__,
            "doc": func.__doc__ or "No docstring",
        }


class ReactExecutor(ScriptExecutor):
    """
    Extended executor with ReAct (Reason + Act) pattern for iterative debugging.

    When a script fails, this executor can:
    1. Capture the error and context
    2. Ask the LLM to fix the script
    3. Re-compile and re-test
    """

    def __init__(self, script_generator=None, max_retries: int = 3, **kwargs):
        """
        Initialize with a script generator for iterative fixing.

        Args:
            script_generator: A ScriptGenerator instance for fixing scripts
            max_retries: Maximum number of fix attempts
        """
        super().__init__(**kwargs)
        self.script_generator = script_generator
        self.max_retries = max_retries
        self._error_history: List[Dict[str, Any]] = []

    def compile_and_fix(self, code: str, function_name: str,
                        sample_row: Optional[pd.Series] = None) -> Tuple[str, bool, List[str]]:
        """
        Compile a script, and if it fails, attempt to fix it.

        Args:
            code: The Python code to compile
            function_name: The function name
            sample_row: Optional sample row for testing

        Returns:
            (final_code, success, list_of_errors_encountered)
        """
        errors = []
        current_code = code

        for attempt in range(self.max_retries):
            # Try to compile
            success, error = self.compile_script(current_code, function_name)

            if success:
                # Test execution if we have a sample row
                if sample_row is not None:
                    result = self.execute_on_row(function_name, sample_row)
                    if not result.success:
                        errors.append(f"Runtime error: {result.error_type}: {result.error_message}")
                        # Here we would ask the LLM to fix - for now just log
                        self._error_history.append({
                            "attempt": attempt,
                            "error_type": "runtime",
                            "error": result.error_message,
                            "code": current_code
                        })
                        continue
                return current_code, True, errors

            errors.append(error)
            self._error_history.append({
                "attempt": attempt,
                "error_type": "compile",
                "error": error,
                "code": current_code
            })

            # TODO: If we have a script generator, ask it to fix the code
            # For now, just fail
            break

        return current_code, False, errors

    def get_error_history(self) -> List[Dict[str, Any]]:
        """Get the history of errors for debugging"""
        return self._error_history.copy()
