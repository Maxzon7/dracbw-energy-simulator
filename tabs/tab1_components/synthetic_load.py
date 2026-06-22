import pandas as pd
import numpy as np

def synthetic_load(monthly_consumption: float, 
                   days_per_week: int, 
                   hours_per_day: int, 
                   base_load_pct: int = 15,
                   year: int = 2026,
                   month: int = 1,
                   noise_enabled: bool = False,
                   noise_percentage: float = 5.0) -> pd.DataFrame:
    """
    Generates a 15-minute load profile based on monthly consumption,
    working days, and working hours for a SINGLE MONTH.
    Features optional user-controlled Gaussian fluctuations.
    """
    # Start and End Date for the specific month
    start_date = f'{year}-{month:02d}-01'
    end_date = (pd.to_datetime(start_date) + pd.offsets.MonthEnd(1)).strftime('%Y-%m-%d')
    
    # Generate timestamps for one month
    timestamps = pd.date_range(start=start_date, end=f'{end_date} 23:45:00', freq='15min')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    # Base load factor (e.g. 15% running during nights/weekends)
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    # Operation mask
    start_hour = 8
    end_hour = start_hour + hours_per_day
    
    if end_hour > 24:
        # Crosses midnight
        op_mask = (df['hour'] >= start_hour) | (df['hour'] < (end_hour % 24))
    else:
        op_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
        
    if hours_per_day == 24:
        op_mask = pd.Series([True] * len(df))
        
    # Working days mask (0 = Monday, 6 = Sunday)
    working_days_mask = df['dayofweek'] < days_per_week
    
    # Apply full load only on working days during working hours
    active_mask = op_mask & working_days_mask
    profile[active_mask] = 1.0
    
    # --- NOISE GENERATION ---
    if noise_enabled:
        # Converts percentage (e.g., 5%) into standard deviation (0.05)
        std_dev = noise_percentage / 100.0
        noise = np.random.normal(1.0, std_dev, len(profile))
        profile = profile * noise
    
    # Secure the lower boundary to prevent negative loads
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # --- THE FIX: 30-DAY STANDARD MONTH CALIBRATION ---
    # Calculate the exact mathematical days in this specific month
    actual_days_in_month = len(df) / (24 * 4)
    
    # Adjust the target consumption to a 30-day standard. 
    # Example: February (28 days) will get 28/30 of the inputted monthly consumption.
    # This ensures kW peaks remain identical across all months regardless of length.
    adjusted_monthly_consumption = monthly_consumption * (actual_days_in_month / 30.0)
    
    # Normalize the profile based on the adjusted energy target (Power / 4 = Energy per 15-min)
    current_monthly_energy = np.sum(profile) / 4.0
    scaling_factor = adjusted_monthly_consumption / current_monthly_energy
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    
    return df