# tabs/tab2_components/solar_logic.py
import pandas as pd
import numpy as np

# 1. DATABASE: Global Horizontal Irradiation (GHI) in kWh/m2/day per month
# Based on PVGIS (Europe) and NASA POWER (Argentina)
GHI_DATABASE = {
    "Netherlands 🇳🇱": {1: 0.8, 2: 1.5, 3: 2.5, 4: 4.0, 5: 5.0, 6: 5.5, 7: 5.2, 8: 4.5, 9: 3.0, 10: 1.8, 11: 0.9, 12: 0.6},
    "Germany 🇩🇪":     {1: 0.9, 2: 1.6, 3: 2.6, 4: 4.2, 5: 5.1, 6: 5.6, 7: 5.3, 8: 4.6, 9: 3.1, 10: 1.9, 11: 1.0, 12: 0.7},
    "Argentina 🇦🇷":  {1: 6.8, 2: 6.2, 3: 5.5, 4: 4.5, 5: 3.8, 6: 3.2, 7: 3.5, 8: 4.5, 9: 5.5, 10: 6.2, 11: 6.8, 12: 7.1},
    "Other":          {m: 3.5 for m in range(1, 13)}
}

def get_transposition_factor(country: str, tilt: str, azimuth: str) -> float:
    """
    Returns the performance multiplier based on panel orientation and tilt.
    Extracts logic from standard CF-Documents (Transposition Matrices).
    """
    # Southern Hemisphere (Argentina) needs North-facing panels
    if "Argentina" in country:
        if azimuth == "North (0°)" and tilt == "30°": return 1.15
        if azimuth == "North (0°)" and tilt == "15°": return 1.08
        if azimuth in ["East (90°)", "West (270°)"]: return 0.95
        return 0.85 # Suboptimal (e.g. South facing in Argentina)
    
    # Northern Hemisphere (Europe) needs South-facing panels
    else:
        if azimuth == "South (180°)" and tilt == "30°": return 1.12
        if azimuth == "South (180°)" and tilt == "15°": return 1.05
        if azimuth in ["East (90°)", "West (270°)"]: return 0.90
        return 0.80

def generate_solar_profile(baseline_df: pd.DataFrame, project_metadata: dict, solar_params: dict) -> pd.DataFrame:
    """
    Layer 2 & 3: Calculates 15-min solar generation and the resulting energy balance matrix.
    """
    df = baseline_df.copy()
    
    # Extract Parameters
    country = project_metadata.get('country', "Other")
    strict_zero_export = project_metadata.get('strict_zero_export', False)
    
    kwp = solar_params['installed_kwp']
    pr = solar_params['performance_ratio'] / 100.0
    tilt = solar_params['tilt']
    azimuth = solar_params['azimuth']
    thermal_loss_active = solar_params['thermal_loss']
    
    # Fetch geography data
    ghi_monthly = GHI_DATABASE.get(country, GHI_DATABASE["Other"])
    transposition = get_transposition_factor(country, tilt, azimuth)
    
    # Pre-calculate a Gaussian bell curve shape for 96 intervals (1 day)
    # Centered at interval 48 (12:00 PM), standard deviation 12 intervals (3 hours)
    intervals = np.arange(96)
    bell_curve = np.exp(-0.5 * ((intervals - 48) / 12) ** 2)
    bell_curve /= bell_curve.sum() # Normalize so the sum equals 1.0
    
    solar_generation = []
    
    # Fast iteration over the 365 days
    for date, group in df.groupby(df['timestamp'].dt.date):
        month = date.month
        
        # 1. Calculate Daily Energy Yield in kWh
        daily_ghi = ghi_monthly[month]
        daily_energy_yield_kwh = kwp * daily_ghi * transposition * pr
        
        # 2. Distribute over the 96 intervals of the day (convert to kW power by multiplying by 4)
        daily_power_kw = (daily_energy_yield_kwh * bell_curve) * 4
        
        # 3. Apply Thermal Loss (DRACBV standard: high midday temps reduce efficiency)
        if thermal_loss_active and month in [6, 7, 8] and "Argentina" not in country:
            # Drop midday peaks by 5% in European summer
            daily_power_kw[40:56] *= 0.95 
        elif thermal_loss_active and month in [12, 1, 2] and "Argentina" in country:
            # Drop midday peaks by 5% in Argentine summer
            daily_power_kw[40:56] *= 0.95
            
        solar_generation.extend(daily_power_kw)
    
    # Add to dataframe
    df['solar_gen_kw'] = solar_generation
    
    # Layer 3: Energy Balance Matrix
    # Direct Self-Consumption Priority
    df['net_load_kw'] = df['consumption_kw'] - df['solar_gen_kw']
    
    # Handle strict zero export
    if strict_zero_export:
        # If strict zero export is true, anything below 0 is capped at 0 (curtailed)
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        df['grid_feed_in_kw'] = 0.0
    else:
        # If export is allowed, negative net_load becomes feed-in
        df['grid_feed_in_kw'] = df['net_load_kw'].apply(lambda x: abs(x) if x < 0 else 0.0)
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        
    return df