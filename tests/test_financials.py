# tests/test_financials.py
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabs.tab3_components.financial_engine import generate_15_year_cashflow

# Simple mock classes to replicate data models without unpickling dependency
class MockFinancials:
    def __init__(self):
        self.lifespan_years = 15
        self.capex = 50000.0
        self.opex_yearly = 1000.0
        self.inflation_rate = 0.02
        self.energy_price_growth = 0.04

class MockTariff:
    def __init__(self):
        self.fixed_costs_per_year = 500.0
        self.price_per_kwh = 0.20
        self.price_per_kw_peak = 80.0

class MockBaseScenario:
    def __init__(self, df):
        self.original_profile = df
        self.base_tariff = MockTariff()
        self.metadata = {
            "financial_metadata": {
                "feed_in_tariff": 0.08,
                "diesel_price": 1.50
            }
        }

class MockSubScenario:
    def __init__(self, df, tech_params):
        self.financials = MockFinancials()
        self.simulated_profile = df
        self.tech_params = tech_params
        self.custom_tariff = None # Defaults to base tariff

class TestFinancialEngine(unittest.TestCase):
    def setUp(self):
        # 24-hour timestamps
        self.times = pd.date_range(start="2022-06-01 00:00:00", periods=24, freq="h")
        
        # Mock baseline profile
        self.base_df = pd.DataFrame({
            "timestamp": self.times,
            "consumption_kw": [50.0] * 24 # Constant 50 kW load
        })
        
        # Mock sub-scenario profile (with PV + Battery)
        self.sub_df = pd.DataFrame({
            "timestamp": self.times,
            "consumption_kw": [50.0] * 24,
            "solar_gen_kw": [0.0] * 6 + [30.0] * 12 + [0.0] * 6,
            "battery_action_kw": [0.0] * 24,
            "final_grid_load_kw": [50.0] * 6 + [20.0] * 12 + [50.0] * 6, # Shaved by PV during daytime
            "grid_feed_in_kw": [0.0] * 24,
            "generator_fuel_l": [0.0] * 24
        })

    def test_cashflow_generation(self):
        # Configure technology params
        tech_params = {
            "solar": {
                "degradation_pct": 0.5
            },
            "battery": {
                "replacement_year": 10,
                "replacement_pct": 100.0,
                "total_storage_capex": 20000.0
            }
        }
        
        base_scenario = MockBaseScenario(self.base_df)
        sub_scenario = MockSubScenario(self.sub_df, tech_params)
        
        df_cf = generate_15_year_cashflow(sub_scenario, base_scenario)
        
        # Checks
        self.assertIsNotNone(df_cf)
        self.assertEqual(len(df_cf), 16) # Year 0 to 15 (16 rows)
        self.assertIn("Year", df_cf.columns)
        self.assertIn("CAPEX (€)", df_cf.columns)
        self.assertIn("OPEX (€)", df_cf.columns)
        self.assertIn("Grid Savings (€)", df_cf.columns)
        self.assertIn("Net Cashflow (€)", df_cf.columns)
        self.assertIn("Cumulative Cashflow (€)", df_cf.columns)
        
        # Year 0 capex check
        self.assertEqual(df_cf.loc[df_cf["Year"] == 0, "CAPEX (€)"].values[0], -50000.0)
        
        # Battery replacement capex spike check in Year 10
        # Expected: total_storage_capex * inflation compounding for 10 years: 20000 * (1.02)^9 = ~23901.85
        # Since Year 10 replace matches year == 10
        # Check that Year 10 capex column has replacement value
        repl_capex = df_cf.loc[df_cf["Year"] == 10, "CAPEX (€)"].values[0]
        self.assertLess(repl_capex, 0.0) # Capex is negative outflow
        self.assertAlmostEqual(repl_capex, -20000.0 * (1.02**9), delta=100.0)
        
        # Compounding Solar PV degradation checks
        # Net savings should decline over the years (excluding inflation impact)
        # Year 1 savings vs Year 2 savings: Year 2 should apply 0.5% degradation penalty
        sav_y1 = df_cf.loc[df_cf["Year"] == 1, "Grid Savings (€)"].values[0]
        sav_y2 = df_cf.loc[df_cf["Year"] == 2, "Grid Savings (€)"].values[0]
        
        # Check that degradation was compounded using the electricity tariff growth rate (energy_price_growth = 4%)
        expected_sav_y2 = sav_y1 * (1 + 0.04) * (1 - 0.005) # energy escalation=4%, degradation=0.5%
        self.assertAlmostEqual(sav_y2, expected_sav_y2, delta=1e-3)

    def test_irr_calculation(self):
        from tabs.tab3_components.financial_engine import calculate_irr
        # Cashflow: invest 100, return 25 for 5 years. Expected IRR ~ 7.93%
        cfs = [-100.0, 25.0, 25.0, 25.0, 25.0, 25.0]
        irr = calculate_irr(cfs)
        self.assertAlmostEqual(irr, 0.079308, delta=1e-4)
        
        # Unfeasible scenario with no sign change (no positive returns)
        self.assertEqual(calculate_irr([-100.0, -20.0, -10.0]), -1.0)

if __name__ == "__main__":
    unittest.main()
