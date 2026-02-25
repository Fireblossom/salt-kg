"""
Build all prediction mappings with anti-overfitting measures.

Uses DuckDB for fast vectorized SQL operations (avoids pandas performance issues).

Usage:
    python3 agentic_solver/build_mappings.py

Applies:
- Minimum support thresholds per cascade level
- SHIPTOPARTY anchoring for Incoterms
- Structural fallback chains (DT+ORG level)
"""

import duckdb
import json
import time
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).parent.parent / 'data' / 'salt'
SCRIPTS_DIR = Path(__file__).parent / 'saved_scripts'


def build_lookup(con: duckdb.DuckDBPyConnection, keys: List[str], target: str,
                 min_support: int = 1) -> Dict[str, str]:
    """Build a mode-based lookup using SQL, with minimum support filtering."""
    if len(keys) == 1:
        key_expr = f'CAST("{keys[0]}" AS VARCHAR)'
    else:
        parts = [f'CAST("{k}" AS VARCHAR)' for k in keys]
        key_expr = " || '|' || ".join(parts)

    sql = f"""
    WITH counts AS (
        SELECT {key_expr} AS lookup_key,
               CAST("{target}" AS VARCHAR) AS val,
               COUNT(*) AS cnt
        FROM train
        GROUP BY 1, 2
    ),
    ranked AS (
        SELECT lookup_key, val, cnt,
               ROW_NUMBER() OVER (PARTITION BY lookup_key ORDER BY cnt DESC, val) AS rn
        FROM counts
    )
    SELECT lookup_key, val FROM ranked WHERE rn = 1 AND cnt >= {min_support}
    """
    rows = con.execute(sql).fetchall()
    return {r[0]: r[1] for r in rows}


def global_mode(con: duckdb.DuckDBPyConnection, target: str) -> str:
    """Get the global most frequent value for a target field."""
    sql = f"""
    SELECT CAST("{target}" AS VARCHAR) AS val, COUNT(*) AS cnt
    FROM train GROUP BY 1 ORDER BY cnt DESC LIMIT 1
    """
    return con.execute(sql).fetchone()[0]


def report(name: str, levels: Dict[str, dict], mode_val: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    total_keys = 0
    for level_name, info in levels.items():
        n = len(info['lookup'])
        total_keys += n
        print(f"  {level_name}: {n:,} keys (min_support={info['min_support']})")
    print(f"  mode: '{mode_val}'")
    print(f"  total keys: {total_keys:,}")


def build_customerpaymentterms(con: duckdb.DuckDBPyConnection) -> dict:
    target = 'CUSTOMERPAYMENTTERMS'
    levels = {
        'L0_SOLDTO_DT': {
            'lookup': build_lookup(con, ['SOLDTOPARTY', 'SALESDOCUMENTTYPE'], target, min_support=3),
            'min_support': 3,
        },
        'L1_SOLDTO': {
            'lookup': build_lookup(con, ['SOLDTOPARTY'], target, min_support=2),
            'min_support': 2,
        },
        'L2_DT_ORG': {
            'lookup': build_lookup(con, ['SALESDOCUMENTTYPE', 'SALESORGANIZATION'], target, min_support=1),
            'min_support': 1,
        },
        'L3_ORG': {
            'lookup': build_lookup(con, ['SALESORGANIZATION'], target, min_support=1),
            'min_support': 1,
        },
    }

    mode_val = global_mode(con, target)
    report('CUSTOMERPAYMENTTERMS', levels, mode_val)

    return {
        'L0_SOLDTO_DT': levels['L0_SOLDTO_DT']['lookup'],
        'L1_SOLDTO': levels['L1_SOLDTO']['lookup'],
        'L2_DT_ORG': levels['L2_DT_ORG']['lookup'],
        'L3_ORG': levels['L3_ORG']['lookup'],
        'mode': mode_val,
    }


def build_salesgroup(con: duckdb.DuckDBPyConnection) -> dict:
    target = 'SALESGROUP'
    levels = {
        'L0_SOLDTO_DT_SA': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SALESDOCUMENTTYPE', 'SALESORGANIZATION', 'DISTRIBUTIONCHANNEL', 'ORGANIZATIONDIVISION'],
                target, min_support=1),
            'min_support': 1,
        },
        'L1_SOLDTO_DT': {
            'lookup': build_lookup(con, ['SOLDTOPARTY', 'SALESDOCUMENTTYPE'], target, min_support=1),
            'min_support': 1,
        },
        'L2_SOLDTO': {
            'lookup': build_lookup(con, ['SOLDTOPARTY'], target, min_support=1),
            'min_support': 1,
        },
        'L3_DT_SA': {
            'lookup': build_lookup(con,
                ['SALESDOCUMENTTYPE', 'SALESORGANIZATION', 'DISTRIBUTIONCHANNEL', 'ORGANIZATIONDIVISION'],
                target, min_support=1),
            'min_support': 1,
        },
        'L4_SA': {
            'lookup': build_lookup(con,
                ['SALESORGANIZATION', 'DISTRIBUTIONCHANNEL', 'ORGANIZATIONDIVISION'],
                target, min_support=1),
            'min_support': 1,
        },
        'L5_ORG': {
            'lookup': build_lookup(con, ['SALESORGANIZATION'], target, min_support=1),
            'min_support': 1,
        },
    }

    mode_val = global_mode(con, target)
    report('SALESGROUP', levels, mode_val)

    return {
        'L0_SOLDTO_DT_SA': levels['L0_SOLDTO_DT_SA']['lookup'],
        'L1_SOLDTO_DT': levels['L1_SOLDTO_DT']['lookup'],
        'L2_SOLDTO': levels['L2_SOLDTO']['lookup'],
        'L3_DT_SA': levels['L3_DT_SA']['lookup'],
        'L4_SA': levels['L4_SA']['lookup'],
        'L5_ORG': levels['L5_ORG']['lookup'],
        'mode': mode_val,
    }


def build_incoterms(con: duckdb.DuckDBPyConnection, target: str) -> dict:
    levels = {
        'L0_SOLDTO_DT_ORG_SC': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SALESDOCUMENTTYPE', 'SALESORGANIZATION', 'SHIPPINGCONDITION'],
                target, min_support=5),
            'min_support': 5,
        },
        'L1_SOLDTO_DT_ORG': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SALESDOCUMENTTYPE', 'SALESORGANIZATION'],
                target, min_support=3),
            'min_support': 3,
        },
        'L2_SHIPTO_DT_ORG': {
            'lookup': build_lookup(con,
                ['SHIPTOPARTY', 'SALESDOCUMENTTYPE', 'SALESORGANIZATION'],
                target, min_support=3),
            'min_support': 3,
        },
        'L3_SOLDTO_SC': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SHIPPINGCONDITION'],
                target, min_support=3),
            'min_support': 3,
        },
        'L4_SOLDTO': {
            'lookup': build_lookup(con, ['SOLDTOPARTY'], target, min_support=2),
            'min_support': 2,
        },
        'L5_SHIPTO': {
            'lookup': build_lookup(con, ['SHIPTOPARTY'], target, min_support=2),
            'min_support': 2,
        },
        'L6_DT_ORG_SC': {
            'lookup': build_lookup(con,
                ['SALESDOCUMENTTYPE', 'SALESORGANIZATION', 'SHIPPINGCONDITION'],
                target, min_support=1),
            'min_support': 1,
        },
        'L7_DT_ORG': {
            'lookup': build_lookup(con,
                ['SALESDOCUMENTTYPE', 'SALESORGANIZATION'],
                target, min_support=1),
            'min_support': 1,
        },
        'L8_ORG': {
            'lookup': build_lookup(con, ['SALESORGANIZATION'], target, min_support=1),
            'min_support': 1,
        },
    }

    mode_val = global_mode(con, target)
    report(target, levels, mode_val)

    return {
        'L0_SOLDTO_DT_ORG_SC': levels['L0_SOLDTO_DT_ORG_SC']['lookup'],
        'L1_SOLDTO_DT_ORG': levels['L1_SOLDTO_DT_ORG']['lookup'],
        'L2_SHIPTO_DT_ORG': levels['L2_SHIPTO_DT_ORG']['lookup'],
        'L3_SOLDTO_SC': levels['L3_SOLDTO_SC']['lookup'],
        'L4_SOLDTO': levels['L4_SOLDTO']['lookup'],
        'L5_SHIPTO': levels['L5_SHIPTO']['lookup'],
        'L6_DT_ORG_SC': levels['L6_DT_ORG_SC']['lookup'],
        'L7_DT_ORG': levels['L7_DT_ORG']['lookup'],
        'L8_ORG': levels['L8_ORG']['lookup'],
        'mode': mode_val,
    }


def build_shippingcondition(con: duckdb.DuckDBPyConnection) -> dict:
    target = 'SHIPPINGCONDITION'
    levels = {
        'L0_SOLDTO_DT_SP': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SALESDOCUMENTTYPE', 'SHIPPINGPOINT'],
                target, min_support=3),
            'min_support': 3,
        },
        'L1_SHIPTO_DT_SP': {
            'lookup': build_lookup(con,
                ['SHIPTOPARTY', 'SALESDOCUMENTTYPE', 'SHIPPINGPOINT'],
                target, min_support=3),
            'min_support': 3,
        },
        'L2_DT_PLANT_SP': {
            'lookup': build_lookup(con,
                ['SALESDOCUMENTTYPE', 'PLANT', 'SHIPPINGPOINT'],
                target, min_support=1),
            'min_support': 1,
        },
        'L3_DT_SP': {
            'lookup': build_lookup(con,
                ['SALESDOCUMENTTYPE', 'SHIPPINGPOINT'],
                target, min_support=1),
            'min_support': 1,
        },
        'L4_SP': {
            'lookup': build_lookup(con, ['SHIPPINGPOINT'], target, min_support=1),
            'min_support': 1,
        },
        'L5_SOLDTO_DT': {
            'lookup': build_lookup(con,
                ['SOLDTOPARTY', 'SALESDOCUMENTTYPE'],
                target, min_support=2),
            'min_support': 2,
        },
    }

    mode_val = global_mode(con, target)
    report('SHIPPINGCONDITION', levels, mode_val)

    return {
        'L0_SOLDTO_DT_SP': levels['L0_SOLDTO_DT_SP']['lookup'],
        'L1_SHIPTO_DT_SP': levels['L1_SHIPTO_DT_SP']['lookup'],
        'L2_DT_PLANT_SP': levels['L2_DT_PLANT_SP']['lookup'],
        'L3_DT_SP': levels['L3_DT_SP']['lookup'],
        'L4_SP': levels['L4_SP']['lookup'],
        'L5_SOLDTO_DT': levels['L5_SOLDTO_DT']['lookup'],
        'mode': mode_val,
    }


def save_mapping(mapping: dict, filename: str):
    out = SCRIPTS_DIR / filename
    out.write_text(json.dumps(mapping, indent=2, ensure_ascii=False))
    print(f"  → Saved to {out.name}")


def main():
    start = time.time()

    print("Loading training data with DuckDB...")
    con = duckdb.connect()
    con.execute(f"CREATE TABLE train AS SELECT * FROM read_parquet('{DATA_DIR / 'JoinedTables_train.parquet'}')")
    n_rows = con.execute("SELECT COUNT(*) FROM train").fetchone()[0]
    n_cols = len(con.execute("SELECT * FROM train LIMIT 0").description)
    print(f"Train: {n_rows:,} rows, {n_cols} columns (loaded in {time.time()-start:.1f}s)\n")

    # 1. CUSTOMERPAYMENTTERMS
    save_mapping(build_customerpaymentterms(con), 'customerpaymentterms_mapping.json')

    # 2. SALESGROUP
    save_mapping(build_salesgroup(con), 'salesgroup_mapping.json')

    # 3. HEADERINCOTERMSCLASSIFICATION
    save_mapping(build_incoterms(con, 'HEADERINCOTERMSCLASSIFICATION'), 'headerincotermsclassification_mapping.json')

    # 4. ITEMINCOTERMSCLASSIFICATION
    save_mapping(build_incoterms(con, 'ITEMINCOTERMSCLASSIFICATION'), 'itemincotermsclassification_mapping.json')

    # 5. SHIPPINGCONDITION
    save_mapping(build_shippingcondition(con), 'shippingcondition_mapping_simple.json')

    con.close()
    print(f"\nAll mappings built successfully in {time.time()-start:.1f}s.")


if __name__ == '__main__':
    main()
