"""SAM and SOM narrowing for the tier-2 city entry question.

Narrows the TAM to a serviceable market (tier-2 cities specifically),
then to a plausible obtainable share for a well-funded new entrant
over its first two years.
"""

from src.config import Assumptions
from src.bottom_up import compute_bottom_up_tam


def compute_sam_som(config: Assumptions = None, overrides: dict = None):
    """Compute SAM (Tier-2 only) and SOM (new entrant 2-year share).
    
    Returns:
        dict with SAM, SOM, and the strategic question answer components
    """
    if config is None:
        config = Assumptions()
    
    def val(key):
        if overrides and key in overrides:
            return overrides[key]
        return config.get(key)
    
    # Get the full TAM result for tier-2 breakdown
    tam = compute_bottom_up_tam(config, overrides=overrides)
    
    # SAM: Tier-2 portion of the TAM
    # This comes directly from the bottom-up build's tier-2 component
    tier2 = tam['tier2']
    sam_annual_cr = tier2['annual_gov_cr']
    
    usd_rate = val('exchange_rates.usd_inr_fy26')
    sam_annual_usd_b = (sam_annual_cr * 1e7) / (usd_rate * 1e9)
    
    # Further narrow SAM to the target cities for a new entrant
    total_tier2_cities = val('demographics.tier2_city_count')
    target_cities = val('sam_som.tier2_target_cities_for_entrant')
    city_coverage_ratio = target_cities / total_tier2_cities
    
    # Adjusted SAM for target cities (proportional to city count, rough)
    target_sam_cr = sam_annual_cr * city_coverage_ratio
    target_sam_usd_b = sam_annual_usd_b * city_coverage_ratio
    
    # SOM: New entrant's obtainable share in year 2
    entrant_share = val('sam_som.new_entrant_tier2_share_year2')
    som_annual_cr = target_sam_cr * entrant_share
    som_annual_usd_b = target_sam_usd_b * entrant_share
    
    # Unit economics check
    stores_y2 = val('sam_som.new_entrant_dark_stores_year2')
    breakeven_gov_per_day = val('sam_som.dark_store_breakeven_gov_per_day_lakh') * 1e5  # Convert to INR
    
    # Required daily GOV per store to break even
    required_annual_gov_for_breakeven = breakeven_gov_per_day * stores_y2 * 365
    required_annual_gov_for_breakeven_cr = required_annual_gov_for_breakeven / 1e7
    
    # Is the SOM sufficient to cover breakeven?
    som_daily_gov_per_store = (som_annual_cr * 1e7) / (stores_y2 * 365)
    som_daily_gov_per_store_lakh = som_daily_gov_per_store / 1e5
    meets_breakeven = som_daily_gov_per_store_lakh >= val('sam_som.dark_store_breakeven_gov_per_day_lakh')
    
    # The strategic question: what market size would justify entry?
    # Work backward: for breakeven, need X GOV per store per day
    # With Y stores and Z% share, implied SAM must be at least:
    min_sam_for_breakeven_cr = required_annual_gov_for_breakeven_cr / entrant_share
    min_sam_for_breakeven_usd_b = (min_sam_for_breakeven_cr * 1e7) / (usd_rate * 1e9)
    
    return {
        'tam_annual_cr': tam['tam_annual_cr'],
        'tam_annual_usd_b': tam['tam_annual_usd_b'],
        'sam_tier2_annual_cr': sam_annual_cr,
        'sam_tier2_annual_usd_b': sam_annual_usd_b,
        'target_cities': target_cities,
        'total_tier2_cities': total_tier2_cities,
        'target_sam_annual_cr': target_sam_cr,
        'target_sam_annual_usd_b': target_sam_usd_b,
        'entrant_share_assumed': entrant_share,
        'som_annual_cr': som_annual_cr,
        'som_annual_usd_b': som_annual_usd_b,
        'stores_year2': stores_y2,
        'som_daily_gov_per_store_lakh': som_daily_gov_per_store_lakh,
        'breakeven_threshold_lakh': val('sam_som.dark_store_breakeven_gov_per_day_lakh'),
        'meets_breakeven': meets_breakeven,
        'min_sam_for_breakeven_cr': min_sam_for_breakeven_cr,
        'min_sam_for_breakeven_usd_b': min_sam_for_breakeven_usd_b,
        'tier2_adopting_hh': tier2['adopting'],
        'tier2_aov': tier2['aov'],
        'tier2_frequency': tier2['frequency'],
    }


def format_sam_som(result):
    """Format SAM/SOM analysis as readable text."""
    lines = []
    lines.append('SAM / SOM ANALYSIS: TIER-2 CITY ENTRY')
    lines.append('=' * 70)
    lines.append('')
    lines.append(f"TAM (all quick commerce, Tier-1 + Tier-2): Rs {result['tam_annual_cr']:,.0f} Cr (~${result['tam_annual_usd_b']:.1f}B)")
    lines.append(f"SAM (Tier-2 cities only):                  Rs {result['sam_tier2_annual_cr']:,.0f} Cr (~${result['sam_tier2_annual_usd_b']:.1f}B)")
    lines.append(f"  Target: top {result['target_cities']} of {result['total_tier2_cities']} tier-2 cities")
    lines.append(f"  Target SAM (top {result['target_cities']} cities):         Rs {result['target_sam_annual_cr']:,.0f} Cr (~${result['target_sam_annual_usd_b']:.1f}B)")
    lines.append(f"  Assumed new-entrant share by Year 2:    {result['entrant_share_assumed']:.0%}")
    lines.append(f"  SOM (Year 2):                           Rs {result['som_annual_cr']:,.0f} Cr (~${result['som_annual_usd_b']:.1f}B)")
    lines.append('')
    lines.append('UNIT ECONOMICS CHECK:')
    lines.append(f"  Stores at Year 2: {result['stores_year2']}")
    lines.append(f"  Implied daily GOV per store: Rs {result['som_daily_gov_per_store_lakh']:.1f} lakh")
    lines.append(f"  Breakeven threshold (Blinkit benchmark): Rs {result['breakeven_threshold_lakh']:.1f} lakh/store/day")
    lines.append(f"  Meets breakeven: {'YES' if result['meets_breakeven'] else 'NO'}")
    lines.append('')
    lines.append('STRATEGIC QUESTION: What market size would justify entry?')
    lines.append(f"  For a {result['entrant_share_assumed']:.0%}-share entrant with {result['stores_year2']} stores to break even:")
    lines.append(f"  Minimum required SAM in target cities: Rs {result['min_sam_for_breakeven_cr']:,.0f} Cr (~${result['min_sam_for_breakeven_usd_b']:.1f}B)")
    lines.append(f"  Current estimated SAM in target cities: Rs {result['target_sam_annual_cr']:,.0f} Cr (~${result['target_sam_annual_usd_b']:.1f}B)")
    
    if result['meets_breakeven']:
        lines.append(f"  CONCLUSION: The estimated SAM exceeds the breakeven threshold.")
    else:
        lines.append(f"  CONCLUSION: The estimated SAM falls SHORT of the breakeven threshold.")
        gap_pct = (result['min_sam_for_breakeven_cr'] - result['target_sam_annual_cr']) / result['min_sam_for_breakeven_cr'] * 100
        lines.append(f"  Gap: {gap_pct:.0f}% shortfall. Entry requires either a larger market than estimated,")
        lines.append(f"  a higher share capture, or lower unit economics threshold than Blinkit's benchmark.")
    
    return '\n'.join(lines)


if __name__ == '__main__':
    result = compute_sam_som()
    print(format_sam_som(result))
