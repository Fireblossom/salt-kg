"""
rel-arxiv / author-category — Predict author's primary research category
Temporal-weighted MODE: papers in last 1yr get 4x, 2yr 3x, 3yr 2x, older 1x.
Uses on-the-fly computation with proper temporal cutoff per split.
"""
import duckdb
import pandas as pd


def predict(task_df, db):
    papers = db.table_dict['papers'].df
    pa = db.table_dict['paperAuthors'].df
    cats = db.table_dict['categories'].df

    # Determine cutoff: all task rows share the same date (val=2022-01-01, test=2023-01-01)
    time_col = 'date' if 'date' in task_df.columns else 'Date'
    cutoff = str(task_df[time_col].iloc[0].date())

    con = duckdb.connect()
    con.register('papers', papers)
    con.register('pa', pa)
    con.register('cats', cats)
    con.register('task', task_df)

    # Global mode from training-range data
    gm = int(con.execute(f"""
        SELECT MODE(c."Category")
        FROM pa JOIN papers p ON pa."Paper_ID" = p."Paper_ID"
        JOIN cats c ON p."Primary_Category_ID" = c."Category_ID"
        WHERE p."Submission_Date" < '{cutoff}'
    """).fetchone()[0])

    # Temporal-weighted MODE per author
    r = con.execute(f"""
        WITH weighted AS (
            SELECT pa."Author_ID" AS aid, c."Category" AS cat,
                CASE
                    WHEN p."Submission_Date" >= '{cutoff}'::DATE - INTERVAL '1 year' THEN 4
                    WHEN p."Submission_Date" >= '{cutoff}'::DATE - INTERVAL '2 years' THEN 3
                    WHEN p."Submission_Date" >= '{cutoff}'::DATE - INTERVAL '3 years' THEN 2
                    ELSE 1
                END AS weight
            FROM pa JOIN papers p ON pa."Paper_ID" = p."Paper_ID"
            JOIN cats c ON p."Primary_Category_ID" = c."Category_ID"
            WHERE p."Submission_Date" < '{cutoff}'
        ),
        expanded AS (
            SELECT aid, cat FROM weighted
            UNION ALL SELECT aid, cat FROM weighted WHERE weight >= 2
            UNION ALL SELECT aid, cat FROM weighted WHERE weight >= 3
            UNION ALL SELECT aid, cat FROM weighted WHERE weight >= 4
        )
        SELECT CAST(aid AS VARCHAR) AS aid, MODE(cat) AS cat
        FROM expanded GROUP BY aid
    """).fetchdf()
    L0 = dict(zip(r['aid'].tolist(), [int(v) for v in r['cat'].tolist()]))

    con.close()

    preds = [L0.get(str(a), gm) for a in task_df['Author_ID']]
    return pd.Series(preds, index=task_df.index)
