"""
DuckDB Data Analyzer - SQL-based data pattern analysis

Provides in-memory SQL capabilities for analyzing training data patterns.
Used by ScriptImprover to help LLM understand data distributions and
optimize lookup logic.
"""

import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any


class DataAnalyzer:
    """
    SQL-based data analyzer using DuckDB.
    
    Loads parquet training data into an in-memory database and provides
    SQL query execution for pattern analysis.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the analyzer with training data.
        
        Args:
            data_dir: Path to data directory containing parquet files.
                     Defaults to ../../data/salt relative to this file.
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'data' / 'salt'
        
        self.data_dir = Path(data_dir)
        self.conn = duckdb.connect(':memory:')
        self._loaded_tables: Dict[str, str] = {}
        
        # Auto-load training data if available
        self._load_default_tables()
    
    def _load_default_tables(self):
        """Load default training tables."""
        train_file = self.data_dir / 'JoinedTables_train.parquet'
        if train_file.exists():
            self.load_parquet('train', train_file)
        
        test_file = self.data_dir / 'JoinedTables_test.parquet'
        if test_file.exists():
            self.load_parquet('test', test_file)
    
    def load_parquet(self, table_name: str, file_path: Path) -> None:
        """
        Load a parquet file as a table.
        
        Args:
            table_name: Name for the table in SQL
            file_path: Path to the parquet file
        """
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM read_parquet('{file_path}')
        """)
        self._loaded_tables[table_name] = str(file_path)
    
    def load_dataframe(self, table_name: str, df: pd.DataFrame) -> None:
        """
        Load a pandas DataFrame as a table.
        
        Args:
            table_name: Name for the table in SQL
            df: DataFrame to load
        """
        self.conn.register(f'_{table_name}_temp', df)
        self.conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS 
            SELECT * FROM _{table_name}_temp
        """)
        self._loaded_tables[table_name] = 'DataFrame'
    
    def execute_sql(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as DataFrame.
        
        Args:
            query: SQL query string
            
        Returns:
            Query results as pandas DataFrame
        """
        try:
            return self.conn.execute(query).fetchdf()
        except Exception as e:
            # Return error info as DataFrame for LLM to see
            return pd.DataFrame({'error': [str(e)], 'query': [query]})
    
    def execute_sql_safe(self, query: str, max_rows: int = 1000) -> Dict[str, Any]:
        """
        Execute SQL with safety limits and structured output.
        
        Args:
            query: SQL query string
            max_rows: Maximum rows to return
            
        Returns:
            Dict with 'success', 'data' or 'error', 'row_count'
        """
        try:
            # Add LIMIT if not present
            query_lower = query.lower().strip()
            if 'limit' not in query_lower:
                query = f"({query}) LIMIT {max_rows}"
            
            result = self.conn.execute(query).fetchdf()
            return {
                'success': True,
                'data': result,
                'row_count': len(result),
                'columns': list(result.columns)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'query': query
            }
    
    def get_schema_info(self) -> str:
        """
        Get schema information for all loaded tables.
        
        Returns:
            Formatted string describing table schemas
        """
        schema_parts = []
        
        for table_name in self._loaded_tables:
            try:
                # Get column info
                cols = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()
                col_list = [f"  - {row['column_name']}: {row['column_type']}" 
                           for _, row in cols.iterrows()]
                
                # Get row count
                count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                
                schema_parts.append(
                    f"Table: {table_name} ({count:,} rows)\n" + 
                    "\n".join(col_list[:30])  # Limit columns shown
                )
            except Exception as e:
                schema_parts.append(f"Table: {table_name} (error: {e})")
        
        return "\n\n".join(schema_parts)
    
    def get_column_stats(self, table: str, column: str) -> Dict[str, Any]:
        """
        Get statistics for a column.
        
        Args:
            table: Table name
            column: Column name
            
        Returns:
            Dict with column statistics
        """
        query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT "{column}") as unique_values,
            COUNT(*) - COUNT("{column}") as null_count,
            MODE("{column}") as mode_value
        FROM {table}
        """
        result = self.execute_sql(query)
        if 'error' in result.columns:
            return {'error': result['error'].iloc[0]}
        
        row = result.iloc[0]
        return {
            'total': int(row['total']),
            'unique_values': int(row['unique_values']),
            'null_count': int(row['null_count']),
            'mode_value': row['mode_value']
        }
    
    def get_value_distribution(self, table: str, column: str, top_n: int = 20) -> pd.DataFrame:
        """
        Get value distribution for a column.
        
        Args:
            table: Table name
            column: Column name
            top_n: Number of top values to return
            
        Returns:
            DataFrame with value, count, percentage
        """
        query = f"""
        SELECT 
            "{column}" as value,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
        FROM {table}
        GROUP BY "{column}"
        ORDER BY count DESC
        LIMIT {top_n}
        """
        return self.execute_sql(query)
    
    def get_conditional_distribution(self, 
                                     table: str,
                                     target_col: str, 
                                     group_by_col: str,
                                     top_n: int = 50) -> pd.DataFrame:
        """
        Get target distribution grouped by another column.
        
        Useful for finding predictive features.
        
        Args:
            table: Table name
            target_col: Target column to analyze
            group_by_col: Column to group by
            top_n: Limit results
            
        Returns:
            DataFrame with group, mode_target, mode_count, total
        """
        query = f"""
        WITH grouped AS (
            SELECT 
                "{group_by_col}" as group_val,
                "{target_col}" as target_val,
                COUNT(*) as cnt
            FROM {table}
            GROUP BY "{group_by_col}", "{target_col}"
        ),
        ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY group_val ORDER BY cnt DESC) as rn,
                SUM(cnt) OVER (PARTITION BY group_val) as total
            FROM grouped
        )
        SELECT 
            group_val,
            target_val as mode_target,
            cnt as mode_count,
            total,
            ROUND(cnt * 100.0 / total, 1) as mode_pct
        FROM ranked
        WHERE rn = 1
        ORDER BY total DESC
        LIMIT {top_n}
        """
        return self.execute_sql(query)
    
    def find_best_lookup_keys(self, 
                              table: str,
                              target_col: str,
                              candidate_cols: List[str],
                              min_coverage: float = 0.01) -> pd.DataFrame:
        """
        Find the best single-column lookup keys for prediction.
        
        Ranks columns by their ability to predict the target.
        
        Args:
            table: Table name
            target_col: Target column to predict
            candidate_cols: List of potential key columns
            min_coverage: Minimum coverage threshold
            
        Returns:
            DataFrame ranking columns by predictive power
        """
        results = []
        
        for col in candidate_cols:
            if col == target_col:
                continue
            
            query = f"""
            WITH grouped AS (
                SELECT 
                    "{col}" as key_val,
                    "{target_col}" as target_val,
                    COUNT(*) as cnt
                FROM {table}
                WHERE "{col}" IS NOT NULL
                GROUP BY "{col}", "{target_col}"
            ),
            best_per_key AS (
                SELECT 
                    key_val,
                    FIRST(target_val ORDER BY cnt DESC) as best_target,
                    MAX(cnt) as best_cnt,
                    SUM(cnt) as total_cnt
                FROM grouped
                GROUP BY key_val
            )
            SELECT 
                '{col}' as lookup_column,
                COUNT(*) as unique_keys,
                SUM(best_cnt) as correct_predictions,
                SUM(total_cnt) as total_rows,
                ROUND(SUM(best_cnt) * 100.0 / SUM(total_cnt), 2) as accuracy_pct
            FROM best_per_key
            """
            
            result = self.execute_sql(query)
            if 'error' not in result.columns and len(result) > 0:
                results.append(result.iloc[0].to_dict())
        
        if not results:
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        return df.sort_values('accuracy_pct', ascending=False)
    
    def generate_lookup_table(self,
                              table: str,
                              key_col: str,
                              target_col: str,
                              min_count: int = 1) -> Dict[str, str]:
        """
        Generate a lookup dictionary from key to most common target.
        
        Args:
            table: Table name
            key_col: Column to use as lookup key
            target_col: Target column
            min_count: Minimum occurrences to include
            
        Returns:
            Dict mapping key values to target values
        """
        query = f"""
        WITH grouped AS (
            SELECT 
                "{key_col}" as key_val,
                "{target_col}" as target_val,
                COUNT(*) as cnt
            FROM {table}
            WHERE "{key_col}" IS NOT NULL
            GROUP BY "{key_col}", "{target_col}"
        ),
        ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (PARTITION BY key_val ORDER BY cnt DESC) as rn
            FROM grouped
        )
        SELECT key_val, target_val
        FROM ranked
        WHERE rn = 1 AND cnt >= {min_count}
        """
        
        result = self.execute_sql(query)
        if 'error' in result.columns:
            return {}
        
        return dict(zip(result['key_val'].astype(str), result['target_val'].astype(str)))


# Convenience function
def create_analyzer(train_df: Optional[pd.DataFrame] = None) -> DataAnalyzer:
    """
    Create a DataAnalyzer, optionally preloading a DataFrame.
    
    Args:
        train_df: Optional training DataFrame to load as 'train' table
        
    Returns:
        Configured DataAnalyzer instance
    """
    analyzer = DataAnalyzer()
    if train_df is not None:
        analyzer.load_dataframe('train', train_df)
    return analyzer
