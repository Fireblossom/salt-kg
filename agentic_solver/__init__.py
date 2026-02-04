"""
Agentic Scripting Solver for SALT-KG

This module implements a "Code as Reasoning" approach where an LLM generates
Python code based on business knowledge from the Knowledge Graph, rather than
using traditional ML to predict values.

Key Components:
- KGLoader: Loads and parses the SALT-KG metadata
- ScriptGenerator: Uses LLM to generate prediction logic as Python code
- ScriptExecutor: Safely executes generated scripts
- AgenticPredictor: Main interface combining all components
"""

from .kg_loader import KGLoader
from .script_generator import ScriptGenerator
from .script_executor import ScriptExecutor
from .predictor import AgenticPredictor

__all__ = ['KGLoader', 'ScriptGenerator', 'ScriptExecutor', 'AgenticPredictor']
__version__ = '0.1.0'
