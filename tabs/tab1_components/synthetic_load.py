# tabs/tab1_components/synthetic_load.py
import pandas as pd
import numpy as np
import streamlit as st

def render_synthetic_load_ui(active_scenario: str) -> dict:
    st.write("### 🎛️ Synthetic Load Generator")
    st.info("Define the operational characteristics of the facility to generate a simulated 15-minute load profile.")
    
    c1, c2, c3 = st.columns(3)
    monthly_consumption = c1.number_input("Avg. Monthly Consumption (kWh)", value=50000, step=1000, key=f"syn_cons_{active_scenario}")
    days_per_week = c2.number_input("Working Days / Week", min_value=1, max_value=7, value=5, key=f"syn_days_{active_scenario}")
    hours_per_day = c3.number_input("Working Hours / Day", min_value=1, max_value=24, value=12, key=f"syn_hours_{active_scenario}")
    
    c4, c5, c6 = st.columns(3)
    base_load_pct = c4.number_input("Base Load (%)", min_value=0, max_value=100, value=15, help="Energy consumption during nights/weekends.", key=f"syn_base_{active_scenario}")
    noise_enabled = c5.checkbox("Add Random Fluctuations (Noise)", value=True, key=f"syn_noise_en_{active_scenario}")
    noise_percentage = c6.number_input("Noise Level (%)", min_value=0.0, max_value=100.0, value=5.0, step=1.0, disabled=not noise_enabled, key=f"syn_noise_pct_{active_scenario}")
    
    return {
        "monthly_consumption": monthly_consumption,
        "days_per_week": days_per_week,
        "hours_per_day": hours_per_day,
        "base_load_pct": base_load_pct,
        "noise_enabled": noise_enabled,
        "noise_percentage": noise_percentage
    }

def synthetic_load(monthly_consumption: float, 
                   days_per_week: int, 
                   hours_per_day: int, 
                   base_load_pct: int = 15,
                   year: int = 2026,
                   noise_enabled: bool = False,
                   noise_percentage: float = 5.0) -> pd.DataFrame:
    """
    Original logic: Generates a FULL YEAR 15-minute load profile based purely 
    on working days, hours, and standard noise.
    """
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    timestamps = pd.date_range(start=start_date, end=f'{end_date} 23:45:00', freq='15min')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    start_hour = 8
    end_hour = start_hour + hours_per_day
    
    if end_hour > 24:
        op_mask = (df['hour'] >= start_hour) | (df['hour'] < (end_hour % 24))
    else:
        op_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
        
    if hours_per_day == 24:
        op_mask = pd.Series([True] * len(df))
        
    working_days_mask = df['dayofweek'] < days_per_week
    active_mask = op_mask & working_days_mask
    profile[active_mask] = 1.0
    
    if noise_enabled:
        std_dev = noise_percentage / 100.0
        noise = np.random.normal(1.0, std_dev, len(profile))
        profile = profile * noise
    
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Scale to full year target
    annual_target_kwh = monthly_consumption * 12.0
    current_annual_energy = np.sum(profile) / 4.0
    scaling_factor = annual_target_kwh / current_annual_energy
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    
    return df