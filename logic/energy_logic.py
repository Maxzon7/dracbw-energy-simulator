import pandas as pd
import numpy as np
import streamlit as st 

@st.cache_data(show_spinner="Lese Rohdaten in den Zwischenspeicher...")
def load_and_clean_csv(file_obj) -> pd.DataFrame:
    """
    Intelligently reads a CSV file, dynamically handling different separators 
    and bypassing irregular header structures. Cached for extreme performance.
    """
    file_obj.seek(0) 
    content = file_obj.read().decode('utf-8', errors='ignore')
    file_obj.seek(0) 
    lines = content.split('\n')
    first_line = lines[0] if len(lines) > 0 else ""
    skip_rows = 1 if first_line.startswith(';;') or 'Meter' in first_line else 0
    df = pd.read_csv(file_obj, sep=None, engine='python', skiprows=skip_rows)
    return df

@st.cache_data(show_spinner="Formatiere Zeitstempel und erstelle Intervalle...")
def process_consumption_data(df: pd.DataFrame, interval_minutes: int, time_col: str = None, power_col = None, unit: str = "W", use_float64: bool = False) -> pd.DataFrame:
    """
    Standardizes the raw meter data into the required simulation format.
    UPGRADED: Now supports multiple sub-meters. Converts each, retains them in the dataframe, 
    and generates an aggregated 'consumption_kw' total column for system stability.
    """
    # 1. Handle fallback logic if no columns were explicitly provided
    if not time_col or not power_col:
        possible_time_cols = ['Time', 'time', 'timestamp', 'Datum', 'Date', 'zeit', 'datum']
        possible_power_cols = ['Totaal_Vermogen_(System_Power)', 'WATT_TOT', 'Total_Power', 'System_Power', 'consumption_kw', 'leistung']
        
        for col in df.columns:
            clean_col = str(col).strip()
            if not time_col and clean_col in possible_time_cols:
                time_col = col
            if not power_col and clean_col in possible_power_cols:
                power_col = [col] # Initialize as a list for consistency
            
    if not time_col or not power_col:
        raise ValueError("Erforderliche Spalten für Zeit oder Leistung nicht gefunden. Bitte nutze die manuelle Zuordnung im Popup.")
        
    # Ensure power_col is treated as a list
    power_cols = power_col if isinstance(power_col, list) else [power_col]
        
    try:
        cols_to_extract = [time_col] + power_cols
        df_clean = df[cols_to_extract].copy()
        df_clean.rename(columns={time_col: 'timestamp'}, inplace=True)
    except Exception as e:
        raise ValueError(f"Fehler bei der Spaltenextraktion: {e}")
    
    # Process each selected power column individually
    for col in power_cols:
        if df_clean[col].dtype == object:
            df_clean[col] = df_clean[col].astype(str).str.replace(',', '.')
            
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        if unit == "W":
            df_clean[col] = df_clean[col] / 1000.0 
            
        if not use_float64:
            df_clean[col] = df_clean[col].astype('float32')
            
    # CRITICAL STABILITY FIX: Create the master column required by the rest of the application
    df_clean['consumption_kw'] = df_clean[power_cols].sum(axis=1)
    
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], errors='coerce')
    df_clean.dropna(subset=['timestamp', 'consumption_kw'], inplace=True)
    df_clean.set_index('timestamp', inplace=True)
    
    resample_rule = f"{interval_minutes}min"
    return df_clean.resample(resample_rule).mean(numeric_only=True).reset_index().dropna()
def get_exact_minimum_requirements(df: pd.DataFrame, grid_limit_kw: float, interval_min: int) -> dict:
    """
    Calculates the EXACT minimum battery specs needed using an 'Infinite Ghost Battery' algorithm.
    """
    interval_hours = interval_min / 60.0
    diff = df['consumption_kw'] - grid_limit_kw
    max_power_needed = max(0, diff.max())
    
    virtual_soc = 0.0
    min_soc_reached = 0.0
    
    for power_diff in diff:
        if power_diff > 0: 
            virtual_soc -= (power_diff * interval_hours)
            if virtual_soc < min_soc_reached:
                min_soc_reached = virtual_soc
        else: 
            virtual_soc += (abs(power_diff) * interval_hours)
            if virtual_soc > 0:
                virtual_soc = 0.0 
                
    true_min_capacity_kwh = abs(min_soc_reached)
    
    return {
        "min_power_kw": max_power_needed,
        "true_min_capacity_kwh": true_min_capacity_kwh
    }

def simulate_battery_logic(df: pd.DataFrame, grid_limit: float, b_params: dict, res: int = 15) -> pd.DataFrame:
    """
    Simulates a highly precise physical quarter-hourly battery storage dispatch loop.
    """
    res_factor = 60 / res 
    
    b_cap = b_params.get('b_cap', 200.0)
    b_pwr = b_params.get('b_pwr', 100.0)
    shaving_threshold = b_params.get('shaving_threshold', 120.0)
    charge_pwr_limit = b_params.get('charge_pwr_limit', 30.0)
    start_hour = b_params.get('charge_start_hour', 22)
    end_hour = b_params.get('charge_end_hour', 6)
    green_charging = b_params.get('green_charging', False)
    
    eff_factor = (b_params.get('efficiency', 92.0) / 100.0) ** 0.5
    
    soc_history = []
    action_history = []
    final_grid_load = []
    
    current_soc_kwh = b_cap * (b_params.get('initial_soc_pct', 50.0) / 100.0)
    
    load_source_col = 'net_load_kw' if 'net_load_kw' in df.columns else 'consumption_kw'
    solar_gen_col = 'solar_gen_kw' if 'solar_gen_kw' in df.columns else None

    for _, row in df.iterrows():
        timestamp = row['timestamp']
        current_load = row[load_source_col]
        solar_yield = row[solar_gen_col] if solar_gen_col else 0.0
        
        current_hour = timestamp.hour
        battery_action_kw = 0.0 
        
        if current_load > shaving_threshold:
            required_discharge_kw = current_load - shaving_threshold
            allowed_discharge_kw = min(required_discharge_kw, b_pwr)
            max_available_from_cells_kw = (current_soc_kwh * res_factor) * eff_factor
            final_discharge_kw = min(allowed_discharge_kw, max_available_from_cells_kw)
            
            battery_action_kw = final_discharge_kw
            current_soc_kwh -= (final_discharge_kw / res_factor) / eff_factor
            
        else:
            is_inside_window = False
            if start_hour <= end_hour:
                is_inside_window = (start_hour <= current_hour <= end_hour)
            else: 
                is_inside_window = (current_hour >= start_hour or current_hour <= end_hour)
                
            if is_inside_window and current_soc_kwh < b_cap:
                empty_space_kwh = b_cap - current_soc_kwh
                max_charge_allowed_by_cells_kw = (empty_space_kwh * res_factor) / eff_factor
                max_charging_speed_kw = min(b_pwr, charge_pwr_limit, max_charge_allowed_by_cells_kw)
                
                if green_charging:
                    solar_surplus_kw = max(0.0, solar_yield - row['consumption_kw'])
                    final_charge_kw = min(max_charging_speed_kw, solar_surplus_kw)
                else:
                    grid_headroom_kw = max(0.0, shaving_threshold - current_load)
                    final_charge_kw = min(max_charging_speed_kw, grid_headroom_kw)
                
                battery_action_kw = -final_charge_kw
                current_soc_kwh += (final_charge_kw / res_factor) * eff_factor

        soc_history.append(current_soc_kwh)
        action_history.append(battery_action_kw)
        final_grid_load.append(current_load - battery_action_kw)

    df['battery_soc_kwh'] = soc_history
    df['battery_action_kw'] = action_history
    df['final_grid_load_kw'] = final_grid_load
    
    return df

def simulate_generator_logic(df: pd.DataFrame, grid_limit: float, gen_params: dict, res: int = 15) -> pd.DataFrame:
    """
    Simulates a backup generator (Diesel/Gas) that acts as the absolute last resort.
    It automatically detects if a battery or solar system already attempted to reduce the load
    and only kicks in for the remaining deficit that would blow the grid fuse.
    """
    res_factor = 60 / res 
    
    gen_pwr = gen_params.get('gen_pwr', 100.0)             
    fuel_rate = gen_params.get('fuel_l_per_kwh', 0.28)     
    
    gen_action_history = []
    fuel_history = []
    new_final_grid_load = []
    
    if 'final_grid_load_kw' in df.columns:
        load_source_col = 'final_grid_load_kw'
    elif 'net_load_kw' in df.columns:
        load_source_col = 'net_load_kw'
    else:
        load_source_col = 'consumption_kw'
        
    for _, row in df.iterrows():
        current_load = row[load_source_col]
        generator_action_kw = 0.0
        fuel_consumed_l = 0.0
        
        if current_load > grid_limit:
            required_gen_kw = current_load - grid_limit
            generator_action_kw = min(required_gen_kw, gen_pwr)
            fuel_consumed_l = (generator_action_kw / res_factor) * fuel_rate
            
        gen_action_history.append(generator_action_kw)
        fuel_history.append(fuel_consumed_l)
        new_final_grid_load.append(current_load - generator_action_kw)
        
    df['generator_action_kw'] = gen_action_history
    df['generator_fuel_l'] = fuel_history
    df['final_grid_load_kw'] = new_final_grid_load 
    
    return df
