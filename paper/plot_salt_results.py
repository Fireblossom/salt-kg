"""
Plot Figure 1: KG Ablation + Cascade vs GNN bar charts.
Output: paper/figures/salt_results.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# ─── Data ───
fields_ablation = ['PLANT', 'SHPPT', 'HDR\nINCO', 'ITM\nINCO', 'SHP\nCOND', 'SALES\nGRP', 'CUST\nPAYMT', 'SALES\nOFF']
without_kg = [76.6, 67.0, 69.1, 69.1, 56.6, 68.9, 80.0, 99.8]
with_kg    = [99.5, 78.9, 73.0, 72.9, 59.3, 71.0, 81.8, 99.9]

fields_gnn = ['CUST\nPAYMT', 'SALES\nGRP', 'HDR\nINCO', 'ITM\nINCO', 'SHP\nCOND', 'SHPPT', 'PLANT', 'SALES\nOFF']
ours = [82.9, 70.0, 77.2, 77.2, 69.6, 98.7, 99.7, 99.9]
gnn  = [37.5, 15.8, 62.2, 69.4, 56.9, 98.4, 99.5, 99.9]

# ─── Figure ───
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
width = 0.35

# Panel A: KG Ablation
ax = axes[0]
x = np.arange(len(fields_ablation))
ax.bar(x - width/2, without_kg, width, label='Without KG', color='#94a3b8', edgecolor='white')
ax.bar(x + width/2, with_kg, width, label='With KG', color='#3b82f6', edgecolor='white')
for i, (wk, wo) in enumerate(zip(with_kg, without_kg)):
    d = wk - wo
    ax.annotate(f'+{d:.1f}', xy=(x[i] + width/2, wk), xytext=(0, 5),
                textcoords='offset points', ha='center', fontsize=8, fontweight='bold',
                color='#059669' if d >= 5 else '#6b7280')
ax.set_ylabel('Test Accuracy (%)', fontsize=11)
ax.set_title('(a) KG Ablation: Without vs With KG Guidance', fontsize=12, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(fields_ablation, fontsize=8)
ax.legend(fontsize=9); ax.set_ylim(50, 108)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# Panel B: Ours vs GNN
ax = axes[1]
x2 = np.arange(len(fields_gnn))
ax.bar(x2 - width/2, ours, width, label='Ours (Cascade)', color='#3b82f6', edgecolor='white')
ax.bar(x2 + width/2, gnn, width, label='GNN (RelBench v2)', color='#f97316', edgecolor='white')
for i, (o, g) in enumerate(zip(ours, gnn)):
    delta = o - g
    if abs(delta) > 2:
        ax.annotate(f'+{delta:.0f}', xy=(x2[i] - width/2, o), xytext=(0, 5),
                    textcoords='offset points', ha='center', fontsize=8, fontweight='bold',
                    color='#059669')
ax.set_ylabel('Test Accuracy (%)', fontsize=11)
ax.set_title('(b) Cascade vs GNN on SALT-KG', fontsize=12, fontweight='bold')
ax.set_xticks(x2); ax.set_xticklabels(fields_gnn, fontsize=8)
ax.legend(fontsize=9); ax.set_ylim(0, 115)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig('paper/figures/salt_results.png', dpi=200, bbox_inches='tight')
print("Saved paper/figures/salt_results.png")
