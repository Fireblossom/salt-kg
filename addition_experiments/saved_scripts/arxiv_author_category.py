"""
rel-arxiv / author-category — Predict author's primary research category
Lookup cascade (precomputed in arxiv_author_category_mapping.json):
  L0: Author's own publication MODE (author → paperAuthors → papers → categories)
  L1: Coauthor network MODE (for authors not in L0)
  Fallback: Global category MODE
"""
import json
import pandas as pd
from pathlib import Path

_m = json.loads((Path(__file__).parent / 'arxiv_author_category_mapping.json').read_text())
L0 = _m['L0_direct']
L1 = _m['L1_coauthor']
MODE = _m['global_mode']


def predict(task_df, db=None):
    preds = []
    for _, row in task_df.iterrows():
        aid = str(row['Author_ID'])
        if aid in L0:
            preds.append(L0[aid])
        elif aid in L1:
            preds.append(L1[aid])
        else:
            preds.append(MODE)
    return pd.Series(preds, index=task_df.index)
