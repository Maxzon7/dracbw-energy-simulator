import streamlit as st
import pandas as pd
from tabs.tab2_components.solar_logic import generate_solar_profile
from logic.energy_logic import simulate_battery_logic, simulate_generator_logic

def calculate_scenario(
    plot_base_df: pd.DataFrame,
    sim_grid_limit: float,
    enable_solar: bool,
    enable_battery: bool,
    enable_generator: bool,
    params: dict,
    project_metadata: dict,
    res: int
) -> pd.DataFrame:
    """Executes the sequential solver simulations across technologies and returns the calculated DataFrame."""
    calculated_df = plot_base_df.copy()
    calculated_df['solar_gen_kw'] = 0.0
    calculated_df['battery_action_kw'] = 0.0
    calculated_df['battery_soc_kwh'] = 0.0
    calculated_df['generator_action_kw'] = 0.0
    calculated_df['generator_fuel_l'] = 0.0
    calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
    
    # Step 1: Grid Upgrade (resolves the target grid limit used in downstream simulations)
    target_sim_limit = sim_grid_limit
        
    # Step 2: Solar PV Integration
    if enable_solar and 'solar' in params:
        calculated_df = generate_solar_profile(calculated_df, project_metadata, params['solar'])
    else:
        calculated_df['solar_gen_kw'] = 0.0
        calculated_df['net_load_kw'] = calculated_df['consumption_kw']
        calculated_df['grid_feed_in_kw'] = 0.0
        
    # Step 3: Battery (BESS) Simulation
    if enable_battery and 'battery' in params:
        # Ensure battery shaving threshold does not exceed the target grid limit
        bat_params = params['battery'].copy()
        bat_params['shaving_threshold'] = min(float(bat_params.get('shaving_threshold', target_sim_limit)), target_sim_limit)
        calculated_df = simulate_battery_logic(calculated_df, target_sim_limit, bat_params, res)
    else:
        calculated_df['battery_action_kw'] = 0.0
        calculated_df['battery_soc_kwh'] = 0.0
        calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
        
    # Step 4: Backup Generator Simulation
    if enable_generator and 'generator' in params:
        calculated_df = simulate_generator_logic(calculated_df, target_sim_limit, params['generator'], res)
    else:
        calculated_df['generator_action_kw'] = 0.0
        calculated_df['generator_fuel_l'] = 0.0
        
    if 'final_grid_load_kw' not in calculated_df.columns:
        calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
        
    return calculated_df
