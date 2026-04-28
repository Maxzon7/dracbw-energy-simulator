import pandas as pd
import numpy as np

def load_and_clean_csv(file_obj) -> pd.DataFrame:
    """
    Intelligently reads a CSV file, dynamically handling different separators 
    and bypassing irregular header structures.
    """
    # Read the first few lines as a string to analyze the structure
    content = file_obj.read().decode('utf-8', errors='ignore')
    
    # Reset the file pointer back to the beginning so pandas can read it properly
    file_obj.seek(0) 
    
    lines = content.split('\n')
    first_line = lines[0] if len(lines) > 0 else ""
    
    # Check if the first line is a descriptive header rather than actual column names.
    # The Kast L1 file starts with ';;Meter 1 groep...' which is not tabular data.
    skip_rows = 0
    if first_line.startswith(';;') or 'Meter' in first_line:
        skip_rows = 1
        
    # Read the CSV. 
    # sep=None allows the python engine to automatically detect the delimiter (',' or ';').
    df = pd.read_csv(file_obj, sep=None, engine='python', skiprows=skip_rows)
    return df

def process_consumption_data(df: pd.DataFrame, interval_minutes: int) -> pd.DataFrame:
    """
    Standardizes the raw meter data into the required simulation format.
    Dynamically maps available columns to the required 'timestamp' and 'consumption_kw'.
    """
    time_col = None
    power_col = None
    
    # Define acceptable variations of column names for robustness
    possible_time_cols = ['Time', 'time', 'timestamp', 'Datum', 'Date']
    possible_power_cols = ['Totaal_Vermogen_(System_Power)', 'WATT_TOT', 'Total_Power', 'System_Power']
    
    # Search for the correct columns in the dataframe
    for col in df.columns:
        # Strip whitespaces just in case the CSV is messy
        clean_col = str(col).strip()
        if clean_col in possible_time_cols:
            time_col = col
        if clean_col in possible_power_cols:
            power_col = col
            
    if not time_col or not power_col:
        raise ValueError("Required columns for Time or Power not found. Please ensure the CSV contains a recognized time and total power column.")
        
    try:
        # Extract only the necessary data
        df_clean = df[[time_col, power_col]].copy()
        df_clean.columns = ['timestamp', 'consumption_kw']
    except Exception as e:
        raise ValueError(f"Error extracting data columns: {e}")
    
    # Ensure numeric types and convert from Watts to Kilowatts (kW)
    # Using errors='coerce' forces invalid text (like 'NaN') into true Null values
    df_clean['consumption_kw'] = pd.to_numeric(df_clean['consumption_kw'], errors='coerce') / 1000.0 
    
    # Parse timestamps dynamically
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], errors='coerce')
    
    # Remove any rows where time or consumption could not be read
    df_clean.dropna(subset=['timestamp', 'consumption_kw'], inplace=True)
    df_clean.set_index('timestamp', inplace=True)
    
    # Resample the data to the desired interval (e.g., 15 minutes)
    resample_rule = f"{interval_minutes}min"
    
    # numeric_only=True prevents pandas warnings when averaging
    return df_clean.resample(resample_rule).mean(numeric_only=True).reset_index().dropna()

def get_exact_minimum_requirements(df: pd.DataFrame, grid_limit_kw: float, interval_min: int) -> dict:
    """
    Calculates the EXACT minimum battery specs needed using an 'Infinite Ghost Battery' algorithm.
    It tracks the cumulative energy deficit to find the true minimum capacity required.
    """
    interval_hours = interval_min / 60.0
    diff = df['consumption_kw'] - grid_limit_kw
    
    # 1. Absolute Minimum Power required to cover the highest single peak
    max_power_needed = max(0, diff.max())
    
    # 2. Absolute Minimum Capacity required
    # We simulate a battery starting at 0 that only tracks deficits.
    virtual_soc = 0.0
    min_soc_reached = 0.0
    
    for power_diff in diff:
        if power_diff > 0: 
            # Deficit: We need energy from the battery
            virtual_soc -= (power_diff * interval_hours)
            if virtual_soc < min_soc_reached:
                min_soc_reached = virtual_soc
        else: 
            # Surplus: We can recharge the battery
            virtual_soc += (abs(power_diff) * interval_hours)
            if virtual_soc > 0:
                # We only care about covering peaks. If it recharges past 0, cap it.
                virtual_soc = 0.0 
                
    true_min_capacity_kwh = abs(min_soc_reached)
    
    return {
        "min_power_kw": max_power_needed,
        "true_min_capacity_kwh": true_min_capacity_kwh
    }

def simulate_battery_logic(df: pd.DataFrame, 
                           grid_limit_kw: float, 
                           battery_cap_kwh: float, 
                           battery_power_kw: float,
                           interval_min: int) -> pd.DataFrame:
    """
    Core simulation loop for battery State of Charge (SoC).
    """
    results = df.copy()
    interval_hours = interval_min / 60.0
    
    soc_list = []
    battery_action_list = [] 
    
    current_soc_kwh = 0.0 # Start empty
    
    for _, row in results.iterrows():
        load = row['consumption_kw']
        diff_kw = load - grid_limit_kw
        actual_battery_kw = 0.0
        
        if diff_kw > 0: # Peak detected -> Discharge
            max_discharge = min(diff_kw, battery_power_kw, current_soc_kwh / interval_hours)
            actual_battery_kw = max_discharge
            current_soc_kwh -= (actual_battery_kw * interval_hours)
        elif diff_kw < 0: # Charging opportunity -> Charge
            spare_kw = abs(diff_kw)
            max_charge = min(spare_kw, battery_power_kw, (battery_cap_kwh - current_soc_kwh) / interval_hours)
            actual_battery_kw = -max_charge # Negative means energy goes INTO the battery
            current_soc_kwh += (abs(actual_battery_kw) * interval_hours)
            
        soc_list.append(current_soc_kwh)
        battery_action_list.append(actual_battery_kw)

    results['battery_soc_kwh'] = soc_list
    results['battery_action_kw'] = battery_action_list
    results['final_grid_load_kw'] = results['consumption_kw'] - results['battery_action_kw']
    
    return results