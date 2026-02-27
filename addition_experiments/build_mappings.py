"""
Build lookup mappings for all relbench prediction tasks.
Follows SALT-KG pattern: SQL GROUP BY + MODE() → hierarchical lookup cascades.

Usage:
    python experiments/build_mappings.py --task trial_has_dmc
    python experiments/build_mappings.py --task all
"""
import argparse
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd


OUT_DIR = Path(__file__).parent / 'saved_scripts'
OUT_DIR.mkdir(exist_ok=True)


def save_mapping(name, mapping):
    path = OUT_DIR / f'{name}_mapping.json'
    path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False))
    print(f'  Saved {path} ({path.stat().st_size:,} bytes)')


# ──────────────────────────────────────────────────
# rel-arxiv / author-category
# ──────────────────────────────────────────────────

def build_arxiv_author_category():
    """
    Multi-hop join: author → paperAuthors → papers → categories
    L0: Per-author MODE(Category) from their own publications
    L1: Per-author MODE from coauthor network (for unseen authors)
    Fallback: Global MODE
    """
    from relbench.tasks import get_task

    print('=== arxiv / author-category ===')
    task = get_task('rel-arxiv', 'author-category')
    db = task.dataset.get_db()
    train_table = task.get_table('train')
    train_df = train_table.df

    papers = db.table_dict['papers'].df
    pa = db.table_dict['paperAuthors'].df
    cats = db.table_dict['categories'].df

    # Get the timestamp cutoff from the train table
    train_author_ids = set(train_df['Author_ID'].unique())

    con = duckdb.connect()
    con.register('papers', papers)
    con.register('pa', pa)
    con.register('cats', cats)

    # L0: For each author, MODE of their papers' categories
    # Only use papers that exist before the train cutoff
    l0_df = con.execute("""
        SELECT
            CAST(pa.Author_ID AS VARCHAR) AS author_id,
            MODE(cats.Category) AS category,
            COUNT(*) AS cnt
        FROM pa
        JOIN papers p ON pa.Paper_ID = p.Paper_ID
        JOIN cats ON p.Primary_Category_ID = cats.Category_ID
        GROUP BY pa.Author_ID
        HAVING COUNT(*) >= 1
    """).fetchdf()

    L0 = dict(zip(l0_df['author_id'], l0_df['category'].astype(int)))
    print(f'  L0 (direct author mode): {len(L0)} authors')

    # L1: For unseen authors, get coauthor network mode
    # For each author not in L0, find their coauthors' categories
    l1_df = con.execute("""
        WITH author_cats AS (
            SELECT pa.Author_ID,
                   MODE(cats.Category) AS category
            FROM pa
            JOIN papers p ON pa.Paper_ID = p.Paper_ID
            JOIN cats ON p.Primary_Category_ID = cats.Category_ID
            GROUP BY pa.Author_ID
        ),
        coauthor_pairs AS (
            SELECT DISTINCT a1.Author_ID AS author1, a2.Author_ID AS author2
            FROM pa a1
            JOIN pa a2 ON a1.Paper_ID = a2.Paper_ID AND a1.Author_ID != a2.Author_ID
        )
        SELECT
            CAST(cp.author1 AS VARCHAR) AS author_id,
            MODE(ac.category) AS category
        FROM coauthor_pairs cp
        JOIN author_cats ac ON cp.author2 = ac.Author_ID
        WHERE CAST(cp.author1 AS VARCHAR) NOT IN (SELECT author_id FROM l0_df)
        GROUP BY cp.author1
    """).fetchdf()

    L1 = dict(zip(l1_df['author_id'], l1_df['category'].astype(int)))
    print(f'  L1 (coauthor mode): {len(L1)} authors')

    # Global mode
    global_mode_val = con.execute("""
        SELECT MODE(cats.Category) FROM papers p
        JOIN cats ON p.Primary_Category_ID = cats.Category_ID
    """).fetchone()[0]
    global_mode = int(global_mode_val)
    print(f'  Global mode: {global_mode}')

    con.close()

    save_mapping('arxiv_author_category', {
        'L0_direct': L0,
        'L1_coauthor': L1,
        'global_mode': global_mode,
    })

# ──────────────────────────────────────────────────
# rel-stack / badges-class
# ──────────────────────────────────────────────────

def build_stack_badges_class():
    """
    Multiclass autocomplete classification: predict badge class (0=gold, 1=silver, 2=bronze).
    Join: badge → UserId → user's training badge class history
    L0: Per-UserId MODE(Class) — most specific
    Fallback: Global MODE (2 = bronze)
    Badge table only has (Id, UserId, Date) — no Name or TagBased columns.
    """
    from relbench.tasks import get_task

    print('=== stack / badges-class ===')
    task = get_task('rel-stack', 'badges-class')
    db = task.dataset.get_db()
    train_table = task.get_table('train')
    train_df = train_table.df

    badges = db.table_dict['badges'].df

    con = duckdb.connect()
    con.register('train', train_df)
    con.register('badges', badges)

    # L0: Per-UserId MODE(Class)
    l0 = con.execute("""
        SELECT CAST(b."UserId" AS VARCHAR) AS key,
               MODE(t."Class") AS val,
               COUNT(*) AS cnt
        FROM train t
        JOIN badges b ON t."Id" = b."Id"
        GROUP BY b."UserId"
        HAVING COUNT(*) >= 1
    """).fetchdf()
    L0 = {}
    for k, v in zip(l0['key'], l0['val']):
        L0[k] = int(v) if v is not None else 2
    print(f'  L0 (per-user MODE): {len(L0)} users')

    gm = int(con.execute('SELECT MODE("Class") FROM train').fetchone()[0])
    print(f'  Global mode: {gm}')

    con.close()

    save_mapping('stack_badges_class', {
        'L0_user_mode': L0,
        'mode': gm,
    })


# ──────────────────────────────────────────────────

BUILDERS = {
    'arxiv_author_category': build_arxiv_author_category,
    'stack_badges_class': build_stack_badges_class,
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', default='all',
                        help='Task name or "all"')
    args = parser.parse_args()

    if args.task == 'all':
        for name, fn in BUILDERS.items():
            fn()
    else:
        BUILDERS[args.task]()
