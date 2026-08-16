# Indian Quick Commerce Market Sizing

This repository contains a rigorous, data-driven market sizing of the Indian Quick Commerce (10-20 minute delivery) market for FY2025-26. 

This project was built to demonstrate an alternative approach to traditional "guesstimate" case interviews. Instead of a single point estimate built on unverified assumptions, this model triangulates the market size using a strict bottom-up funnel calibrated against top-down disclosed financials from the major players (Blinkit, Instamart, Zepto). 

Every number used in this project is either a verifiable metric from a public filing or an explicit, sensitivity-tested assumption.

## Project Architecture

The core philosophy of this project is **independent triangulation**:
1. **Bottom-Up (`src/bottom_up.py`)**: A purely demographic funnel starting from the 2011 Census urban population projections, filtering for income, digital readiness, and adoption rates. It does not look at company GOV figures.
2. **Top-Down (`src/top_down.py`)**: A purely financial summation using SEBI filings and shareholder letters. It handles accounting nuances like Blinkit's FY26 transition from Gross Order Value (GOV) to Net Order Value (NOV).
3. **Reconciliation (`run_model.py`)**: The two independent estimates are brought together and compared, exposing the gap between demographic theory and market reality.

## Running the Model

### Prerequisites
- Python 3.9+
- `pandas`, `pyyaml`, `matplotlib`

### Execution
Run the entry point script from the root directory:
```bash
python run_model.py
```

This script will recalculate all figures based on `assumptions.yaml` and generate:
- Console output of the full reconciliation and sensitivity analysis
- `output/results_summary.json`
- Visualization charts in the `output/` directory:
  - `tornado_sensitivity.png`: Sensitivity of the bottom-up TAM to key assumptions
  - `market_share.png`: FY25 competitive market share
  - `scenario_comparison.png`: Low, Base, and High scenario TAMs
  - `quarterly_gov_trend.png`: Quarterly GOV growth trajectory of the players

## Key Nuances Addressed

- **Category Expansion**: The model explicitly notes that while quick commerce started as "grocery and essentials," a rising share of GOV now comes from electronics, beauty, and cafe items. The model sizes the *full* quick commerce GOV to match company disclosures.
- **1P vs 3P Accounting**: Blinkit transitioned from a marketplace model to an inventory-led model in FY26, switching its primary metric from GOV to NOV (excluding taxes and delivery fees). The `top_down.py` script carefully converts NOV back to a GOV-equivalent basis to maintain comparability with Instamart and Zepto.

## Repository Structure

- `assumptions.yaml`: The central configuration file. All demographic and economic assumptions live here, fully cited.
- `data/`: Contains the raw CSV datasets extracted from company shareholder letters, SEBI DRHPs, and government census/survey data. 
- `data/sources.md`: A detailed methodology document listing all citations and links.
- `src/`: The core Python logic suite for calculating TAM, SAM, SOM, and competitive shares.
- `output/`: Auto-generated charts and JSON summaries.
- `memo/case_memo.md`: The final synthesized business memo outlining the key findings.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
