# tests/test_energy_logic.py
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.energy_logic import simulate_battery_logic

class TestEnergyLogic(unittest.TestCase):
    def setUp(self):
        # Create a 24-hour simulation DataFrame
        # Peaky load profile (max 150 kW)
        self.df = pd.DataFrame({
            "timestamp": pd.date_range(start="2022-06-01 00:00:00", periods=24, freq="h"),
            "consumption_kw": [20.0] * 8 + [120.0, 150.0, 120.0, 80.0, 50.0, 50.0] + [20.0] * 10,
            "solar_gen_kw": [0.0] * 6 + [10.0, 30.0, 60.0, 80.0, 90.0, 80.0, 50.0, 20.0, 10.0, 0.0] + [0.0] * 8,
            "net_load_kw": [20.0] * 6 + [10.0, 90.0, 90.0, 70.0, -40.0, -30.0, 0.0, 30.0, 10.0, 20.0] + [20.0] * 8,
            "temp_c": [20.0] * 24 # Standard 20C (optimal zone)
        })

    def test_battery_soc_limits(self):
        # Basic battery setup
        bat_params = {
            "b_cap": 100.0,
            "b_pwr": 50.0,
            "shaving_threshold": 80.0,
            "charge_pwr_limit": 20.0,
            "charge_start_hour": 22,
            "charge_end_hour": 6,
            "green_charging": False,
            "efficiency": 90.0,
            "initial_soc_pct": 50.0,
            "min_soc_pct": 10.0,
            "max_soc_pct": 90.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(self.df, 100.0, bat_params, res=60)
        
        # Verify columns exist
        self.assertIn("battery_action_kw", res_df.columns)
        self.assertIn("battery_soc_kwh", res_df.columns)
        self.assertIn("final_grid_load_kw", res_df.columns)
        
        # Verify min/max limits are strictly maintained (10 kWh to 90 kWh)
        for val in res_df["battery_soc_kwh"]:
            self.assertTrue(10.0 - 1e-5 <= val <= 90.0 + 1e-5, f"SoC value {val} out of bounds")

    def test_temperature_capacity_retention(self):
        # Hot temperature: 45C (10C deviation above 35C)
        # Expected retention capacity = 100 - (10 * 0.5%) = 95%
        # Safe SoC limits scale accordingly to (9.5 kWh to 85.5 kWh)
        hot_df = self.df.copy()
        hot_df["temp_c"] = 45.0
        
        bat_params = {
            "b_cap": 100.0,
            "b_pwr": 50.0,
            "shaving_threshold": 80.0,
            "charge_pwr_limit": 20.0,
            "charge_start_hour": 22,
            "charge_end_hour": 6,
            "green_charging": False,
            "efficiency": 90.0,
            "initial_soc_pct": 50.0,
            "min_soc_pct": 10.0,
            "max_soc_pct": 90.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(hot_df, 100.0, bat_params, res=60)
        
        for val in res_df["battery_soc_kwh"]:
            # Max capacity should be throttled to 95.0 kWh, so max soc is 95 * 0.9 = 85.5 kWh
            self.assertTrue(val <= 85.5 + 1e-5, f"SoC value {val} exceeded hot capacity limit 85.5 kWh")

    def test_green_charging_constraint(self):
        # With green charging = True, battery charges ONLY when solar surplus exists (net_load_kw < 0)
        bat_params = {
            "b_cap": 100.0,
            "b_pwr": 50.0,
            "shaving_threshold": 80.0,
            "charge_pwr_limit": 20.0,
            "charge_start_hour": 0, # Allowed to charge anytime
            "charge_end_hour": 23,
            "green_charging": True, # BUT restricted to green only
            "efficiency": 90.0,
            "initial_soc_pct": 10.0, # Empty
            "min_soc_pct": 10.0,
            "max_soc_pct": 90.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(self.df, 100.0, bat_params, res=60)
        
        # Verify that battery charging (action < 0) only occurs during solar surplus (index 10, 11 where solar gen is high)
        for idx, row in res_df.iterrows():
            if row["battery_action_kw"] < 0: # Battery is charging
                self.assertLess(row["net_load_kw"], 0, f"Charged at index {idx} without solar surplus")

if __name__ == "__main__":
    unittest.main()
