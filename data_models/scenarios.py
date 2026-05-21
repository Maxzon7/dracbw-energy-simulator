from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd

@dataclass
class AnomalyConfig:
    """Stores the exact UI configuration of a single anomaly."""
    id: str
    anomaly_type: str        # 'additional_load', 'fixed_value', 'reduction'
    value_kw: float          # The slider value (e.g., 80.0)
    frequency_type: str      # 'regular', 'block', 'random'
    start_time: str          # e.g., '08:00'
    end_time: str            # e.g., '14:00'
    
    # Frequency specific settings (empty by default, filled based on frequency_type)
    regular_days: List[str] = field(default_factory=list)     # e.g., ['Monday', 'Wednesday']
    block_start_date: Optional[str] = None                    # e.g., '2025-07-01'
    block_end_date: Optional[str] = None                      # e.g., '2025-07-21'
    random_dates: List[str] = field(default_factory=list)     # e.g., ['2025-03-14', '2025-09-24']

@dataclass
class ScenarioConfig:
    """The master container holding all parameters, overrides, and the final dataframe."""
    scenario_name: str
    baseline_name: str
    technology_mode: str     # 'Solar PV', 'Battery (Peak Shaving)', etc.
    
    # The global slider positions (Part A of our concept)
    global_params: dict = field(default_factory=dict)         # e.g., {'solar_kwp': 150, 'bat_cap': 200}
    
    # The monthly slider exceptions
    monthly_overrides: dict = field(default_factory=dict)     # e.g., {'August': {'base_load': 0.05}}
    
    # The list of applied anomalies
    anomalies: List[AnomalyConfig] = field(default_factory=list)
    
    # The calculated resulting data (Part B of our concept)
    result_df: Optional[pd.DataFrame] = None

class BaselineScenario:
    def __init__(self, monthly_consumption, days_per_week, hours_per_day, num_connections, amperage, enable_noise, noise_percentage):
        #user input
        self.monthly_consumption = monthly_consumption
        self.days_per_week = days_per_week
        self.hours_per_day = hours_per_day
        
        self.num_connections = num_connections
        self.amperage = amperage
        
        self.enable_noise = enable_noise
        self.noise_percentage = noise_percentage
        
        # profile is empty in the beginning, will get filled after the calcualtion
        self.load_profile = None