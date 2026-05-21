# tabs/tab2_components/scenario_engine.py
import pandas as pd
from logic.energy_logic import simulate_battery_logic

# --- FIXES THE IMPORT ERROR: Link to our upgraded solar core function ---
from tabs.tab2_components.solar_logic import generate_solar_profile

def run_isolated_scenario(baseline_df: pd.DataFrame, mode: str, params: dict, grid_limit: float, res: int = 15) -> pd.DataFrame:
    """
    Runs strictly isolated scenarios (Either Solar OR Battery).
    Updated to align with new data models and eliminate import mismatches.
    """
    df = baseline_df.copy()
    
    # 1. Initialize standard tracking columns
    df['solar_gen_kw'] = 0.0
    df['unprofitable_excess_kw'] = 0.0
    df['battery_action_kw'] = 0.0
    df['battery_soc_kwh'] = 0.0
    df['final_grid_load_kw'] = df['consumption_kw']
    
    # ==========================================
    # PATH A: SOLAR PV PIPELINE
    # ==========================================
    if "Solar" in mode:
        # Fallback route for legacy execution if called via scenario engine directly
        project_metadata = df.attrs.get('project_metadata', {})
        df = generate_solar_profile(df, project_metadata, params)
        df['final_grid_load_kw'] = df['net_load_kw']
        
    # ==========================================
    # PATH B: BATTERY ONLY PIPELINE
    # ==========================================
    elif mode == "Battery (Peak Shaving)":
        # Keep old battery logic fully functional
        # Safe-guard to handle both old tuple parameters and new dictionary formatting
        if isinstance(params, tuple):
            enable, b_params = params
        else:
            enable = True
            b_params = params
            
        if enable and b_params.get("b_cap", 0) > 0:
            bat_res = simulate_battery_logic(df, grid_limit, b_params, res)
            df['battery_action_kw'] = bat_res['battery_action_kw']
            df['battery_soc_kwh'] = bat_res['battery_soc_kwh']
            df['final_grid_load_kw'] = bat_res['final_grid_load_kw']
            
            # Safely attach physical degradation tracking parameters as metadata attributes
            if hasattr(bat_res, 'attrs'):
                df.attrs['bess_metrics'] = bat_res.attrs.get('bess_metrics', {})
            
    return df