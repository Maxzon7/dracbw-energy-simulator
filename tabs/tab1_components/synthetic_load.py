import pandas as pd
import numpy as np

def synthetic_load(monthly_consumption: float, 
                   days_per_week: int, 
                   hours_per_day: int, 
                   base_load_pct: int = 15,
                   year: int = 2026) -> pd.DataFrame:
    """
    Generiert ein 15-Minuten-Lastprofil basierend auf monatlichem Verbrauch,
    Arbeitstagen und Arbeitsstunden.
    """
    # Auf das Jahr hochrechnen
    annual_consumption = monthly_consumption * 12.0
    
    timestamps = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31 23:45:00', freq='15min')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    # Grundlast-Faktor (z.B. 15% laufen auch nachts/am Wochenende für Server, Kühlung etc.)
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    # Operations-Maske: Wir nehmen an, eine typische Schicht startet um 08:00 Uhr
    start_hour = 8
    end_hour = start_hour + hours_per_day
    
    if end_hour > 24:
        # Falls über Mitternacht hinaus gearbeitet wird
        op_mask = (df['hour'] >= start_hour) | (df['hour'] < (end_hour % 24))
    else:
        op_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
        
    if hours_per_day == 24:
        op_mask = pd.Series([True] * len(df))
        
    # Arbeitstage-Maske (0 = Montag, 6 = Sonntag)
    working_days_mask = df['dayofweek'] < days_per_week
    
    # Kombinieren: Nur an Arbeitstagen während der Arbeitszeit ist Volllast
    active_mask = op_mask & working_days_mask
    
    # Profil in den aktiven Zeiten auf 100% (1.0) setzen
    profile[active_mask] = 1.0
    
    # Leichtes Rauschen (Noise) für Realismus hinzufügen
    noise = np.random.normal(1.0, 0.05, len(profile))
    profile = profile * noise
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Auf Ziel-Verbrauch normieren (Leistung / 4 = Energie für 15-Min-Intervalle)
    current_annual_energy = np.sum(profile) / 4.0
    scaling_factor = annual_consumption / current_annual_energy
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    
    return df