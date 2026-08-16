"""Competitive market share and positioning analysis.

Computes quarterly market shares from disclosed figures
and summarizes competitive positioning.

Note: Blinkit's shift to 1P reporting in FY26 means GOV is not available
for Q2-Q4 FY26. For the quarterly comparison, we use GOV where available
(FY24-FY25 quarters) and note the metric gap for FY26 quarters.
"""

import pandas as pd
from pathlib import Path
from src.config import Assumptions
from src.top_down import load_company_data, estimate_zepto_gov


def compute_quarterly_shares(config: Assumptions = None):
    """Compute quarterly GOV-based market shares where data overlaps.

    Returns a DataFrame with quarterly shares for Blinkit and Instamart.
    Only includes quarters where both players have comparable GOV data.
    FY26 quarters are excluded because Blinkit shifted to NOV reporting.
    """
    if config is None:
        config = Assumptions()

    blinkit_df, instamart_df, zepto_df = load_company_data()

    # Find overlapping quarters between Blinkit and Instamart
    # Only use quarters where Blinkit has GOV (pre-FY26 or Q1 FY26)
    blinkit_with_gov = blinkit_df[blinkit_df['gov_cr'].notna() & (blinkit_df['gov_cr'] > 0)]
    blinkit_quarters = set(blinkit_with_gov['quarter'])
    instamart_quarters = set(instamart_df['quarter'])
    common_quarters = sorted(blinkit_quarters & instamart_quarters)

    rows = []
    for q in common_quarters:
        b_row = blinkit_df[blinkit_df['quarter'] == q].iloc[0]
        i_row = instamart_df[instamart_df['quarter'] == q].iloc[0]

        b_gov = b_row['gov_cr']
        i_gov = i_row['gov_cr']

        b_orders = b_row['orders_m'] if pd.notna(b_row['orders_m']) else None
        i_orders = i_row['orders_m'] if pd.notna(i_row['orders_m']) else None

        b_aov = b_row['aov_inr']
        i_aov = i_row['aov_inr']

        b_stores = b_row['dark_stores']
        i_stores = i_row['dark_stores']

        two_player_total = b_gov + i_gov

        rows.append({
            'quarter': q,
            'blinkit_gov_cr': b_gov,
            'instamart_gov_cr': i_gov,
            'blinkit_share_of_two': b_gov / two_player_total if two_player_total > 0 else 0,
            'instamart_share_of_two': i_gov / two_player_total if two_player_total > 0 else 0,
            'blinkit_orders_m': b_orders,
            'instamart_orders_m': i_orders,
            'blinkit_aov': b_aov,
            'instamart_aov': i_aov,
            'blinkit_stores': b_stores,
            'instamart_stores': i_stores,
        })

    return pd.DataFrame(rows)


def compute_fy_shares(config: Assumptions = None):
    """Compute annual market shares for FY25 (where all three have comparable data).

    FY25 is the best period for share comparison because:
    - Blinkit still reported GOV (not yet shifted to 1P/NOV)
    - Instamart reported GOV throughout
    - Zepto FY25 can be estimated from U-DRHP
    """
    if config is None:
        config = Assumptions()

    blinkit_df, instamart_df, zepto_df = load_company_data()
    zepto_est = estimate_zepto_gov(zepto_df, config)

    results = {}

    # FY25: All three players have comparable GOV data
    blinkit_fy25 = blinkit_df[blinkit_df['quarter'].str.contains('FY25')]
    blinkit_fy25_with_gov = blinkit_fy25[blinkit_fy25['gov_cr'].notna()]

    if len(blinkit_fy25_with_gov) == 4:
        b_fy25_gov = blinkit_fy25_with_gov['gov_cr'].sum()
        b_fy25_orders = blinkit_fy25['orders_m'].sum()
    else:
        b_fy25_gov = None
        b_fy25_orders = None

    # Instamart FY25
    instamart_fy25 = instamart_df[instamart_df['quarter'].str.contains('FY25')]
    i_fy25_gov = instamart_fy25['gov_cr'].sum() if len(instamart_fy25) == 4 else None
    i_fy25_orders = instamart_fy25['orders_m'].sum() if len(instamart_fy25) == 4 else None

    # Zepto FY25 (estimated)
    z_fy25 = zepto_est[zepto_est['fiscal_year'] == 'FY25']
    z_fy25_gov = z_fy25['estimated_gov_cr'].values[0] if len(z_fy25) > 0 else None

    if b_fy25_gov and i_fy25_gov:
        total_known = b_fy25_gov + i_fy25_gov + (z_fy25_gov if z_fy25_gov else 0)
        results['FY25'] = {
            'blinkit_gov_cr': b_fy25_gov,
            'instamart_gov_cr': i_fy25_gov,
            'zepto_gov_cr': z_fy25_gov,
            'zepto_is_estimated': True,
            'big3_total_cr': total_known,
            'blinkit_share': b_fy25_gov / total_known if total_known else None,
            'instamart_share': i_fy25_gov / total_known if total_known else None,
            'zepto_share': z_fy25_gov / total_known if (z_fy25_gov and total_known) else None,
            'note': 'All GOV figures are on a comparable basis (pre-1P transition for Blinkit)',
        }

    return results


def get_positioning_comparison():
    """Return a static positioning comparison table.

    Uses the most recent disclosed data for each player.
    """
    return [
        {
            'player': 'Blinkit (Eternal)',
            'delivery_promise': '10-15 minutes',
            'city_coverage': '300+ cities (FY26)',
            'dark_stores': '2,243 (Q4 FY26); 2,443 (Q1 FY27)',
            'sku_depth': '~80,000 SKUs in Delhi-NCR; ~50,000 in other Tier-1; ~20,000 in Tier-2',
            'category_breadth': 'Grocery, electronics, beauty, toys, home appliances',
            'unit_economics': (
                'EBITDA positive from Q3 FY26 (+Rs 4 Cr); Q1 FY27: +Rs 102 Cr (+0.6% of NOV). '
                'Contribution margin 5.3% (Q1 FY27). Breakeven threshold Rs 7L GOV/store/day.'
            ),
            'key_advantage': 'Largest scale, deepest Delhi-NCR density, Zomato ecosystem cross-sell, 915.6M orders in FY26',
            'source': 'Eternal FY26 and Q1 FY27 Shareholder Letters',
        },
        {
            'player': 'Instamart (Swiggy)',
            'delivery_promise': '10-15 minutes',
            'city_coverage': '131 cities (Q1 FY27)',
            'dark_stores': '1,143 (Q4 FY26); 1,171 (Q1 FY27)',
            'sku_depth': '50,000+ SKUs in Megapod stores (10,000-12,000 sq ft)',
            'category_breadth': 'Grocery, daily essentials, beauty, Maxxsaver bulk packs',
            'unit_economics': (
                'Contribution margin -0.2% of GOV (Q1 FY27), reaching break-even in May 2026. '
                '412.2M orders in FY26.'
            ),
            'key_advantage': 'Swiggy food delivery base, Megapod format for larger baskets, strong in South/West India',
            'source': 'Swiggy Q1 FY27 Shareholder Letter, July 2026',
        },
        {
            'player': 'Zepto',
            'delivery_promise': '10 minutes',
            'city_coverage': '20+ metro clusters (FY26)',
            'dark_stores': '1,139 (FY26 end)',
            'sku_depth': 'Not disclosed in U-DRHP',
            'category_breadth': 'Grocery, Zepto Cafe (100k+ orders/day), electronics, beauty',
            'unit_economics': (
                'EBITDA loss Rs 78.75/order (FY26, improving from Rs 136.15 in FY25). '
                'Revenue Rs 22,624 Cr in FY26. Net loss Rs 5,905 Cr.'
            ),
            'key_advantage': 'Highest order density per store (2,140/day Q4 FY26), pure-play focus, 35% order market share (U-DRHP)',
            'source': 'Zepto U-DRHP filed June 8, 2026',
        },
    ]


def format_shares(shares_data):
    """Format market share data as readable text."""
    lines = []
    lines.append('COMPETITIVE MARKET SHARE ANALYSIS')
    lines.append('=' * 70)

    for fy, data in shares_data.items():
        lines.append(f'\n{fy} GOV-Based Market Share (Big-3 Only):')
        lines.append(f"  Blinkit:   Rs {data['blinkit_gov_cr']:>10,.0f} Cr  ({data['blinkit_share']:.1%})")
        lines.append(f"  Instamart: Rs {data['instamart_gov_cr']:>10,.0f} Cr  ({data['instamart_share']:.1%})")
        if data.get('zepto_gov_cr'):
            est_tag = ' [estimated from U-DRHP]' if data.get('zepto_is_estimated') else ''
            lines.append(f"  Zepto:     Rs {data['zepto_gov_cr']:>10,.0f} Cr  ({data['zepto_share']:.1%}){est_tag}")
        lines.append(f"  Total:     Rs {data['big3_total_cr']:>10,.0f} Cr")
        if data.get('note'):
            lines.append(f"  Note: {data['note']}")

    return '\n'.join(lines)


if __name__ == '__main__':
    shares = compute_fy_shares()
    print(format_shares(shares))
    print()
    print('POSITIONING COMPARISON')
    print('=' * 70)
    for p in get_positioning_comparison():
        print(f"\n{p['player']}:")
        for k, v in p.items():
            if k != 'player':
                print(f"  {k}: {v}")
