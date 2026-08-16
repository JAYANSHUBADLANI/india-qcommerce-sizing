"""Top-down market size triangulation from disclosed company figures.

Uses actual filed GMV/GOV/NOV, order volumes, and dark store counts
from Blinkit, Instamart, and Zepto to estimate total market size.

This module does NOT import from bottom_up.py.
The two estimates are built independently.

IMPORTANT NOTE ON BLINKIT FY26 DATA:
Blinkit transitioned from a marketplace (3P) model to an inventory-led (1P)
model during FY26. As a result:
- Q1 FY26: Both GOV (Rs 11,821 Cr) and NOV (Rs 9,230 Cr) were reported
- Q2-Q4 FY26: Only NOV was reported (GOV not explicitly cited)
- NOV is smaller than GOV because it excludes taxes, delivery fees, and
  packaging charges that GOV includes
- Instamart and Zepto still report GOV, making direct comparison imperfect
- The Q1 FY26 GOV/NOV ratio (~1.28) provides a conversion factor

This discrepancy is flagged prominently in all outputs.
"""

import pandas as pd
from pathlib import Path
from src.config import Assumptions


def load_company_data(data_dir=None):
    """Load all company quarterly/annual CSV files."""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / 'data'

    blinkit = pd.read_csv(data_dir / 'blinkit_quarterly.csv')
    instamart = pd.read_csv(data_dir / 'instamart_quarterly.csv')
    zepto = pd.read_csv(data_dir / 'zepto_annual.csv')

    return blinkit, instamart, zepto


def get_blinkit_order_value(row):
    """Get the best available order value metric for a Blinkit quarter.

    Returns (value_cr, metric_type) where metric_type is 'GOV' or 'NOV'.
    Prefers GOV when available; falls back to NOV.
    """
    gov = row.get('gov_cr')
    nov = row.get('nov_cr')

    if pd.notna(gov) and gov > 0:
        return gov, 'GOV'
    elif pd.notna(nov) and nov > 0:
        return nov, 'NOV'
    else:
        return None, None


def estimate_zepto_gov(zepto_df, config: Assumptions):
    """Estimate Zepto's GOV from its U-DRHP disclosed metrics.

    Zepto reports revenue (not GOV) in its U-DRHP. We estimate GOV using:
    GOV = orders_per_store_per_day x dark_stores x 365 x AOV

    This is an explicit estimation, not a filed GOV figure.
    """
    results = []
    for _, row in zepto_df.iterrows():
        fy = row['fiscal_year']
        stores = row['dark_stores']
        opd = row.get('orders_per_store_per_day')
        aov = row.get('aov_inr')
        revenue = row['revenue_cr']

        if pd.notna(opd) and pd.notna(aov) and pd.notna(stores):
            annual_orders = opd * stores * 365
            estimated_gov_cr = (annual_orders * aov) / 1e7
            estimation_method = 'orders_per_store x stores x 365 x AOV'
        else:
            estimated_gov_cr = None
            estimation_method = 'not estimable from available data'
            annual_orders = None

        results.append({
            'fiscal_year': fy,
            'dark_stores': stores,
            'revenue_cr': revenue,
            'estimated_gov_cr': estimated_gov_cr,
            'estimated_annual_orders_m': annual_orders / 1e6 if annual_orders else None,
            'estimation_method': estimation_method,
            'aov_inr': aov,
        })

    return pd.DataFrame(results)


def compute_top_down(config: Assumptions = None, overrides: dict = None):
    """Compute the top-down market size triangulation.

    Approach:
    1. Sum disclosed GOV/NOV for Blinkit for FY26 (handling the 1P transition)
    2. Sum disclosed GOV for Instamart for FY26
    3. Estimate Zepto GOV from U-DRHP metrics
    4. Sum Big-3 order value
    5. Divide by estimated Big-3 market share to get implied total
    6. Cross-check against third-party estimates

    Returns:
        dict with total market estimate and breakdown
    """
    if config is None:
        config = Assumptions()

    def val(key):
        if overrides and key in overrides:
            return overrides[key]
        return config.get(key)

    blinkit_df, instamart_df, zepto_df = load_company_data()

    # --- BLINKIT FY26 ---
    # Due to the 1P model transition, Blinkit reports NOV (not GOV) from Q2 FY26.
    # Strategy: Use NOV where GOV is unavailable, then estimate total GOV using
    # the Q1 FY26 GOV/NOV ratio (~1.28) as a conversion factor.

    blinkit_fy26_quarters = blinkit_df[blinkit_df['quarter'].str.contains('FY26')]

    if len(blinkit_fy26_quarters) >= 4:
        # We have all 4 FY26 quarters
        # Q1 FY26 has GOV = 11821, NOV = 9230; ratio = 1.281
        q1_row = blinkit_fy26_quarters[blinkit_fy26_quarters['quarter'] == 'Q1 FY26'].iloc[0]
        gov_nov_ratio = q1_row['gov_cr'] / q1_row['nov_cr']  # ~1.281

        total_nov = 0
        total_gov_direct = 0
        quarters_with_gov = 0

        for _, row in blinkit_fy26_quarters.iterrows():
            gov = row.get('gov_cr')
            nov = row.get('nov_cr')
            if pd.notna(gov) and gov > 0:
                total_gov_direct += gov
                quarters_with_gov += 1
            if pd.notna(nov) and nov > 0:
                total_nov += nov

        # Sum NOV across all 4 quarters, then convert to estimated GOV
        # Q1: GOV = 11,821 (filed), Q2-Q4: NOV only
        q2_q4_nov = total_nov - q1_row['nov_cr']
        estimated_q2_q4_gov = q2_q4_nov * gov_nov_ratio
        blinkit_fy26_gov = q1_row['gov_cr'] + estimated_q2_q4_gov
        blinkit_fy26_nov = total_nov

        blinkit_gov_source = (
            f'Q1 FY26 GOV filed (Rs 11,821 Cr). Q2-Q4 FY26 GOV estimated from '
            f'NOV using Q1 GOV/NOV ratio of {gov_nov_ratio:.3f}. '
            f'Total FY26 NOV (filed): Rs {total_nov:,.0f} Cr.'
        )
        blinkit_data_flag = (
            'IMPORTANT: Blinkit transitioned to a 1P (inventory-led) model during FY26. '
            'GOV was only explicitly reported for Q1 FY26 (Rs 11,821 Cr). '
            'For Q2-Q4 FY26, only NOV was reported. '
            f'FY26 GOV is estimated by converting NOV using the Q1 GOV/NOV ratio ({gov_nov_ratio:.3f}). '
            'This makes the Blinkit figure not directly comparable to Instamart GOV.'
        )

        # Orders
        blinkit_fy26_orders = blinkit_fy26_quarters['orders_m'].sum()
        # Handle NaN in orders (Q2 FY26 has no explicit order count)
        if pd.isna(blinkit_fy26_orders):
            # FY26 total orders = 915.6M from the annual filing
            blinkit_fy26_orders = 915.6
            blinkit_gov_source += ' FY26 total orders: 915.6M (annual filing).'

    elif len(blinkit_fy26_quarters) > 0:
        # Partial FY26 data
        available_values = []
        for _, row in blinkit_fy26_quarters.iterrows():
            v, _ = get_blinkit_order_value(row)
            if v:
                available_values.append(v)
        available_total = sum(available_values)
        quarters_available = len(available_values)
        blinkit_fy26_gov = available_total * (4 / quarters_available)
        blinkit_fy26_nov = blinkit_fy26_gov  # approximate
        blinkit_fy26_orders = blinkit_fy26_quarters['orders_m'].dropna().sum()
        blinkit_fy26_orders = blinkit_fy26_orders * (4 / quarters_available)
        blinkit_gov_source = f'Extrapolated from {quarters_available} available FY26 quarter(s)'
        blinkit_data_flag = f'WARNING: Only {quarters_available} of 4 FY26 quarters available.'
    else:
        # No FY26 data at all: use Q4 FY25 run-rate
        q4_fy25 = blinkit_df[blinkit_df['quarter'] == 'Q4 FY25'].iloc[0]
        blinkit_fy26_gov = q4_fy25['gov_cr'] * 4
        blinkit_fy26_nov = blinkit_fy26_gov
        blinkit_fy26_orders = q4_fy25['orders_m'] * 4
        blinkit_gov_source = 'Q4 FY25 run-rate annualized (FY26 data not in dataset)'
        blinkit_data_flag = (
            'WARNING: Blinkit FY26 filings not in dataset. '
            'Using Q4 FY25 GOV (Rs 9,421 Cr) annualized. '
            'This likely UNDERSTATES actual FY26 given ~130% YoY growth.'
        )

    # --- INSTAMART FY26 ---
    instamart_fy26 = instamart_df[
        instamart_df['quarter'].isin(['Q1 FY26', 'Q2 FY26', 'Q3 FY26', 'Q4 FY26'])
    ]
    instamart_fy26_gov = instamart_fy26['gov_cr'].sum()
    instamart_fy26_orders = instamart_fy26['orders_m'].sum()
    instamart_gov_source = 'Sum of Q1-Q4 FY26 shareholder letters (GOV)'

    # --- ZEPTO FY26 ---
    zepto_estimated = estimate_zepto_gov(zepto_df, config)
    zepto_fy26 = zepto_estimated[zepto_estimated['fiscal_year'] == 'FY26'].iloc[0]
    zepto_fy26_gov = zepto_fy26['estimated_gov_cr']
    zepto_fy26_orders = zepto_fy26['estimated_annual_orders_m']
    zepto_gov_source = (
        f"Estimated from U-DRHP: {int(zepto_fy26['dark_stores'])} stores x "
        f"{zepto_df[zepto_df['fiscal_year']=='FY26'].iloc[0]['orders_per_store_per_day']} orders/store/day x "
        f"365 days x Rs {zepto_fy26['aov_inr']} AOV. "
        f"NOT a directly filed GOV figure."
    )

    # --- BIG-3 COMBINED ---
    big3_gov = blinkit_fy26_gov + instamart_fy26_gov + (zepto_fy26_gov if zepto_fy26_gov else 0)
    big3_orders = blinkit_fy26_orders + instamart_fy26_orders + (zepto_fy26_orders if zepto_fy26_orders else 0)

    # Implied total market
    big3_share = val('top_down.big3_combined_market_share')
    implied_total_gov_cr = big3_gov / big3_share

    usd_rate = val('exchange_rates.usd_inr_fy26')
    implied_total_usd_b = (implied_total_gov_cr * 1e7) / (usd_rate * 1e9)

    # Cross-checks against third-party estimates
    usd_rate_cy25 = val('exchange_rates.usd_inr_cy2025')
    cross_checks = [
        {
            'source': 'Redseer (2025 estimate)',
            'value_usd_b': 7.0,
            'value_inr_cr': 7.0 * 1e9 * usd_rate_cy25 / 1e7,
            'rate_used': usd_rate_cy25,
            'rate_note': 'CY2025 average rate (Rs 83/$1)',
        },
        {
            'source': 'Goldman Sachs (FY25 estimate)',
            'value_usd_b': 5.75,
            'value_inr_cr': 5.75 * 1e9 * usd_rate_cy25 / 1e7,
            'rate_used': usd_rate_cy25,
            'rate_note': 'CY2025 average rate (Rs 83/$1)',
        },
        {
            'source': 'Bernstein (end-2025 estimate)',
            'value_usd_b': 11.5,
            'value_inr_cr': 95500,  # Originally cited in INR
            'rate_used': None,
            'rate_note': 'Originally reported in INR (Rs 95,500 Cr)',
        },
        {
            'source': 'JM Financial (2024/25 estimate, midpoint)',
            'value_usd_b': 7.75,
            'value_inr_cr': 7.75 * 1e9 * usd_rate_cy25 / 1e7,
            'rate_used': usd_rate_cy25,
            'rate_note': 'CY2025 average rate (Rs 83/$1)',
        },
    ]

    return {
        'implied_total_gov_cr': implied_total_gov_cr,
        'implied_total_usd_b': implied_total_usd_b,
        'big3_gov_cr': big3_gov,
        'big3_share_assumed': big3_share,
        'blinkit': {
            'fy26_gov_cr': blinkit_fy26_gov,
            'fy26_nov_cr': blinkit_fy26_nov if 'blinkit_fy26_nov' in dir() else blinkit_fy26_gov,
            'fy26_orders_m': blinkit_fy26_orders,
            'source': blinkit_gov_source,
            'data_flag': blinkit_data_flag,
        },
        'instamart': {
            'fy26_gov_cr': instamart_fy26_gov,
            'fy26_orders_m': instamart_fy26_orders,
            'source': instamart_gov_source,
        },
        'zepto': {
            'fy26_estimated_gov_cr': zepto_fy26_gov,
            'fy26_estimated_orders_m': zepto_fy26_orders,
            'source': zepto_gov_source,
            'estimation_method': zepto_fy26['estimation_method'],
        },
        'cross_checks': cross_checks,
        'implied_annual_orders_m': big3_orders / big3_share,
    }


def format_top_down(result):
    """Format the top-down results as a readable string."""
    lines = []
    lines.append('TOP-DOWN MARKET SIZE TRIANGULATION')
    lines.append('=' * 70)
    lines.append('')
    lines.append('Disclosed / Estimated FY26 GOV by Player:')
    lines.append(f"  Blinkit:   Rs {result['blinkit']['fy26_gov_cr']:>10,.0f} Cr")
    lines.append(f"             [{result['blinkit']['source']}]")
    if result['blinkit'].get('data_flag'):
        lines.append(f"             *** {result['blinkit']['data_flag']}")
    lines.append(f"  Instamart: Rs {result['instamart']['fy26_gov_cr']:>10,.0f} Cr  [{result['instamart']['source']}]")
    lines.append(f"  Zepto:     Rs {result['zepto']['fy26_estimated_gov_cr']:>10,.0f} Cr  [{result['zepto']['estimation_method']}]")
    lines.append(f"  ---")
    lines.append(f"  Big-3 Total: Rs {result['big3_gov_cr']:>10,.0f} Cr")
    lines.append('')
    lines.append(f"  Assumed Big-3 market share: {result['big3_share_assumed']:.0%}")
    lines.append(f"  Implied total market: Rs {result['implied_total_gov_cr']:,.0f} Cr (~${result['implied_total_usd_b']:.1f}B)")
    lines.append('')
    lines.append('Cross-Checks (third-party estimates, not used in calculation):')
    for cc in result['cross_checks']:
        lines.append(f"  {cc['source']}: ${cc['value_usd_b']:.1f}B / Rs {cc['value_inr_cr']:,.0f} Cr [{cc['rate_note']}]")

    return '\n'.join(lines)


if __name__ == '__main__':
    result = compute_top_down()
    print(format_top_down(result))
