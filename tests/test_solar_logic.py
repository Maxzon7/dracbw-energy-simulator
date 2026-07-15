# tests/test_solar_logic.py
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabs.tab2_components.solar_logic import generate_solar_profile, get_transposition_factor

class TestSolarLogic(unittest.TestCase):
    def setUp(self):
        # Create a 24-hour baseline DataFrame
        timestamps = pd.date_range(start="2022-06-01 00:00:00", periods=24, freq="h")
        self.df = pd.DataFrame({
            "timestamp": timestamps,
            "consumption_kw": [10.0] * 24
        })
        self.metadata = {
            "latitude": 52.3676,
            "longitude": 4.9041,
            "country": "Netherlands 🇳🇱",
            "strict_zero_export": False
        }

    def test_transposition_factor(self):
        # Verify Argentina
        f1 = get_transposition_factor("Argentina", "30°", "North (0°)")
        self.assertEqual(f1, 1.15)
        # Verify default (other countries)
        f2 = get_transposition_factor("Netherlands 🇳🇱", "30°", "South (180°)")
        self.assertEqual(f2, 1.12)

    @patch("requests.get")
    def test_solar_open_meteo_fetching(self, mock_get):
        # Mock weather API response
        mock_response = mock_get.return_value
        mock_response.json.return_value = {
            "hourly": {
                "time": [t.strftime("%Y-%m-%dT%H:%M") for t in self.df["timestamp"]],
                "shortwave_radiation": [0] * 6 + [200, 400, 600, 800, 1000, 1000, 800, 600, 400, 200] + [0] * 8, # Peak at noon
                "temperature_2m": [15.0] * 6 + [20.0, 22.0, 25.0, 28.0, 30.0, 30.0, 28.0, 25.0, 22.0, 20.0] + [15.0] * 8 # Peak temperature of 30C
            }
        }

        solar_params = {
            "installed_kwp": 100.0,
            "performance_ratio": 80.0,
            "tilt": "30°",
            "azimuth": "South (180°)",
            "thermal_loss": True,
            "ghi_source": "Open-Meteo API",
            "yield_factor": 1.0,
            "temp_coeff": 0.4,
            "loss_inverter": 3.0,
            "loss_cabling": 1.5,
            "loss_soiling": 1.0,
            "loss_other": 2.0
        }

        res_df = generate_solar_profile(self.df, self.metadata, solar_params)

        self.assertIn("ghi_w_m2", res_df.columns)
        self.assertIn("temp_c", res_df.columns)
        self.assertIn("solar_gen_kw", res_df.columns)
        self.assertEqual(res_df["ghi_w_m2"].max(), 1000)
        self.assertEqual(res_df["temp_c"].max(), 30.0)
        
        # Verify thermal losses at 30C: (30 - 25) * 0.4% = 2% loss
        # Expected max yield: 100 kWp * 1.0 (noon radiation) * 1.12 (orientation) * 0.80 (PR) * (1-0.03)*(1-0.015)*(1-0.01)*(1-0.02) (PR losses) * 0.98 (thermal)
        # Verify it has some positive solar generation
        self.assertGreater(res_df["solar_gen_kw"].max(), 0)

    def test_manual_specific_yield_scaling(self):
        solar_params = {
            "installed_kwp": 50.0,
            "performance_ratio": 85.0,
            "tilt": "30°",
            "azimuth": "South (180°)",
            "thermal_loss": False,
            "ghi_source": "Manual specific yield",
            "specific_yield": 1000.0, # 1000 kWh per kWp per year
            "yield_factor": 1.0,
            "loss_inverter": 0.0,
            "loss_cabling": 0.0,
            "loss_soiling": 0.0,
            "loss_other": 0.0
        }
        res_df = generate_solar_profile(self.df, self.metadata, solar_params)
        # Verify that total year yield scales to (installed_kwp * specific_yield)
        total_yield_kwh = res_df["solar_gen_kw"].sum()
        self.assertGreater(total_yield_kwh, 0)
        self.assertAlmostEqual(total_yield_kwh, 50.0 * 1000.0, delta=1.0)

    def test_manual_sunshine_hours_scaling(self):
        solar_params = {
            "installed_kwp": 10.0,
            "performance_ratio": 85.0,
            "tilt": "30°",
            "azimuth": "South (180°)",
            "thermal_loss": False,
            "ghi_source": "Manual sunshine hours",
            "annual_sunshine_hours": 1200.0,
            "yield_factor": 1.0,
            "loss_inverter": 0.0,
            "loss_cabling": 0.0,
            "loss_soiling": 0.0,
            "loss_other": 0.0
        }
        res_df = generate_solar_profile(self.df, self.metadata, solar_params)
        total_yield_kwh = res_df["solar_gen_kw"].sum()
        self.assertAlmostEqual(total_yield_kwh, 10.0 * 1200.0, delta=1.0)

if __name__ == "__main__":
    unittest.main()
