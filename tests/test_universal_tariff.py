# tests/test_universal_tariff.py
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Ensure the workspace root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tabs.tab3_components.financial_engine import calculate_annual_grid_bill_with_pillars

class TestUniversalMultiPillarTariff(unittest.TestCase):
    def setUp(self):
        # Create a simple 8760 hourly DataFrame with a constant consumption
        # of 10.0 kW, with two peaks in EVERY month on the 1st day:
        # 1. Pico peak of 40.0 kW at 20:00 (Pico window: 18:00 - 23:00)
        # 2. Resto peak of 50.0 kW at 12:00 (Resto window)
        times = pd.date_range(start="2026-01-01 00:00:00", periods=8760, freq="h")
        self.df = pd.DataFrame({
            "timestamp": times,
            "consumption_kw": [10.0] * 8760
        })
        
        for m in range(1, 13):
            # Pico peak
            self.df.loc[(self.df["timestamp"].dt.month == m) & 
                        (self.df["timestamp"].dt.day == 1) & 
                        (self.df["timestamp"].dt.hour == 20), "consumption_kw"] = 40.0
            # Resto peak
            self.df.loc[(self.df["timestamp"].dt.month == m) & 
                        (self.df["timestamp"].dt.day == 1) & 
                        (self.df["timestamp"].dt.hour == 12), "consumption_kw"] = 50.0

    def test_multipillar_pico_vs_absolute_peak_and_taxes(self):
        provincial_taxes = [
            {"Tax Name": "CCCE Ley 6497", "Rate (%)": 9.0},
            {"Tax Name": "Tasa fisc. y Control", "Rate (%)": 1.5},
            {"Tax Name": "Sobretasa Provincial Ley 2539", "Rate (%)": 1.0}
        ]
        
        custom_adjustments = [
            {"Charge Name": "Cargo AP Municipal", "Amount (€)": 43000.0, "Is Pre-tax": False},
            {"Charge Name": "Pre-tax Adjustment", "Amount (€)": 5000.0, "Is Pre-tax": True},
            {"Charge Name": "Adjustment Net Credit", "Amount (€)": -10000.0, "Is Pre-tax": False}
        ]
        
        monthly_schedule = {}
        for m in range(1, 13):
            monthly_schedule[str(m)] = {
                "base_fee": 100.0,
                "contracted_capacity_kw": 30.0,
                "contracted_capacity_price": 5.0,
                "peak_penalty_price": 2.0,
                "excess_penalty_price": 10.0,
                "enable_tou": True,
                "alta": {"price": 0.20, "start_hour": 18, "end_hour": 23},
                "baja": {"price": 0.10, "start_hour": 23, "end_hour": 5},
                "resto": {"price": 0.15},
                "tax_pct": 27.0,
                "provincial_taxes": provincial_taxes,
                "custom_adjustments": custom_adjustments,
                "subsidy_amount": 0.0,
                "stabilization_credit": 0.0
            }
            
        fin_params = {
            "monthly_tariff_schedule": monthly_schedule
        }
        
        # Calculate expected annual cost programmatically to account for real calendar monthly hours:
        expected_annual_gross = 0.0
        
        for m in range(1, 13):
            # Filter days for this month
            m_mask = self.df["timestamp"].dt.month == m
            m_df = self.df[m_mask]
            
            # Net capacity costs
            m_fixed = 100.0
            m_capacity = 30.0 * 5.0 # contracted kw * contracted price = 150.0
            
            # Measured Pico Peak
            pico_peak = 40.0 # set in setUp
            m_peak_penalty = pico_peak * 2.0 # 80.0
            
            # Excess absolute peak
            abs_peak = 50.0
            m_excess = (abs_peak - 30.0) * 10.0 # 200.0
            
            # Energy cost
            # Count hours in Pico (18-23h), Valle (23-5h), Resto (other)
            hours = m_df["timestamp"].dt.hour
            is_alta = (hours >= 18) & (hours < 23)
            is_baja = (hours >= 23) | (hours < 5)
            is_resto = ~(is_alta | is_baja)
            
            e_alta = m_df[is_alta]["consumption_kw"].sum()
            e_baja = m_df[is_baja]["consumption_kw"].sum()
            e_resto = m_df[is_resto]["consumption_kw"].sum()
            
            m_energy = (e_alta * 0.20) + (e_baja * 0.10) + (e_resto * 0.15)
            
            net_m = m_fixed + m_capacity + m_peak_penalty + m_excess + m_energy
            
            # Pre-tax custom adjustments
            net_with_pre_tax = net_m + 5000.0
            
            # Surcharges: VAT 27.0%, Provincial 11.5% -> Total 38.5%
            taxes_sum = net_with_pre_tax * 0.385
            
            # Gross subtotal
            gross_m = net_with_pre_tax + taxes_sum
            
            # Post-tax adjustments: +43000.0 - 10000.0 = +33000.0
            gross_m += 33000.0
            
            expected_annual_gross += max(0.0, gross_m)
            
        total_bill = calculate_annual_grid_bill_with_pillars(self.df, fin_params)
        
        self.assertAlmostEqual(total_bill, expected_annual_gross, delta=1.0)

if __name__ == "__main__":
    unittest.main()
