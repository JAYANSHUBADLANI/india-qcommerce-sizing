#!/usr/bin/env python3
"""Run the complete Indian Quick Commerce market sizing model.

This script loads assumptions from assumptions.yaml, runs the bottom-up TAM,
top-down triangulation, sensitivity analysis, competitive analysis, and
SAM/SOM calculations. All outputs go to the output/ directory.

Usage:
    python run_model.py
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import Assumptions
from src.bottom_up import compute_bottom_up_tam, format_funnel
from src.top_down import compute_top_down, format_top_down
from src.sensitivity import compute_tornado, compute_scenarios, format_tornado, format_scenarios
from src.competitive import compute_quarterly_shares, compute_fy_shares, format_shares
from src.sam_som import compute_sam_som, format_sam_som
from src.charts import generate_all_charts


def main():
    print('Indian Quick Commerce Market Sizing Model')
    print('=' * 60)
    print()
    
    # Load configuration
    config = Assumptions()
    print(f"Reference period: {config.get('reference_period_label')}")
    print(f"Exchange rates: Rs {config.get('exchange_rates.usd_inr_fy26')} = $1 (FY26), "
          f"Rs {config.get('exchange_rates.usd_inr_cy2025')} = $1 (CY2025 cross-checks)")
    print()
    
    # 1. Bottom-up TAM
    print('\n' + '=' * 60)
    print('SECTION 1: BOTTOM-UP TAM BUILD')
    print('=' * 60)
    bottom_up = compute_bottom_up_tam(config)
    print(format_funnel(bottom_up))
    
    # 2. Top-down triangulation
    print('\n' + '=' * 60)
    print('SECTION 2: TOP-DOWN TRIANGULATION')
    print('=' * 60)
    top_down = compute_top_down(config)
    print(format_top_down(top_down))
    
    # 3. Reconciliation
    print('\n' + '=' * 60)
    print('SECTION 3: RECONCILIATION')
    print('=' * 60)
    bu_tam = bottom_up['tam_annual_cr']
    td_tam = top_down['implied_total_gov_cr']
    gap = bu_tam - td_tam
    gap_pct = gap / td_tam * 100
    print(f"\n  Bottom-up TAM:  Rs {bu_tam:,.0f} Cr (~${bottom_up['tam_annual_usd_b']:.1f}B)")
    print(f"  Top-down TAM:   Rs {td_tam:,.0f} Cr (~${top_down['implied_total_usd_b']:.1f}B)")
    print(f"  Gap:            Rs {abs(gap):,.0f} Cr ({gap_pct:+.1f}%)")
    print()
    if gap > 0:
        print('  The bottom-up estimate is HIGHER than the top-down.')
        print('  Most likely reasons:')
        print('    1. The adoption rate assumption may be optimistic for current penetration')
        print('    2. Order frequency per household may overstate actual usage patterns')
        print('    3. The tier-2 component may be overestimated relative to current reality')
        print('    4. The bottom-up captures addressable potential; the top-down reflects current scale')
    else:
        print('  The bottom-up estimate is LOWER than the top-down.')
        print('  Most likely reasons:')
        print('    1. The income/digital filters may be too restrictive')
        print('    2. The Big-3 market share assumption may be too high (denominator too small)')
        print('    3. Non-household orders (offices, hostels, PGs) are not captured in bottom-up')
        print('    4. The Zepto GOV estimation from U-DRHP may overstate actual GOV')
    
    # 4. Sensitivity analysis
    print('\n' + '=' * 60)
    print('SECTION 4: SENSITIVITY AND SCENARIO ANALYSIS')
    print('=' * 60)
    tornado = compute_tornado(config)
    scenarios = compute_scenarios(config)
    print(format_tornado(tornado, bu_tam))
    print()
    print(format_scenarios(scenarios))
    
    # 5. Competitive analysis
    print('\n' + '=' * 60)
    print('SECTION 5: COMPETITIVE MARKET SHARE')
    print('=' * 60)
    quarterly_shares = compute_quarterly_shares(config)
    fy_shares = compute_fy_shares(config)
    print(format_shares(fy_shares))
    
    # 6. SAM/SOM
    print('\n' + '=' * 60)
    print('SECTION 6: SAM / SOM FOR TIER-2 ENTRY')
    print('=' * 60)
    sam_som = compute_sam_som(config)
    print(format_sam_som(sam_som))
    
    # 7. Generate charts
    print('\n' + '=' * 60)
    print('SECTION 7: GENERATING CHARTS')
    print('=' * 60)
    chart_paths = generate_all_charts(
        tornado_data=tornado,
        base_tam_cr=bu_tam,
        shares_data=fy_shares,
        scenarios=scenarios,
        quarterly_df=quarterly_shares,
    )
    for name, path in chart_paths.items():
        print(f"  Generated: {name} -> {path}")
    
    # 8. Save numerical results to JSON for use by memo/README
    output_dir = Path(__file__).parent / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_summary = {
        'reference_period': config.get('reference_period_label'),
        'bottom_up_tam_cr': round(bu_tam),
        'bottom_up_tam_usd_b': round(bottom_up['tam_annual_usd_b'], 1),
        'top_down_tam_cr': round(td_tam),
        'top_down_tam_usd_b': round(top_down['implied_total_usd_b'], 1),
        'reconciliation_gap_pct': round(gap_pct, 1),
        'scenario_low_cr': round(scenarios['low']['tam_annual_cr']),
        'scenario_base_cr': round(scenarios['base']['tam_annual_cr']),
        'scenario_high_cr': round(scenarios['high']['tam_annual_cr']),
        'scenario_low_usd_b': round(scenarios['low']['tam_annual_usd_b'], 1),
        'scenario_high_usd_b': round(scenarios['high']['tam_annual_usd_b'], 1),
        'sam_tier2_cr': round(sam_som['sam_tier2_annual_cr']),
        'sam_tier2_usd_b': round(sam_som['sam_tier2_annual_usd_b'], 1),
        'som_year2_cr': round(sam_som['som_annual_cr']),
        'som_year2_usd_b': round(sam_som['som_annual_usd_b'], 2),
        'meets_breakeven': sam_som['meets_breakeven'],
        'min_sam_for_breakeven_cr': round(sam_som['min_sam_for_breakeven_cr']),
    }
    
    with open(output_dir / 'results_summary.json', 'w') as f:
        json.dump(results_summary, f, indent=2)
    print(f"\n  Saved results summary to output/results_summary.json")
    
    print('\n' + '=' * 60)
    print('MODEL RUN COMPLETE')
    print('=' * 60)
    
    return results_summary


if __name__ == '__main__':
    main()
