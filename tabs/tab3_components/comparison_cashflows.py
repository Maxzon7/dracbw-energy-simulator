import pandas as pd
from tabs.tab3_components.financial_engine import calculate_annual_grid_bill_with_pillars

def generate_baseline_cashflow_df(base_scenario, discount_rate, capex_mult=1.0, energy_esc_add=0.0):
    """Generates the business-as-usual cashflow projection dataframe for the baseline scenario."""
    fin_meta = base_scenario.metadata.get('financial_metadata', {})
    lifespan = int(fin_meta.get('lifespan_years', 15))
    base_grid_capex = float(fin_meta.get('baseline_grid_capex', 0.0))
    base_tariff = base_scenario.base_tariff
    
    base_df = base_scenario.original_profile
    if len(base_df) > 0:
        factor = 4.0 if len(base_df) > 15000 else 1.0
    else:
        factor = 1.0
        
    base_grid_bill_yr1 = calculate_annual_grid_bill_with_pillars(base_df, fin_meta)
    
    energy_esc = float(fin_meta.get('energy_price_growth', 4.0)) / 100.0 + energy_esc_add
    
    jahre = list(range(lifespan + 1))
    df = pd.DataFrame({"Year": jahre})
    
    df["CAPEX (€)"] = 0.0
    df.loc[df["Year"] == 0, "CAPEX (€)"] = -base_grid_capex * capex_mult
    
    grid_costs = [0.0]
    for jahr in range(1, lifespan + 1):
        grid_multiplier = (1.0 + energy_esc) ** (jahr - 1)
        grid_costs.append(-base_grid_bill_yr1 * grid_multiplier)
        
    df["OPEX (€)"] = 0.0
    df["Grid Savings (€)"] = 0.0
    df["Generator Fuel (€)"] = 0.0
    df["Generator Rental (€)"] = 0.0
    df["Generator Maintenance (€)"] = 0.0
    df["Grid Costs (€)"] = grid_costs
    
    df["Net Cashflow (€)"] = df["CAPEX (€)"] + df["Grid Costs (€)"]
    df["Cumulative Cashflow (€)"] = df["Net Cashflow (€)"].cumsum()
    df["Present Value (€)"] = df["Net Cashflow (€)"] / ((1.0 + discount_rate) ** df["Year"])
    df["Cumulative NPV (€)"] = df["Present Value (€)"].cumsum()
    
    return df
