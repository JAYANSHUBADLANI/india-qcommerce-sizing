"""Visualization module for market sizing charts.

Generates:
- Tornado chart for sensitivity analysis
- Market share bar charts
- Bottom-up funnel waterfall
- Scenario comparison
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path


OUTPUT_DIR = Path(__file__).parent.parent / 'output'


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_tornado(tornado_data, base_tam_cr, output_path=None):
    """Generate a horizontal tornado chart showing sensitivity of TAM to each assumption."""
    ensure_output_dir()
    if output_path is None:
        output_path = OUTPUT_DIR / 'tornado_sensitivity.png'
    
    # Take top 6 most impactful
    data = tornado_data[:6]
    data = list(reversed(data))  # Reverse so largest is on top
    
    labels = [d['label'] for d in data]
    low_vals = [d['tam_at_low_cr'] for d in data]
    high_vals = [d['tam_at_high_cr'] for d in data]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    y_pos = np.arange(len(labels))
    
    # Draw bars from low to high
    for i, (label, low, high) in enumerate(zip(labels, low_vals, high_vals)):
        ax.barh(i, high - base_tam_cr, left=base_tam_cr, height=0.5,
                color='#2ecc71', alpha=0.8, label='High' if i == 0 else '')
        ax.barh(i, base_tam_cr - low, left=low, height=0.5,
                color='#e74c3c', alpha=0.8, label='Low' if i == 0 else '')
    
    # Base line
    ax.axvline(x=base_tam_cr, color='#2c3e50', linestyle='--', linewidth=1.5, label='Base')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('TAM (INR Crore)', fontsize=11)
    ax.set_title('Sensitivity Analysis: Impact of Each Assumption on TAM', fontsize=13, fontweight='bold')
    ax.legend(loc='lower right')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def plot_market_share_bars(shares_data, output_path=None):
    """Generate grouped bar chart of market shares by fiscal year."""
    ensure_output_dir()
    if output_path is None:
        output_path = OUTPUT_DIR / 'market_share.png'
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    years = list(shares_data.keys())
    x = np.arange(len(years))
    width = 0.25
    
    blinkit_shares = [shares_data[y].get('blinkit_share', 0) * 100 for y in years]
    instamart_shares = [shares_data[y].get('instamart_share', 0) * 100 for y in years]
    zepto_shares = [shares_data[y].get('zepto_share', 0) * 100 for y in years]
    
    bars1 = ax.bar(x - width, blinkit_shares, width, label='Blinkit', color='#e74c3c', alpha=0.85)
    bars2 = ax.bar(x, instamart_shares, width, label='Instamart', color='#f39c12', alpha=0.85)
    bars3 = ax.bar(x + width, zepto_shares, width, label='Zepto', color='#3498db', alpha=0.85)
    
    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{height:.1f}%',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords='offset points',
                           ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel('Market Share (%)', fontsize=11)
    ax.set_title('Quick Commerce Market Share by GOV (Big-3)', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=11)
    ax.legend()
    ax.set_ylim(0, 65)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def plot_scenario_comparison(scenarios, output_path=None):
    """Generate a horizontal bar chart comparing low/base/high scenarios."""
    ensure_output_dir()
    if output_path is None:
        output_path = OUTPUT_DIR / 'scenario_comparison.png'
    
    fig, ax = plt.subplots(figsize=(10, 4))
    
    names = ['Low', 'Base', 'High']
    values = [
        scenarios['low']['tam_annual_cr'],
        scenarios['base']['tam_annual_cr'],
        scenarios['high']['tam_annual_cr'],
    ]
    colors = ['#e74c3c', '#2c3e50', '#2ecc71']
    
    bars = ax.barh(names, values, color=colors, alpha=0.85, height=0.5)
    
    for bar, val in zip(bars, values):
        usd = val * 1e7 / (95.47 * 1e9)
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                f'Rs {val:,.0f} Cr (~${usd:.1f}B)',
                va='center', fontsize=10)
    
    ax.set_xlabel('TAM (INR Crore)', fontsize=11)
    ax.set_title('TAM Scenario Analysis: Low / Base / High', fontsize=13, fontweight='bold')
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.set_xlim(0, max(values) * 1.35)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def plot_quarterly_gov_trend(quarterly_shares_df, output_path=None):
    """Plot quarterly GOV trend for Blinkit and Instamart."""
    ensure_output_dir()
    if output_path is None:
        output_path = OUTPUT_DIR / 'quarterly_gov_trend.png'
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    quarters = quarterly_shares_df['quarter']
    x = np.arange(len(quarters))
    
    ax.plot(x, quarterly_shares_df['blinkit_gov_cr'], 'o-', color='#e74c3c',
            linewidth=2, markersize=6, label='Blinkit GOV')
    ax.plot(x, quarterly_shares_df['instamart_gov_cr'], 's-', color='#f39c12',
            linewidth=2, markersize=6, label='Instamart GOV')
    
    ax.set_xticks(x)
    ax.set_xticklabels(quarters, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel('GOV (INR Crore)', fontsize=11)
    ax.set_title('Quarterly GOV Trend: Blinkit vs Instamart', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def generate_all_charts(tornado_data, base_tam_cr, shares_data, scenarios, quarterly_df):
    """Generate all charts and return paths."""
    paths = {}
    paths['tornado'] = str(plot_tornado(tornado_data, base_tam_cr))
    paths['market_share'] = str(plot_market_share_bars(shares_data))
    paths['scenarios'] = str(plot_scenario_comparison(scenarios))
    paths['gov_trend'] = str(plot_quarterly_gov_trend(quarterly_df))
    return paths
