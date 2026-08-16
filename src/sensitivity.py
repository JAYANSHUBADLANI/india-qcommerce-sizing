"""Sensitivity and scenario analysis for the bottom-up TAM.

Identifies the assumptions the TAM is most sensitive to,
produces a tornado-style analysis and low/base/high scenarios.
"""

from src.config import Assumptions
from src.bottom_up import compute_bottom_up_tam


# The assumptions to test, in order of expected sensitivity
SENSITIVITY_PARAMS = [
    {
        'key': 'order_economics.tier1_orders_per_hh_per_month',
        'label': 'Tier-1 order frequency (orders/HH/month)',
    },
    {
        'key': 'addressable_population.tier1_adoption_rate',
        'label': 'Tier-1 adoption rate',
    },
    {
        'key': 'order_economics.tier1_aov',
        'label': 'Tier-1 average order value (INR)',
    },
    {
        'key': 'addressable_population.tier1_income_filter',
        'label': 'Tier-1 income filter (% of HH)',
    },
    {
        'key': 'addressable_population.digital_readiness_filter',
        'label': 'Digital readiness filter',
    },
    {
        'key': 'order_economics.tier2_orders_per_hh_per_month',
        'label': 'Tier-2 order frequency (orders/HH/month)',
    },
    {
        'key': 'addressable_population.tier2_adoption_rate',
        'label': 'Tier-2 adoption rate',
    },
    {
        'key': 'order_economics.tier2_aov',
        'label': 'Tier-2 average order value (INR)',
    },
]


def compute_tornado(config: Assumptions = None):
    """Compute tornado chart data: for each key assumption, show TAM at low and high.
    
    Returns:
        list of dicts sorted by impact (largest swing first), each with:
            'label', 'key', 'low_val', 'base_val', 'high_val',
            'tam_at_low_cr', 'tam_at_base_cr', 'tam_at_high_cr', 'swing_cr'
    """
    if config is None:
        config = Assumptions()
    
    base_result = compute_bottom_up_tam(config)
    base_tam = base_result['tam_annual_cr']
    
    tornado_data = []
    
    for param in SENSITIVITY_PARAMS:
        key = param['key']
        try:
            low_val, base_val, high_val = config.get_range(key)
        except KeyError:
            continue
        
        # If low == high == base, skip (no range defined)
        if low_val == high_val:
            continue
        
        # TAM at low end
        low_result = compute_bottom_up_tam(config, overrides={key: low_val})
        tam_at_low = low_result['tam_annual_cr']
        
        # TAM at high end
        high_result = compute_bottom_up_tam(config, overrides={key: high_val})
        tam_at_high = high_result['tam_annual_cr']
        
        swing = abs(tam_at_high - tam_at_low)
        
        tornado_data.append({
            'label': param['label'],
            'key': key,
            'low_val': low_val,
            'base_val': base_val,
            'high_val': high_val,
            'tam_at_low_cr': tam_at_low,
            'tam_at_base_cr': base_tam,
            'tam_at_high_cr': tam_at_high,
            'swing_cr': swing,
            'swing_pct': swing / base_tam * 100,
        })
    
    # Sort by swing (largest first)
    tornado_data.sort(key=lambda x: x['swing_cr'], reverse=True)
    return tornado_data


def compute_scenarios(config: Assumptions = None):
    """Compute low, base, and high scenarios.
    
    Each scenario sets ALL assumptions to their respective low/base/high values
    simultaneously (unlike tornado, which varies one at a time).
    
    Returns:
        dict with 'low', 'base', 'high', each containing:
            'tam_annual_cr', 'tam_annual_usd_b', 'narrative'
    """
    if config is None:
        config = Assumptions()
    
    # Base case: all defaults
    base = compute_bottom_up_tam(config)
    
    # Low scenario: all assumptions at their pessimistic end
    low_overrides = {}
    high_overrides = {}
    for param in SENSITIVITY_PARAMS:
        key = param['key']
        try:
            low_val, _, high_val = config.get_range(key)
            low_overrides[key] = low_val
            high_overrides[key] = high_val
        except KeyError:
            continue
    
    low = compute_bottom_up_tam(config, overrides=low_overrides)
    high = compute_bottom_up_tam(config, overrides=high_overrides)
    
    return {
        'low': {
            'tam_annual_cr': low['tam_annual_cr'],
            'tam_annual_usd_b': low['tam_annual_usd_b'],
            'narrative': (
                'Conservative: lower adoption rates, fewer orders per household, '
                'smaller addressable base. Reflects a scenario where quick commerce '
                'remains concentrated in top-tier metros with limited tier-2 traction.'
            ),
        },
        'base': {
            'tam_annual_cr': base['tam_annual_cr'],
            'tam_annual_usd_b': base['tam_annual_usd_b'],
            'narrative': 'Central estimates using midpoint assumptions.',
        },
        'high': {
            'tam_annual_cr': high['tam_annual_cr'],
            'tam_annual_usd_b': high['tam_annual_usd_b'],
            'narrative': (
                'Optimistic: higher adoption driven by category expansion '
                '(electronics, beauty, cafe), deeper tier-2 penetration, '
                'and increased order frequency as quick commerce becomes '
                'a primary grocery channel for urban households.'
            ),
        },
    }


def format_tornado(tornado_data, base_tam_cr):
    """Format tornado data as a readable table."""
    lines = []
    lines.append('SENSITIVITY ANALYSIS (TORNADO)')
    lines.append('=' * 90)
    lines.append(f'Base TAM: Rs {base_tam_cr:,.0f} Cr')
    lines.append('')
    lines.append(f'{"Assumption":<45} {"Low":>10} {"Base":>10} {"High":>10} {"Swing":>10} {"Swing%":>8}')
    lines.append('-' * 93)
    for row in tornado_data:
        lines.append(
            f"{row['label']:<45} "
            f"{row['tam_at_low_cr']:>10,.0f} "
            f"{row['tam_at_base_cr']:>10,.0f} "
            f"{row['tam_at_high_cr']:>10,.0f} "
            f"{row['swing_cr']:>10,.0f} "
            f"{row['swing_pct']:>7.1f}%"
        )
    return '\n'.join(lines)


def format_scenarios(scenarios):
    """Format scenario analysis as a readable string."""
    lines = []
    lines.append('SCENARIO ANALYSIS')
    lines.append('=' * 70)
    for name in ['low', 'base', 'high']:
        s = scenarios[name]
        lines.append(f"  {name.upper()}: Rs {s['tam_annual_cr']:,.0f} Cr (~${s['tam_annual_usd_b']:.1f}B)")
        lines.append(f"    {s['narrative']}")
        lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    config = Assumptions()
    base = compute_bottom_up_tam(config)
    tornado = compute_tornado(config)
    scenarios = compute_scenarios(config)
    print(format_tornado(tornado, base['tam_annual_cr']))
    print()
    print(format_scenarios(scenarios))
