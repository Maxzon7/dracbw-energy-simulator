import pandas as pd
import numpy as np
import streamlit as st 

@st.cache_data(show_spinner="Lese Rohdaten in den Zwischenspeicher...")
def load_and_clean_csv(file_obj) -> pd.DataFrame:
    """
    Intelligently reads a CSV file, dynamically handling different separators 
    and bypassing irregular header structures. Cached for extreme performance.
    """
    # Streamlit hashes the file. To be safe, we always start reading at byte 0.
    file_obj.seek(0) 
    
    # Read the first few lines as a string to analyze the structure
    content = file_obj.read().decode('utf-8', errors='ignore')
    
    # Reset the file pointer back to the beginning so pandas can read it properly
    file_obj.seek(0) 
    
    lines = content.split('\n')
    first_line = lines[0] if len(lines) > 0 else ""
    
    # Check if the first line is a descriptive header rather than actual column names.
    skip_rows = 0
    if first_line.startswith(';;') or 'Meter' in first_line:
        skip_rows = 1
        
    # Read the CSV. 
    # sep=None allows the python engine to automatically detect the delimiter.
    df = pd.read_csv(file_obj, sep=None, engine='python', skiprows=skip_rows)
    return df

@st.cache_data(show_spinner="Formatiere Zeitstempel und erstelle Intervalle (dauert nur einmalig)...")
def process_consumption_data(df: pd.DataFrame, interval_minutes: int, time_col: str = None, power_col: str = None, unit: str = "W", use_float64: bool = False) -> pd.DataFrame:
    """
    Standardizes the raw meter data into the required simulation format.
    Dynamically maps available columns or uses user-selected columns from the popup dialog.
    Cached to prevent massive CPU load when re-parsing 8760+ datetime rows.
    """
    # Falls keine Spalten übergeben wurden, starte die automatische Erkennung (Fallback)
    if not time_col or not power_col:
        possible_time_cols = ['Time', 'time', 'timestamp', 'Datum', 'Date', 'zeit', 'datum']
        possible_power_cols = ['Totaal_Vermogen_(System_Power)', 'WATT_TOT', 'Total_Power', 'System_Power', 'consumption_kw', 'leistung']
        
        for col in df.columns:
            clean_col = str(col).strip()
            if not time_col and clean_col in possible_time_cols:
                time_col = col
            if not power_col and clean_col in possible_power_cols:
                power_col = col
            
    if not time_col or not power_col:
        raise ValueError("Erforderliche Spalten für Zeit oder Leistung nicht gefunden. Bitte nutze die manuelle Zuordnung im Popup.")
        
    try:
        # Extrahiere die vom Nutzer gewählten Spalten
        df_clean = df[[time_col, power_col]].copy()
        df_clean.columns = ['timestamp', 'consumption_kw']
    except Exception as e:
        raise ValueError(f"Fehler bei der Spaltenextraktion: {e}")
    
    # Bereinigung europäischer Komma-Zahlen (z.B. "12,5" -> "12.5")
    if df_clean['consumption_kw'].dtype == object:
        df_clean['consumption_kw'] = df_clean['consumption_kw'].astype(str).str.replace(',', '.')
        
    # In numerische Werte umwandeln
    df_clean['consumption_kw'] = pd.to_numeric(df_clean['consumption_kw'], errors='coerce')
    
    # Einheiten-Umrechnung: Wenn die Daten in Watt (W) vorliegen, teile durch 1000 für kW
    if unit == "W":
        df_clean['consumption_kw'] = df_clean['consumption_kw'] / 1000.0 
        
    # --- UPGRADE: DATENTYP-SCHLANKHEITSKUR (DOWNCASTING) ---
    # Default is False, which forces 32-bit floats to halve RAM usage and boost loop speed.
    if not use_float64:
        df_clean['consumption_kw'] = df_clean['consumption_kw'].astype('float32')
    # -------------------------------------------------------
    
    # Zeitstempel parsen (Das ist der rechenintensivste Prozess im ganzen Tool!)
    df_clean['timestamp'] = pd.to_datetime(df_clean['timestamp'], errors='coerce')
    
    # Fehlerhafte Zeilen löschen
    df_clean.dropna(subset=['timestamp', 'consumption_kw'], inplace=True)
    df_clean.set_index('timestamp', inplace=True)
    
    # Auf das gewünschte Intervall resampeln
    resample_rule = f"{interval_minutes}min"
    return df_clean.resample(resample_rule).mean(numeric_only=True).reset_index().dropna()

# --- DIE UNTEREN FUNKTIONEN BLEIBEN OHNE CACHE ---
# (Da sie sich sofort anpassen müssen, wenn man die Batterie-Parameter ändert)

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

def simulate_battery_logic(df: pd.DataFrame, grid_limit: float, b_params: dict, res: int = 15) -> pd.DataFrame:
    """
    Simulates a highly precise physical quarter-hourly battery storage dispatch loop.
    Implements threshold trigger constraints and controlled, safe recharging schedules.
    """
    res_factor = 60 / res # 4 for 15-min intervals
    
    # Extract structural configuration parameters
    b_cap = b_params.get('b_cap', 200.0)
    b_pwr = b_params.get('b_pwr', 100.0)
    shaving_threshold = b_params.get('shaving_threshold', 120.0)
    charge_pwr_limit = b_params.get('charge_pwr_limit', 30.0)
    start_hour = b_params.get('charge_start_hour', 22)
    end_hour = b_params.get('charge_end_hour', 6)
    green_charging = b_params.get('green_charging', False)
    
    # Mathematical split of round-trip loss using square root
    eff_factor = (b_params.get('efficiency', 92.0) / 100.0) ** 0.5
    
    # State tracking vectors
    soc_history = []
    action_history = []
    final_grid_load = []
    
    # Establish starting capacity
    current_soc_kwh = b_cap * (b_params.get('initial_soc_pct', 50.0) / 100.0)
    
    # Check if a solar yield baseline column exists to factor in net load offsets
    load_source_col = 'net_load_kw' if 'net_load_kw' in df.columns else 'consumption_kw'
    solar_gen_col = 'solar_gen_kw' if 'solar_gen_kw' in df.columns else None

    # THE CORE 34,560 INTERVAL STEPPING LOOP
    for _, row in df.iterrows():
        timestamp = row['timestamp']
        current_load = row[load_source_col]
        solar_yield = row[solar_gen_col] if solar_gen_col else 0.0
        
        current_hour = timestamp.hour
        battery_action_kw = 0.0 # Negative = Charging, Positive = Discharging
        
        # --- PHASE 1: DISCHARGING MODE (PEAK SHAVING TRIGGER) ---
        if current_load > shaving_threshold:
            required_discharge_kw = current_load - shaving_threshold
            
            # Limit by maximum physical inverter constraint
            allowed_discharge_kw = min(required_discharge_kw, b_pwr)
            
            # Limit by actual remaining chemical energy in the cells (factoring efficiency loss)
            max_available_from_cells_kw = (current_soc_kwh * res_factor) * eff_factor
            final_discharge_kw = min(allowed_discharge_kw, max_available_from_cells_kw)
            
            # Dispatch energy and update system memory states
            battery_action_kw = final_discharge_kw
            current_soc_kwh -= (final_discharge_kw / res_factor) / eff_factor
            
        # --- PHASE 2: SAFE RECHARGING MODE ---
        else:
            # Evaluate time window window boundary rules
            is_inside_window = False
            if start_hour <= end_hour:
                is_inside_window = (start_hour <= current_hour <= end_hour)
            else: # Handles overnight wrap-around windows (e.g., 22:00 to 06:00)
                is_inside_window = (current_hour >= start_hour or current_hour <= end_hour)
                
            if is_inside_window and current_soc_kwh < b_cap:
                # Calculate maximum headroom capacity inside the tank
                empty_space_kwh = b_cap - current_soc_kwh
                max_charge_allowed_by_cells_kw = (empty_space_kwh * res_factor) / eff_factor
                
                # Base charging ceiling driven by hardware settings
                max_charging_speed_kw = min(b_pwr, charge_pwr_limit, max_charge_allowed_by_cells_kw)
                
                if green_charging:
                    # Only charge using real physical solar surplus power
                    solar_surplus_kw = max(0.0, solar_yield - row['consumption_kw'])
                    final_charge_kw = min(max_charging_speed_kw, solar_surplus_kw)
                else:
                    # Grid charging: CRITICAL constraint to prevent creating a secondary peak!
                    # Total grid draw (load + battery charge) must never cross the shaving threshold
                    grid_headroom_kw = max(0.0, shaving_threshold - current_load)
                    final_charge_kw = min(max_charging_speed_kw, grid_headroom_kw)
                
                # Absorbing energy into storage and update system memory states
                battery_action_kw = -final_charge_kw
                current_soc_kwh += (final_charge_kw / res_factor) * eff_factor

        # Finalize array tracking states
        soc_history.append(current_soc_kwh)
        action_history.append(battery_action_kw)
        
        # Grid load is baseline consumption minus battery output (discharge reduces, charge increases it)
        final_grid_load.append(current_load - battery_action_kw)

    # Append structural result profiles to the output dataframe package
    df['battery_soc_kwh'] = soc_history
    df['battery_action_kw'] = action_history
    df['final_grid_load_kw'] = final_grid_load
    
    return df