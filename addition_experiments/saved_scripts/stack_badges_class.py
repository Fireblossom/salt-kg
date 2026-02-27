"""
rel-stack / badges-class — Predict badge class (0=gold, 1=silver, 2=bronze)
Join: badge → UserId → per-user MODE(Class) from training data
Fallback: Global MODE (2 = bronze)
"""
import json
import pandas as pd
import duckdb
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'stack_badges_class_mapping.json').read_text())
L0 = _m['L0_user_mode']
MODE = _m['mode']


def predict(task_df, db):
    con = duckdb.connect()
    con.register('task', task_df)
    con.register('badges', db.table_dict['badges'].df)

    features = con.execute("""
        SELECT t."Id", CAST(b."UserId" AS VARCHAR) AS uid
        FROM task t
        LEFT JOIN badges b ON t."Id" = b."Id"
    """).fetchdf()
    con.close()

    preds = []
    for _, row in features.iterrows():
        uid = row['uid']
        if uid is not None and uid in L0:
            preds.append(L0[uid])
        else:
            preds.append(MODE)

    return pd.Series(preds, index=task_df.index)
