# tabs/tab2_components/solar_logic.py
import pandas as pd
import numpy as np
import streamlit as st
import requests

def get_transposition_factor(country: str, tilt: str, azimuth: str) -> float:
    """
    Returns the performance multiplier based on panel orientation and tilt.
    Extracts logic from standard CF-Documents (Transposition Matrices).
    """
    if "Argentina" in country:
        if azimuth == "North (0°)" and tilt == "30°": return 1.15
        if azimuth == "North (0°)" and tilt == "15°": return 1.08
        if azimuth in ["East (90°)", "West (270°)"]: return 0.95
        return 0.85
    else:
        if azimuth == "South (180°)" and tilt == "30°": return 1.12
        if azimuth == "South (180°)" and tilt == "15°": return 1.05
        if azimuth in ["East (90°)", "West (270°)"]: return 0.90
        return 0.80

def generate_solar_profile(baseline_df: pd.DataFrame, project_metadata: dict, solar_params: dict) -> pd.DataFrame:
    """
    Layer 2 & 3: Fetches real-world historical satellite solar radiation data (GHI) live 
    from the Open-Meteo Archive API based on project coordinates and computes the energy matrix.
    """
    df = baseline_df.copy()
    
    # Extract geographical configurations from top-level metadata
    lat = project_metadata.get('latitude', 52.3676)
    lon = project_metadata.get('longitude', 4.9041)
    country = project_metadata.get('country', "Netherlands 🇳🇱")
    strict_zero_export = project_metadata.get('strict_zero_export', False)
    
    # Extract hardware specifications
    kwp = solar_params.get('installed_kwp', 0.0)
    pr = solar_params.get('performance_ratio', 85.0) / 100.0
    tilt = solar_params.get('tilt', "30°")
    azimuth = solar_params.get('azimuth', "South (180°)")
    thermal_loss_active = solar_params.get('thermal_loss', True)
    
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    start_date = df['timestamp'].min().strftime("%Y-%m-%d")
    end_date = df['timestamp'].max().strftime("%Y-%m-%d")
    
    # 1. Fetch Live Satellite Weather Data from Open-Meteo
    try:
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}&"
            f"start_date={start_date}&end_date={end_date}&"
            f"hourly=shortwave_radiation"
        )
        response = requests.get(url, timeout=10).json()
        
        hourly_times = pd.to_datetime(response['hourly']['time'])
        hourly_rad = response['hourly']['shortwave_radiation']  # W/m²
        
        hourly_df = pd.DataFrame({'ghi_w_m2': hourly_rad}, index=hourly_times)
        
        # 2. Linear Resolution Upsampling (Hourly -> 15-Minute Load Profile Grid)
        upsampled_df = hourly_df.resample('15min').interpolate(method='linear')
        
        # Map values exactly onto the baseline timestamps
        df.set_index('timestamp', drop=False, inplace=True)
        df['ghi_w_m2'] = upsampled_df.reindex(df.index, method='ffill')['ghi_w_m2'].fillna(0.0)
        df.reset_index(drop=True, inplace=True)
        
    except Exception as api_error:
        st.warning(f"⚠️ Live Solar API offline ({api_error}). Falling back to randomized cloud baseline.")
        hours = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
        df['ghi_w_m2'] = np.maximum(1 - ((hours - 12.0) / 6.0)**2, 0) * 500.0
        
    # 3. Apply Tilt Transposition Multipliers
    transposition = get_transposition_factor(country, tilt, azimuth)
    
    # Math: Capacity(kWp) * (GHI / STC Standard 1000 W/m²) * transposition * system_efficiency
    df['solar_gen_kw'] = kwp * (df['ghi_w_m2'] / 1000.0) * transposition * pr
    
    # 4. Apply Thermal Midday Losses if enabled
    if thermal_loss_active:
        midday_mask = (df['timestamp'].dt.hour >= 11) & (df['timestamp'].dt.hour <= 15)
        summer_months = [12, 1, 2] if "Argentina" in country else [6, 7, 8]
        season_mask = df['timestamp'].dt.month.isin(summer_months)
        df.loc[midday_mask & season_mask, 'solar_gen_kw'] *= 0.95
        
    # 5. Energy Balance Matrix Calculations
    df['net_load_kw'] = df['consumption_kw'] - df['solar_gen_kw']
    
    if strict_zero_export:
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        df['grid_feed_in_kw'] = 0.0
    else:
        df['grid_feed_in_kw'] = df['net_load_kw'].apply(lambda x: abs(x) if x < 0 else 0.0)
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        
    return df