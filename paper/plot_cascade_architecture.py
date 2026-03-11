"""
Plot Figure 0 (Method): Cascade architecture diagram for CUSTOMERPAYMENTTERMS.
Shows KG rule -> hierarchical cascade levels -> prediction.
Output: paper/figures/cascade_architecture.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as path_effects
from matplotlib.patches import FancyArrowPatch
import numpy as np

# Apply professional styling
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

def rounded_box(ax, xy, w, h, text, facecolor='#ffffff', edgecolor='#334155', textcolor='#0f172a',
                fontsize=9, fontweight='normal', alpha=1.0, lw=1.5, shadow=True):
    """Draw a rounded rectangle with centered text and optional drop shadow."""
    box = mpatches.FancyBboxPatch(
        xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=lw, alpha=alpha, zorder=3)
    
    if shadow:
        box.set_path_effects([
            path_effects.SimplePatchShadow(offset=(1.5, -1.5), shadow_rgbFace=(0,0,0), alpha=0.15),
            path_effects.Normal()
        ])
    
    ax.add_patch(box)
    
    cx, cy = xy[0] + w / 2, xy[1] + h / 2
    ax.text(cx, cy, text, ha='center', va='center',
            fontsize=fontsize, color=textcolor, fontweight=fontweight,
            linespacing=1.5, zorder=4)
    return cx, cy

def curved_arrow(ax, start, end, color='#475569', lw=1.5, style='-|>', rad=0.1, label='', label_offset=(0,0)):
    """Draw a curved arrow."""
    arrow = FancyArrowPatch(start, end,
                            connectionstyle=f"arc3,rad={rad}",
                            arrowstyle=style, color=color, lw=lw,
                            mutation_scale=12, zorder=2)
    ax.add_patch(arrow)
    if label:
        # Approximate midpoint for label
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        
        # Add a small white bounding box behind text for readability
        bbox_props = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.9)
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=8, color=color, fontstyle='italic', zorder=5, bbox=bbox_props)

fig, ax = plt.subplots(figsize=(12, 5.5))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# Colors
C_KG_bg     = '#fdf4ff'
C_KG_border = '#c026d3'
C_L0_bg     = '#eff6ff'
C_L0_border = '#3b82f6'
C_L1_bg     = '#f0fdf4'
C_L1_border = '#22c55e'
C_L2_bg     = '#f8fafc'
C_L2_border = '#64748b'
C_OUT_bg    = '#fefce8'
C_OUT_border= '#eab308'

# ─── Title ───
ax.text(0.5, 0.96, 'Cascade Architecture: CUSTOMERPAYMENTTERMS',
        ha='center', va='top', fontsize=15, fontweight='bold', color='#0f172a')
ax.text(0.5, 0.90, 'KG-guided hierarchical lookup with statistical mode aggregation',
        ha='center', va='top', fontsize=11, color='#475569', fontstyle='italic')

y_top = 0.55
h_box = 0.22

# KG Rule
cx_kg, cy_kg = rounded_box(ax, (0.02, y_top), 0.16, h_box,
            'Knowledge Graph\n─────────────\nAccess Sequence:\nSOLDTO + DOCTYPE\nthen SOLDTO alone',
            facecolor=C_KG_bg, edgecolor=C_KG_border, textcolor='#701a75', fontsize=8.5)

# L0
cx_l0, cy_l0 = rounded_box(ax, (0.28, y_top), 0.19, h_box,
            'Level 0 (L0)\n─────────────\nSOLDTOPARTY ×\nSALESDOCTYPE\n(69K keys | 95.3% hit)',
            facecolor=C_L0_bg, edgecolor=C_L0_border, textcolor='#1e3a8a', fontsize=8.5)

# L1
cx_l1, cy_l1 = rounded_box(ax, (0.55, y_top), 0.17, h_box,
            'Level 1 (L1)\n─────────────\nSOLDTOPARTY\n(10K keys | 4.5% hit)',
            facecolor=C_L1_bg, edgecolor=C_L1_border, textcolor='#14532d', fontsize=8.5)

# L2
cx_l2, cy_l2 = rounded_box(ax, (0.80, y_top), 0.17, h_box,
            'Level 2 (L2)\n─────────────\nGlobal MODE\n(1 key | 0.2% hit)',
            facecolor=C_L2_bg, edgecolor=C_L2_border, textcolor='#1e293b', fontsize=8.5)

# Lateral Arrows
curved_arrow(ax, (0.02+0.16, cy_kg), (0.28, cy_l0), color=C_KG_border, rad=0, label=' guides ')
curved_arrow(ax, (0.28+0.19, cy_l0), (0.55, cy_l1), color='#ef4444', rad=0, label=' miss ')
curved_arrow(ax, (0.55+0.17, cy_l1), (0.80, cy_l2), color='#ef4444', rad=0, label=' miss ')

# ─── Row 2: Outputs ───
y_bot = 0.15
h_out = 0.16

cx_out, cy_out = rounded_box(ax, (0.30, y_bot), 0.45, h_out,
            'Prediction Output: CUSTOMERPAYMENTTERMS = "NT30"\n'
            'Test Acc: 82.9%  |  Inference: Object Key Lookup (0 ms GPU)',
            facecolor=C_OUT_bg, edgecolor=C_OUT_border, textcolor='#713f12', fontsize=9.5, fontweight='bold')

# Downward Arrows
curved_arrow(ax, (cx_l0, y_top), (cx_out - 0.1, y_bot + h_out), color=C_L0_border, rad=0.1, label='hit')
curved_arrow(ax, (cx_l1, y_top), (cx_out, y_bot + h_out), color=C_L1_border, rad=0.0, label='hit')
curved_arrow(ax, (cx_l2, y_top), (cx_out + 0.1, y_bot + h_out), color=C_L2_border, rad=-0.1, label='hit')

# ─── Info Panels ───
ax.text(0.02, 0.12, 'Cascade Principle:\n• More specific keys first\n• First match wins\n• Mirrors SAP Config',
        fontsize=8.5, color='#334155', va='bottom',
        bbox=dict(boxstyle='round,pad=0.5,rounding_size=0.1', facecolor='#f8fafc', edgecolor='#cbd5e1'),
        linespacing=1.6)

ax.text(0.98, 0.12, 'KG Ablation Insight:\nWithout KG, schema-only approach\nuses just L1 + L2 → 80.0% (−2.9 pp)',
        fontsize=8.5, color='#991b1b', ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.5,rounding_size=0.1', facecolor='#fef2f2', edgecolor='#fecaca'),
        linespacing=1.6)

plt.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
plt.savefig('paper/figures/cascade_architecture.png', dpi=300, bbox_inches='tight', facecolor='white')
print("Saved paper/figures/cascade_architecture.png")
