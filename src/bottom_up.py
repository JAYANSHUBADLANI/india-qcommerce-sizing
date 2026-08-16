"""Bottom-up TAM build for Indian quick commerce.

Starting from urban population, narrows to the addressable segment
step by step. Every narrowing ratio is sourced from real data or
flagged as an assumption with a stated range.

This module does NOT import from top_down.py. The two estimates
are built independently and reconciled afterward.
"""

from src.config import Assumptions


def compute_bottom_up_tam(config: Assumptions = None, overrides: dict = None):
    """Compute the bottom-up TAM.
    
    Args:
        config: Assumptions instance. If None, loads default.
        overrides: Optional dict of dotted_key -> value to override
                   specific assumptions (used by sensitivity analysis).
    
    Returns:
        dict with keys:
            'tam_annual_cr': Total TAM in INR crore per year
            'tam_annual_usd_b': Total TAM in USD billion
            'funnel': list of dicts, each with 'step', 'value', 'unit', 'ratio', 'source_type'
            'tier1': dict with tier-1 specific subtotals
            'tier2': dict with tier-2 specific subtotals
    """
    if config is None:
        config = Assumptions()
    
    def val(key):
        if overrides and key in overrides:
            return overrides[key]
        return config.get(key)
    
    funnel = []
    
    # Step 1: Total urban households
    urban_hh = val('demographics.urban_households')
    funnel.append({
        'step': 'Total urban households (India, 2026)',
        'value': urban_hh,
        'unit': 'households',
        'ratio': None,
        'source_type': 'derived from official projection'
    })
    
    # Step 2: Geographic filter, tier-1
    tier1_hh = val('demographics.tier1_households')
    funnel.append({
        'step': 'Tier-1 metro households (top 8 cities)',
        'value': tier1_hh,
        'unit': 'households',
        'ratio': tier1_hh / urban_hh,
        'source_type': 'derived from official projection'
    })
    
    # Step 3: Geographic filter, tier-2
    tier2_hh = val('demographics.tier2_households')
    funnel.append({
        'step': 'Tier-2 city households (next ~70 cities)',
        'value': tier2_hh,
        'unit': 'households',
        'ratio': tier2_hh / urban_hh,
        'source_type': 'derived from official projection'
    })
    
    # Step 4: Income filter
    tier1_income_ratio = val('addressable_population.tier1_income_filter')
    tier2_income_ratio = val('addressable_population.tier2_income_filter')
    tier1_income_hh = tier1_hh * tier1_income_ratio
    tier2_income_hh = tier2_hh * tier2_income_ratio
    total_income_hh = tier1_income_hh + tier2_income_hh
    funnel.append({
        'step': f'Income-qualifying households (>{"Rs 30k/month"})',
        'value': total_income_hh,
        'unit': 'households',
        'ratio': total_income_hh / (tier1_hh + tier2_hh),
        'source_type': 'assumption (PRICE ICE 360, HCES 2022-23)'
    })
    
    # Step 5: Digital readiness filter
    digital_ratio = val('addressable_population.digital_readiness_filter')
    tier1_digital_hh = tier1_income_hh * digital_ratio
    tier2_digital_hh = tier2_income_hh * digital_ratio
    total_digital_hh = tier1_digital_hh + tier2_digital_hh
    funnel.append({
        'step': 'Digitally ready households (smartphone + UPI + online shopping)',
        'value': total_digital_hh,
        'unit': 'households',
        'ratio': digital_ratio,
        'source_type': 'assumption (TRAI, MoSPI PLFS, Bain)'
    })
    
    # Step 6: Adoption rate
    tier1_adopt = val('addressable_population.tier1_adoption_rate')
    tier2_adopt = val('addressable_population.tier2_adoption_rate')
    tier1_adopting_hh = tier1_digital_hh * tier1_adopt
    tier2_adopting_hh = tier2_digital_hh * tier2_adopt
    total_adopting_hh = tier1_adopting_hh + tier2_adopting_hh
    funnel.append({
        'step': 'Adopting households (order at least once per month)',
        'value': total_adopting_hh,
        'unit': 'households',
        'ratio': total_adopting_hh / total_digital_hh,
        'source_type': 'ASSUMPTION (key sensitivity driver)'
    })
    
    # Step 7: Monthly order volume
    tier1_freq = val('order_economics.tier1_orders_per_hh_per_month')
    tier2_freq = val('order_economics.tier2_orders_per_hh_per_month')
    tier1_monthly_orders = tier1_adopting_hh * tier1_freq
    tier2_monthly_orders = tier2_adopting_hh * tier2_freq
    total_monthly_orders = tier1_monthly_orders + tier2_monthly_orders
    funnel.append({
        'step': 'Monthly orders (adopting HH x frequency)',
        'value': total_monthly_orders,
        'unit': 'orders/month',
        'ratio': None,
        'source_type': 'ASSUMPTION (key sensitivity driver)'
    })
    
    # Step 8: Monthly GOV
    tier1_aov = val('order_economics.tier1_aov')
    tier2_aov = val('order_economics.tier2_aov')
    tier1_monthly_gov = tier1_monthly_orders * tier1_aov
    tier2_monthly_gov = tier2_monthly_orders * tier2_aov
    total_monthly_gov = tier1_monthly_gov + tier2_monthly_gov
    
    # Step 9: Annual GOV (TAM)
    tier1_annual_gov = tier1_monthly_gov * 12
    tier2_annual_gov = tier2_monthly_gov * 12
    total_annual_gov = total_monthly_gov * 12
    total_annual_gov_cr = total_annual_gov / 1e7  # Convert to crore
    
    usd_rate = val('exchange_rates.usd_inr_fy26')
    total_annual_usd_b = (total_annual_gov_cr * 1e7) / (usd_rate * 1e9)
    
    funnel.append({
        'step': 'Annual GOV (TAM)',
        'value': total_annual_gov_cr,
        'unit': 'INR crore/year',
        'ratio': None,
        'source_type': 'calculated'
    })
    
    tier1_annual_gov_cr = tier1_annual_gov / 1e7
    tier2_annual_gov_cr = tier2_annual_gov / 1e7
    
    return {
        'tam_annual_cr': total_annual_gov_cr,
        'tam_annual_usd_b': total_annual_usd_b,
        'funnel': funnel,
        'tier1': {
            'households': tier1_hh,
            'income_qualified': tier1_income_hh,
            'digitally_ready': tier1_digital_hh,
            'adopting': tier1_adopting_hh,
            'monthly_orders': tier1_monthly_orders,
            'annual_gov_cr': tier1_annual_gov_cr,
            'aov': tier1_aov,
            'frequency': tier1_freq,
        },
        'tier2': {
            'households': tier2_hh,
            'income_qualified': tier2_income_hh,
            'digitally_ready': tier2_digital_hh,
            'adopting': tier2_adopting_hh,
            'monthly_orders': tier2_monthly_orders,
            'annual_gov_cr': tier2_annual_gov_cr,
            'aov': tier2_aov,
            'frequency': tier2_freq,
        },
        'monthly_orders_total': total_monthly_orders,
        'annual_orders_total': total_monthly_orders * 12,
    }


def format_funnel(result):
    """Format the bottom-up funnel as a readable string."""
    lines = []
    lines.append('BOTTOM-UP TAM FUNNEL')
    lines.append('=' * 70)
    for step in result['funnel']:
        val = step['value']
        if val > 1e6:
            val_str = f"{val/1e6:.1f}M"
        elif val > 1e3:
            val_str = f"{val/1e3:.1f}K"
        else:
            val_str = f"{val:.1f}"
        
        ratio_str = f" (ratio: {step['ratio']:.1%})" if step['ratio'] else ""
        source_str = f" [{step['source_type']}]" if step['source_type'] else ""
        lines.append(f"  {step['step']}: {val_str} {step['unit']}{ratio_str}{source_str}")
    
    lines.append('')
    lines.append(f"  TOTAL TAM: Rs {result['tam_annual_cr']:,.0f} Cr (~${result['tam_annual_usd_b']:.1f}B)")
    lines.append(f"    Tier-1 contribution: Rs {result['tier1']['annual_gov_cr']:,.0f} Cr")
    lines.append(f"    Tier-2 contribution: Rs {result['tier2']['annual_gov_cr']:,.0f} Cr")
    return '\n'.join(lines)


if __name__ == '__main__':
    result = compute_bottom_up_tam()
    print(format_funnel(result))
