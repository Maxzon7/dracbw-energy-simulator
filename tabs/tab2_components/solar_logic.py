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
    Layer 2 & 3: Computes solar energy matrix using either live GHI/temperature weather data
    from Open-Meteo or manual specific yield / sunshine hour models.
    Accounts for orientation, performance ratios, detailed losses, and temperature-based degradation.
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
    
    # Extra parameters
    ghi_source = solar_params.get('ghi_source', "Open-Meteo API")
    yield_factor = solar_params.get('yield_factor', 1.0)
    
    # Detailed losses
    loss_inverter = solar_params.get('loss_inverter', 0.0) / 100.0
    loss_cabling = solar_params.get('loss_cabling', 0.0) / 100.0
    loss_soiling = solar_params.get('loss_soiling', 0.0) / 100.0
    loss_other = solar_params.get('loss_other', 0.0) / 100.0
    combined_loss_factor = (1.0 - loss_inverter) * (1.0 - loss_cabling) * (1.0 - loss_soiling) * (1.0 - loss_other)
    effective_pr = pr * combined_loss_factor

    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
    start_date = df['timestamp'].min()
    end_date = df['timestamp'].max()
    
    # Estimate time-step delta hours
    if len(df) > 1:
        step_hours = (df['timestamp'].iloc[1] - df['timestamp'].iloc[0]).total_seconds() / 3600.0
    else:
        step_hours = 1.0
    
    # 1. Fetch or generate GHI and Temperature data
    if ghi_source == "Open-Meteo API":
        year_offset = start_date.year - 2022
        if year_offset > 0:
            api_start = (start_date - pd.DateOffset(years=year_offset)).strftime("%Y-%m-%d")
            api_end = (end_date - pd.DateOffset(years=year_offset)).strftime("%Y-%m-%d")
        else:
            api_start = start_date.strftime("%Y-%m-%d")
            api_end = end_date.strftime("%Y-%m-%d")
        
        try:
            # Request radiation AND temperature
            url = (
                f"https://archive-api.open-meteo.com/v1/archive?"
                f"latitude={lat}&longitude={lon}&"
                f"start_date={api_start}&end_date={api_end}&"
                f"hourly=shortwave_radiation,temperature_2m"
            )
            response = requests.get(url, timeout=10).json()
            
            if 'error' in response:
                raise ValueError(f"API error: {response.get('reason', 'Unknown error')}")
                
            hourly_times = pd.to_datetime(response['hourly']['time'])
            hourly_rad = response['hourly']['shortwave_radiation']  # W/m²
            hourly_temp = response['hourly']['temperature_2m']  # °C
            
            if year_offset > 0:
                hourly_times = hourly_times + pd.DateOffset(years=year_offset)
                
            hourly_df = pd.DataFrame({
                'ghi_w_m2': hourly_rad,
                'temp_c': hourly_temp
            }, index=hourly_times)
            
            # Upsample matching simulation resolution
            upsampled_df = hourly_df.resample('15min').interpolate(method='linear')
            
            df.set_index('timestamp', drop=False, inplace=True)
            reindexed = upsampled_df.reindex(df.index, method='ffill').fillna(0.0)
            df['ghi_w_m2'] = reindexed['ghi_w_m2']
            df['temp_c'] = reindexed['temp_c']
            df.reset_index(drop=True, inplace=True)
            
        except Exception as api_error:
            st.warning(f"⚠️ Live Weather API offline ({api_error}). Falling back to randomized cloud and temperature baseline.")
            hours = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
            df['ghi_w_m2'] = np.maximum(1.0 - ((hours - 12.0) / 6.0)**2, 0.0) * 500.0
            
            # Mock daily temperature cycle
            month = df['timestamp'].dt.month
            is_south = "Argentina" in country
            base_temp = 20.0 + 8.0 * np.cos((month - 1) / 12.0 * 2 * np.pi) if is_south else 16.0 - 10.0 * np.cos((month - 1) / 12.0 * 2 * np.pi)
            df['temp_c'] = base_temp + 5.0 * np.sin((hours - 8.0) / 24.0 * 2 * np.pi)
    else:
        # Manual yield specs or sunshine hours: generate standard clear-sky shapes
        hours = df['timestamp'].dt.hour + df['timestamp'].dt.minute / 60.0
        ghi_shape = np.maximum(1.0 - ((hours - 12.0) / 6.0)**2, 0.0) * 800.0
        
        month = df['timestamp'].dt.month
        is_south = "Argentina" in country
        peak_month = 12 if is_south else 6
        seasonal_mult = 1.0 + 0.6 * np.cos((month - peak_month) / 12.0 * 2 * np.pi)
        
        df['ghi_w_m2'] = ghi_shape * seasonal_mult
        
        # Temp fallback
        base_temp = 20.0 + 8.0 * np.cos((month - 1) / 12.0 * 2 * np.pi) if is_south else 16.0 - 10.0 * np.cos((month - 1) / 12.0 * 2 * np.pi)
        df['temp_c'] = base_temp + 5.0 * np.sin((hours - 8.0) / 24.0 * 2 * np.pi)

    # 2. Apply Tilt Transposition Multipliers
    transposition = get_transposition_factor(country, tilt, azimuth)
    
    # 3. Compute Solar Generation
    base_gen = kwp * (df['ghi_w_m2'] / 1000.0) * transposition * effective_pr
    
    # Scale generation if manual target yield is selected
    if ghi_source == "Manual specific yield":
        target_kwh = kwp * solar_params.get('specific_yield', 950.0)
        base_energy = base_gen.sum() * step_hours
        scaling = target_kwh / base_energy if base_energy > 0.0 else 1.0
        df['solar_gen_kw'] = base_gen * scaling * yield_factor
    elif ghi_source == "Manual sunshine hours":
        target_kwh = kwp * solar_params.get('annual_sunshine_hours', 1500.0)
        base_energy = base_gen.sum() * step_hours
        scaling = target_kwh / base_energy if base_energy > 0.0 else 1.0
        df['solar_gen_kw'] = base_gen * scaling * yield_factor
    else:
        df['solar_gen_kw'] = base_gen * yield_factor

    # 4. Apply Temperature Influence (Baseline: 0.25% loss per °C above 25°C)
    if thermal_loss_active:
        temp_coeff = solar_params.get('temp_coeff', 0.25) / 100.0
        temp_loss = np.maximum(0.0, (df['temp_c'] - 25.0) * temp_coeff)
        df['solar_gen_kw'] *= (1.0 - temp_loss)
        
    # 5. Energy Balance Matrix Calculations
    df['net_load_kw'] = df['consumption_kw'] - df['solar_gen_kw']
    
    if strict_zero_export:
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        df['grid_feed_in_kw'] = 0.0
    else:
        df['grid_feed_in_kw'] = df['net_load_kw'].apply(lambda x: abs(x) if x < 0 else 0.0)
        df['net_load_kw'] = df['net_load_kw'].clip(lower=0.0)
        
    return df