# tabs/tab2_components/scenario_engine.py
import pandas as pd
from tabs.tab2_components.solar_logic import generate_synthetic_solar_profile
from logic.energy_logic import simulate_battery_logic

def run_isolated_scenario(baseline_df: pd.DataFrame, mode: str, params: tuple, grid_limit: float, res: int = 15) -> pd.DataFrame:
    """
    Runs strictly isolated scenarios (Either Solar OR Battery).
    """
    df = baseline_df.copy()
    
    # 1. Standard-Spalten anlegen
    df['solar_gen_kw'] = 0.0
    df['unprofitable_excess_kw'] = 0.0
    df['battery_action_kw'] = 0.0
    df['battery_soc_kwh'] = 0.0
    df['final_grid_load_kw'] = df['consumption_kw']
    
    # ==========================================
    # PFAD A: NUR SOLAR
    # ==========================================
    if mode == "Solar PV":
        enable, kwp, yield_factor = params
        if enable and kwp > 0:
            df['solar_gen_kw'] = generate_synthetic_solar_profile(df['timestamp'], kwp, yield_factor)
            
        net_demand = df['consumption_kw'] - df['solar_gen_kw']
        df['unprofitable_excess_kw'] = net_demand.apply(lambda x: abs(x) if x < 0 else 0)
        df['final_grid_load_kw'] = net_demand.apply(lambda x: max(x, 0))
        
    # ==========================================
    # PFAD B: NUR BATTERIE
    # ==========================================
    elif mode == "Battery (Peak Shaving)":
        enable, b_params = params
        if enable and b_params["b_cap"] > 0:
            bat_res = simulate_battery_logic(df, grid_limit, b_params, res)
            df['battery_action_kw'] = bat_res['battery_action_kw']
            df['battery_soc_kwh'] = bat_res['battery_soc_kwh']
            df['final_grid_load_kw'] = bat_res['final_grid_load_kw']
            
            # Die Degradations-KPIs hängen wir uns unsichtbar als Meta-Daten an
            if hasattr(bat_res, 'attrs'):
                df.attrs['bess_metrics'] = bat_res.attrs.get('bess_metrics', {})
            
    return df