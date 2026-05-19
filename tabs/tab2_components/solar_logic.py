# tabs/tab2_components/solar_logic.py
import pandas as pd
import numpy as np

def generate_synthetic_solar_profile(timestamps: pd.Series, capacity_kwp: float, yield_factor: float) -> pd.Series:
    """
    Generates a basic synthetic solar generation profile (bell curve during daytime).
    Scales the 15-min intervals so that the total annual sum matches the target yield.
    """
    if capacity_kwp <= 0 or yield_factor <= 0:
        return pd.Series(np.zeros(len(timestamps)), index=timestamps.index)

    # 1. Uhrzeit als Dezimalzahl (z.B. 14:30 -> 14.5)
    hours = timestamps.dt.hour + timestamps.dt.minute / 60.0
    
    # 2. Synthetische Glockenkurve (Parabel): Peak um 12:00, Null vor 06:00 und nach 18:00
    # y = 1 - ((x - 12) / 6)^2
    solar_shape = 1 - ((hours - 12.0) / 6.0)**2
    
    # Negative Werte in der Nacht auf 0 kappen
    solar_shape = np.maximum(solar_shape, 0)
    
    # 3. Skalierung auf den Jahresertrag
    total_shape_sum = solar_shape.sum()
    target_annual_kwh = capacity_kwp * yield_factor
    
    # Da wir 15-Min-Intervalle haben, entspricht die Summe der kW-Werte * 0.25 der Energie in kWh
    # Umgestellt: Ziel-Summe(kW) = Jahresertrag(kWh) * 4
    target_sum_kw = target_annual_kwh * 4.0
    
    if total_shape_sum > 0:
        solar_kw = solar_shape * (target_sum_kw / total_shape_sum)
    else:
        solar_kw = np.zeros(len(timestamps))
        
    return pd.Series(solar_kw, index=timestamps.index)