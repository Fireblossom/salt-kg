"""
Plot Figure 2: Cross-drift correlation heatmap + Drift vs Accuracy scatter.
Output: paper/figures/drift_analysis.png

Requires: data/salt/JoinedTables_train.parquet, data/salt/JoinedTables_test.parquet
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import duckdb

# ═══════════════════════════════════════════
# Step 1: Compute drift data from parquets
# ═══════════════════════════════════════════
train = pd.read_parquet('data/salt/JoinedTables_train.parquet')
test = pd.read_parquet('data/salt/JoinedTables_test.parquet')

fields = {
    'CUSTOMERPAYMENTTERMS': 'CUSTOMERPAYMENTTERMS',
    'SALESGROUP': 'SALESGROUP',
    'HEADERINCOTERMS': 'HEADERINCOTERMSCLASSIFICATION',
    'SHIPPINGCONDITION': 'SHIPPINGCONDITION',
    'ITEMINCOTERMS': 'ITEMINCOTERMSCLASSIFICATION',
    'PLANT': 'PLANT',
    'SHIPPINGPOINT': 'SHIPPINGPOINT',
    'SALESOFFICE': 'SALESOFFICE',
}

con = duckdb.connect()
con.register('train', train)
con.register('test', test)

names = list(fields.keys())

# Per-field drift rates
drift = {}
for name, col in fields.items():
    result = con.execute(f"""
        WITH train_mode AS (
            SELECT "SOLDTOPARTY", MODE("{col}") AS train_val FROM train GROUP BY "SOLDTOPARTY"
        ),
        test_mode AS (
            SELECT "SOLDTOPARTY", MODE("{col}") AS test_val FROM test GROUP BY "SOLDTOPARTY"
        ),
        comparison AS (
            SELECT tr.train_val, te.test_val,
                   CASE WHEN tr.train_val != te.test_val THEN 1 ELSE 0 END AS drifted
            FROM train_mode tr JOIN test_mode te ON tr."SOLDTOPARTY" = te."SOLDTOPARTY"
        )
        SELECT COUNT(*) AS total, SUM(drifted) AS n_drifted,
               SUM(drifted)*100.0/COUNT(*) AS drift_pct
        FROM comparison
    """).fetchdf()
    drift[name] = {
        'drift_pct': float(result['drift_pct'].iloc[0]),
        'total': int(result['total'].iloc[0]),
        'n_drifted': int(result['n_drifted'].iloc[0]),
    }
    print(f"  {name:<25} drift={drift[name]['drift_pct']:.1f}%")

# Cross-drift correlation matrix: P(col drifts | row drifts)
cross = np.zeros((len(names), len(names)))
for i, (na, ca) in enumerate(fields.items()):
    for j, (nb, cb) in enumerate(fields.items()):
        if i == j:
            cross[i][j] = 100.0
            continue
        result = con.execute(f"""
            WITH train_a AS (SELECT "SOLDTOPARTY", MODE("{ca}") AS val FROM train GROUP BY "SOLDTOPARTY"),
                 test_a  AS (SELECT "SOLDTOPARTY", MODE("{ca}") AS val FROM test GROUP BY "SOLDTOPARTY"),
                 train_b AS (SELECT "SOLDTOPARTY", MODE("{cb}") AS val FROM train GROUP BY "SOLDTOPARTY"),
                 test_b  AS (SELECT "SOLDTOPARTY", MODE("{cb}") AS val FROM test GROUP BY "SOLDTOPARTY"),
                 drifted_a AS (
                     SELECT ta."SOLDTOPARTY" FROM train_a ta
                     JOIN test_a ea ON ta."SOLDTOPARTY" = ea."SOLDTOPARTY"
                     WHERE ta.val != ea.val
                 ),
                 drifted_b AS (
                     SELECT tb."SOLDTOPARTY" FROM train_b tb
                     JOIN test_b eb ON tb."SOLDTOPARTY" = eb."SOLDTOPARTY"
                     WHERE tb.val != eb.val
                 )
            SELECT
                (SELECT COUNT(*) FROM drifted_a) AS total_a,
                (SELECT COUNT(*) FROM drifted_a da
                 JOIN drifted_b db ON da."SOLDTOPARTY" = db."SOLDTOPARTY") AS both_drifted
        """).fetchdf()
        total_a = int(result['total_a'].iloc[0])
        both = int(result['both_drifted'].iloc[0])
        cross[i][j] = (both / total_a * 100) if total_a > 0 else 0

con.close()

# ═══════════════════════════════════════════
# Step 2: Plot
# ═══════════════════════════════════════════
short = {
    'CUSTOMERPAYMENTTERMS': 'CustPayment',
    'SALESGROUP': 'SalesGroup',
    'HEADERINCOTERMS': 'HdrIncoterms',
    'SHIPPINGCONDITION': 'ShipCond',
    'ITEMINCOTERMS': 'ItmIncoterms',
    'PLANT': 'Plant',
    'SHIPPINGPOINT': 'ShipPoint',
    'SALESOFFICE': 'SalesOffice',
}

acc_vals = {
    'CUSTOMERPAYMENTTERMS': 82.9, 'SALESGROUP': 70.0,
    'HEADERINCOTERMS': 77.2, 'SHIPPINGCONDITION': 69.6,
    'ITEMINCOTERMS': 77.2, 'PLANT': 99.7,
    'SHIPPINGPOINT': 98.7, 'SALESOFFICE': 99.9,
}
gnn_acc = {
    'CUSTOMERPAYMENTTERMS': 37.5, 'SALESGROUP': 15.8,
    'HEADERINCOTERMS': 62.2, 'SHIPPINGCONDITION': 56.9,
    'ITEMINCOTERMS': 69.4, 'PLANT': 99.5,
    'SHIPPINGPOINT': 98.4, 'SALESOFFICE': 99.9,
}
cardinality = {
    'CUSTOMERPAYMENTTERMS': 156, 'SALESGROUP': 543,
    'HEADERINCOTERMS': 14, 'SHIPPINGCONDITION': 52,
    'ITEMINCOTERMS': 14, 'PLANT': 35,
    'SHIPPINGPOINT': 88, 'SALESOFFICE': 30,
}

# Sort by drift rate descending for heatmap
order = sorted(range(len(names)), key=lambda i: drift[names[i]]['drift_pct'], reverse=True)
sorted_names = [names[i] for i in order]
sorted_short = [short[n] for n in sorted_names]
sorted_cross = cross[np.ix_(order, order)]

fig = plt.figure(figsize=(16, 7))
gs = fig.add_gridspec(1, 2, width_ratios=[1.1, 1], wspace=0.35)

# ─── Panel A: Cross-drift heatmap ───
ax1 = fig.add_subplot(gs[0])
mask_cross = sorted_cross.copy()
np.fill_diagonal(mask_cross, np.nan)
cmap = plt.cm.YlOrRd.copy()
cmap.set_bad('#f0f0f0')
im = ax1.imshow(mask_cross, cmap=cmap, vmin=0, vmax=100, aspect='equal')

for i in range(len(sorted_names)):
    for j in range(len(sorted_names)):
        if i == j:
            ax1.text(j, i, '–', ha='center', va='center', fontsize=9, color='#aaa')
        else:
            val = sorted_cross[i][j]
            color = 'white' if val > 60 else 'black'
            weight = 'bold' if val > 80 else 'normal'
            ax1.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=8,
                     fontweight=weight, color=color)

ax1.set_xticks(range(len(sorted_short)))
ax1.set_xticklabels(sorted_short, rotation=45, ha='right', fontsize=9)
ax1.set_yticks(range(len(sorted_short)))
ax1.set_yticklabels(sorted_short, fontsize=9)

# Drift rate labels on right y-axis
ax1_r = ax1.twinx()
ax1_r.set_ylim(ax1.get_ylim())
ax1_r.set_yticks(range(len(sorted_names)))
drift_labels = [f"{drift[n]['drift_pct']:.1f}%" for n in sorted_names]
ax1_r.set_yticklabels(drift_labels, fontsize=9, color='#dc2626', fontweight='bold')
ax1_r.tick_params(axis='y', length=0)
ax1_r.set_ylabel('Drift Rate', fontsize=10, color='#dc2626', fontweight='bold')

cbar = plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.12)
cbar.set_label('Co-drift (%)', fontsize=9)

ax1.set_title('(a) Cross-Drift Correlation\n(% of row-drifted customers also drifted in column)',
              fontsize=11, fontweight='bold', pad=10)

# ─── Panel B: Drift vs Accuracy scatter ───
ax2 = fig.add_subplot(gs[1])

# Manual label offsets to avoid overlap
label_pos = {
    'SALESOFFICE':          ( 6,  -2),
    'PLANT':                ( 6,  -2),
    'SHIPPINGPOINT':        ( 6,  -2),
    'CUSTOMERPAYMENTTERMS': ( 6,  -2),
    'HEADERINCOTERMS':      ( 6,   5),
    'ITEMINCOTERMS':        ( 6, -10),
    'SALESGROUP':           ( 6,   5),
    'SHIPPINGCONDITION':    (-75, -10),
}

for n in names:
    d = drift[n]['drift_pct']
    a_ours = acc_vals[n]
    a_gnn = gnn_acc[n]
    size = np.log2(cardinality[n] + 1) * 25

    ax2.scatter(d, a_ours, s=size, c='#3b82f6', alpha=0.85,
                edgecolors='white', linewidths=1.5, zorder=5)
    ax2.scatter(d, a_gnn, s=size, c='#f97316', alpha=0.85,
                edgecolors='white', linewidths=1.5, zorder=4)
    ax2.plot([d, d], [a_gnn, a_ours], '--', color='#94a3b8', lw=1, alpha=0.4, zorder=3)

    ox, oy = label_pos[n]
    ax2.annotate(short[n], (d, a_ours), xytext=(ox, oy),
                 textcoords='offset points', fontsize=8, color='#1e40af', fontweight='bold')

# Trend line for non-trivial fields (accuracy < 95%)
mid = [n for n in names if 50 < acc_vals[n] < 95]
if mid:
    xt = [drift[n]['drift_pct'] for n in mid]
    yt = [acc_vals[n] for n in mid]
    z = np.polyfit(xt, yt, 1)
    p = np.poly1d(z)
    xl = np.linspace(min(xt)-3, max(xt)+3, 50)
    ax2.plot(xl, p(xl), '-', color='#3b82f6', alpha=0.2, lw=2.5, zorder=2)
    # R² annotation
    yp = p(np.array(xt))
    ss_res = np.sum((np.array(yt) - yp)**2)
    ss_tot = np.sum((np.array(yt) - np.mean(yt))**2)
    r2 = 1 - ss_res / ss_tot
    ax2.text(0.97, 0.55, f'slope = {z[0]:.2f}%/pp\nR² = {r2:.2f}',
             transform=ax2.transAxes, fontsize=8, ha='right', va='top',
             color='#3b82f6', alpha=0.6, fontstyle='italic')

from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#3b82f6', markersize=10,
           label='Ours (Cascade)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#f97316', markersize=10,
           label='GNN (RelBench v2)'),
    Line2D([0], [0], linestyle='--', color='#94a3b8', lw=1, label='Cascade advantage'),
]
ax2.legend(handles=legend_elements, fontsize=9, loc='lower left',
           framealpha=0.9, edgecolor='#e2e8f0')

ax2.set_xlabel('Customer Drift Rate (%)', fontsize=11)
ax2.set_ylabel('Test Accuracy (%)', fontsize=11)
ax2.set_title('(b) Drift Rate vs. Accuracy\n(bubble size ∝ field cardinality)',
              fontsize=11, fontweight='bold', pad=10)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.set_xlim(-3, 50)
ax2.set_ylim(10, 105)

plt.savefig('paper/figures/drift_analysis.png', dpi=200, bbox_inches='tight')
print("Saved paper/figures/drift_analysis.png")
