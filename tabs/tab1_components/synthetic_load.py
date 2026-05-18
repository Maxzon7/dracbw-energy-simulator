import streamlit as st
import pandas as pd
import numpy as np

# ==========================================
# 1. BERECHNUNGSLOGIK (Intern für Tab 1)
# ==========================================
def synthetic_load(annual_consumption: float, 
                                     base_load_pct: int, 
                                     peak_multiplier: float, 
                                     operation_hours: str, 
                                     weekend_operation: bool, 
                                     peak_hours: list,
                                     year: int = 2024) -> pd.DataFrame:
    """
    Generiert ein 15-Minuten-Lastprofil. 
    Wird intern von der Tab 1 UI aufgerufen.
    """
    timestamps = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31 23:45:00', freq='15min')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    if operation_hours == "8h (Day shift)":
        op_mask = (df['hour'] >= 8) & (df['hour'] < 16)
    elif operation_hours == "16h (Two shifts)":
        op_mask = (df['hour'] >= 6) & (df['hour'] < 22)
    else: 
        op_mask = pd.Series([True] * len(df))
        
    profile[op_mask] = 1.0
    
    if not weekend_operation:
        weekend_mask = df['dayofweek'] >= 5
        profile[weekend_mask] = base_factor

    for ph in peak_hours:
        try:
            start_h = int(ph.split(':')[0])
            end_h = int(ph.split('-')[1].split(':')[0])
            peak_mask = (df['hour'] >= start_h) & (df['hour'] < end_h)
            
            active_peak = peak_mask & op_mask
            if not weekend_operation:
                active_peak = active_peak & (df['dayofweek'] < 5)
                
            profile[active_peak] *= peak_multiplier
        except Exception:
            continue 
            
    # Leichtes Rauschen für Realismus
    noise = np.random.normal(1.0, 0.05, len(profile))
    profile = profile * noise
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Auf Ziel-Jahresverbrauch normieren
    current_annual_energy = np.sum(profile) / 4.0
    scaling_factor = annual_consumption / current_annual_energy
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    
    return df