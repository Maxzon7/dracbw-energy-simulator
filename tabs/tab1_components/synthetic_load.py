import pandas as pd
import numpy as np

def synthetic_load(monthly_consumption: float, 
                   days_per_week: int, 
                   hours_per_day: int, 
                   base_load_pct: int = 15,
                   year: int = 2026,
                   month: int = 1) -> pd.DataFrame:
    """
    Generates a 15-minute load profile based on monthly consumption,
    working days, and working hours for a SINGLE MONTH.
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
    
    # Add some realistic noise (+/- 5%)
    noise = np.random.normal(1.0, 0.05, len(profile))
    profile = profile * noise
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Normalize to TARGET MONTHLY CONSUMPTION
    current_monthly_energy = np.sum(profile) / 4.0
    scaling_factor = monthly_consumption / current_monthly_energy
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    
    return df