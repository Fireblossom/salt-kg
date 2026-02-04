#!/usr/bin/env python3
"""Quick test for DuckDB analyzer module."""

import sys
sys.path.insert(0, '/Users/duan/salt-kg')

try:
    import duckdb
    print("✓ DuckDB imported successfully")
except ImportError:
    print("✗ DuckDB not installed. Run: pip install duckdb")
    sys.exit(1)

from agentic_solver.duckdb_analyzer import DataAnalyzer

# Create analyzer
da = DataAnalyzer()
print("✓ DataAnalyzer created")

# Check if tables loaded
schema = da.get_schema_info()
print(f"✓ Schema info:\n{schema[:500]}...")

# Test SQL query
result = da.execute_sql("SELECT COUNT(*) as cnt FROM train")
print(f"✓ SQL query executed: {result}")

# Test value distribution
dist = da.get_value_distribution('train', 'CUSTOMERPAYMENTTERMS')
print(f"✓ Value distribution:\n{dist.head()}")

print("\n=== All tests passed! ===")
