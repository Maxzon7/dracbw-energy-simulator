# tests/test_base_scenarios.py
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.energy_logic import simulate_battery_logic

class TestBaseScenarios(unittest.TestCase):
    def setUp(self):
        # 24-hour timestamps
        self.times = pd.date_range(start="2022-06-01 00:00:00", periods=24, freq="h")
        
        # 1. Baseload A (Low peak load: 50 kW)
        self.profile_a = pd.DataFrame({
            "timestamp": self.times,
            "consumption_kw": [30.0] * 8 + [50.0] * 6 + [30.0] * 10,
            "solar_gen_kw": [0.0] * 24,
            "net_load_kw": [30.0] * 8 + [50.0] * 6 + [30.0] * 10,
            "temp_c": [20.0] * 24
        })
        
        # 2. Baseload B (High peak load: 150 kW)
        # Peak peak load at 9:00 (150 kW), 10:00 (120 kW)
        self.profile_b = pd.DataFrame({
            "timestamp": self.times,
            "consumption_kw": [20.0] * 8 + [150.0, 120.0, 100.0, 60.0] + [20.0] * 12,
            "solar_gen_kw": [0.0] * 24,
            "net_load_kw": [20.0] * 8 + [150.0, 120.0, 100.0, 60.0] + [20.0] * 12,
            "temp_c": [20.0] * 24
        })

    def run_feasibility_check(self, results, grid_limit, bat_params):
        """Replicates feasibility_check.py evaluation logic programmatically for test assertion."""
        peak_new = results["final_grid_load_kw"].max()
        b_cap = bat_params.get("b_cap", 0.0)
        max_discharge = results.get("battery_action_kw", pd.Series([0.0])).max()
        c_rate = (max_discharge / b_cap) if b_cap > 0 else 0.0
        
        if peak_new > (grid_limit + 0.1):
            return "NOT_FEASIBLE_GRID_BREACH"
        elif c_rate > 1.2:
            return "HIGH_RISK_C_RATE"
        else:
            return "FEASIBLE"

    def test_baseload_a_native_feasibility(self):
        # Baseload A has peak of 50 kW, grid limit is 60 kW.
        # No battery needed, natively feasible!
        results = self.profile_a.copy()
        results["final_grid_load_kw"] = results["consumption_kw"]
        status = self.run_feasibility_check(results, grid_limit=60.0, bat_params={})
        self.assertEqual(status, "FEASIBLE")

    def test_sub_scenario_b1_feasible(self):
        # Baseload B (150 kW peak, 100 kW grid limit).
        # We shave with a large battery: 150 kWh capacity, 60 kW inverter power
        bat_params = {
            "b_cap": 150.0,
            "b_pwr": 60.0,
            "shaving_threshold": 95.0, # Shave below 100 kW grid limit
            "charge_pwr_limit": 20.0,
            "charge_start_hour": 22,
            "charge_end_hour": 6,
            "green_charging": False,
            "efficiency": 90.0,
            "initial_soc_pct": 80.0, # Sufficient charge
            "min_soc_pct": 10.0,
            "max_soc_pct": 90.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(self.profile_b, 100.0, bat_params, res=60)
        
        status = self.run_feasibility_check(res_df, grid_limit=100.0, bat_params=bat_params)
        
        # Verify optimized peak grid load is shaved below connection limit
        self.assertLessEqual(res_df["final_grid_load_kw"].max(), 100.0)
        # Verify battery discharge C-rate is safe (max discharge kW / b_cap <= 1.2)
        max_discharge = res_df["battery_action_kw"].max()
        self.assertLessEqual(max_discharge / bat_params["b_cap"], 1.2)
        self.assertEqual(status, "FEASIBLE")

    def test_sub_scenario_b2_unfeasible_grid_breach(self):
        # Baseload B (150 kW peak, 100 kW grid limit).
        # We try to shave with a tiny battery: 10 kWh capacity, 10 kW inverter power.
        # Deficit is 50 kW, so a 10 kW inverter cannot shave it down enough.
        bat_params = {
            "b_cap": 10.0,
            "b_pwr": 10.0,
            "shaving_threshold": 95.0,
            "charge_pwr_limit": 5.0,
            "charge_start_hour": 22,
            "charge_end_hour": 6,
            "green_charging": False,
            "efficiency": 90.0,
            "initial_soc_pct": 90.0,
            "min_soc_pct": 10.0,
            "max_soc_pct": 90.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(self.profile_b, 100.0, bat_params, res=60)
        
        status = self.run_feasibility_check(res_df, grid_limit=100.0, bat_params=bat_params)
        
        # Optimized peak should still breach connection limit (150 kW peak - 10 kW battery = 140 kW, which is > 100 kW)
        self.assertGreater(res_df["final_grid_load_kw"].max(), 100.0)
        self.assertEqual(status, "NOT_FEASIBLE_GRID_BREACH")

    def test_sub_scenario_b3_unfeasible_crate_stress(self):
        # Baseload B (150 kW peak, 100 kW grid limit).
        # We simulate with a 15-minute resolution to model a short peak.
        # Battery capacity: 20 kWh, Inverter power: 60 kW.
        # Usable capacity = 20 * (95 - 10) / 100 = 17 kWh.
        # Short peak of 150 kW for 15 mins (deficit: 55 kW) requires 13.75 kWh, so it won't deplete.
        # Peak grid load is shaved below 100 kW, but max discharge is 55 kW.
        # C-rate = 55 / 20 = 2.75C, exceeding the 1.2C stress limit.
        profile_b_15m = self.profile_b.set_index("timestamp").resample("15min").ffill().reset_index()
        profile_b_15m.loc[profile_b_15m["timestamp"] == "2022-06-01 08:00:00", "consumption_kw"] = 150.0
        # Set all other intervals to 20.0 kW
        profile_b_15m.loc[profile_b_15m["timestamp"] != "2022-06-01 08:00:00", "consumption_kw"] = 20.0
        profile_b_15m["net_load_kw"] = profile_b_15m["consumption_kw"]
        
        bat_params = {
            "b_cap": 20.0,
            "b_pwr": 60.0,
            "shaving_threshold": 95.0,
            "charge_pwr_limit": 20.0,
            "charge_start_hour": 22,
            "charge_end_hour": 6,
            "green_charging": False,
            "efficiency": 90.0,
            "initial_soc_pct": 95.0,
            "min_soc_pct": 10.0,
            "max_soc_pct": 95.0,
            "temp_cap_coeff": 0.5
        }
        res_df = simulate_battery_logic(profile_b_15m, 100.0, bat_params, res=15)
        
        status = self.run_feasibility_check(res_df, grid_limit=100.0, bat_params=bat_params)
        
        # Grid limit is respected (peak is <= 100 kW)
        self.assertLessEqual(res_df["final_grid_load_kw"].max(), 100.0)
        # Battery C-rate is dangerously high (> 1.2C)
        max_discharge = res_df["battery_action_kw"].max()
        c_rate = max_discharge / bat_params["b_cap"]
        self.assertGreater(c_rate, 1.2)
        self.assertEqual(status, "HIGH_RISK_C_RATE")

if __name__ == "__main__":
    unittest.main()
