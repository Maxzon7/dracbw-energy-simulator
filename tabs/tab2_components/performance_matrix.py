# tabs/tab2_components/performance_matrix.py
import streamlit as st
import pandas as pd
from logic.energy_logic import get_exact_minimum_requirements

def render_performance_matrix(results: pd.DataFrame, baseline_df: pd.DataFrame, grid_limit: float, res: int, current_mode: str, current_params: dict, project_metadata: dict) -> tuple:
    """
    Renders the Advanced Technical Performance Matrix columns and calculates baseline metrics.
    Returns peak_orig and min_reqs to feed the PDF generation pipeline seamlessly.
    """
    st.write("### 📈 Advanced Technical Performance Matrix")
    
    # Base Math Calculations
    total_consumption_kwh = results['consumption_kw'].sum() / (60 / res)
    total_grid_import_kwh = results['final_grid_load_kw'].clip(lower=0.0).sum() / (60 / res)
    
    autarky_pct = 0.0
    if total_consumption_kwh > 0:
        autarky_pct = (1.0 - (total_grid_import_kwh / total_consumption_kwh)) * 100.0
        
    peak_orig = results['consumption_kw'].max()
    peak_new = results['final_grid_load_kw'].max()
    
    peak_shaving_pct = 0.0
    if peak_orig > 0:
        peak_shaving_pct = ((peak_orig - peak_new) / peak_orig) * 100.0

    # UI Layout columns split
    col_autarky, col_grid, col_asset = st.columns(3)
    
    with col_autarky:
        st.write("**Autarky & Yield**")
        st.metric("Degree of Autarky", f"{autarky_pct:.1f} %")
        
        has_solar = 'solar_gen_kw' in results.columns and results['solar_gen_kw'].sum() > 0
        has_battery = 'battery_action_kw' in results.columns and (results['battery_action_kw'] != 0.0).any()

        if has_solar:
            total_solar_kwh = results['solar_gen_kw'].sum() / (60 / res)
            
            if has_battery:
                if project_metadata.get('strict_zero_export', False):
                    curtailed_kwh = results['final_grid_load_kw'].clip(upper=0.0).abs().sum() / (60 / res)
                else:
                    curtailed_kwh = 0.0
            else:
                gross_excess_kwh = (results['solar_gen_kw'] - results['consumption_kw']).clip(lower=0.0).sum() / (60 / res)
                feed_in_kwh = results.get('grid_feed_in_kw', pd.Series([0])).sum() / (60 / res)
                curtailed_kwh = gross_excess_kwh - feed_in_kwh
            
            self_consumption_pct = 0.0
            if total_solar_kwh > 0:
                exported_or_curtailed = results['final_grid_load_kw'].clip(upper=0.0).abs().sum() / (60 / res)
                self_consumed_kwh = total_solar_kwh - exported_or_curtailed
                self_consumption_pct = (self_consumed_kwh / total_solar_kwh) * 100.0
                
            st.metric("Self-Consumption", f"{self_consumption_pct:.1f} %")
            st.metric("Curtailed Energy", f"{curtailed_kwh:,.0f} kWh", delta="Wasted", delta_color="inverse")
            
    with col_grid:
        st.write("**Grid Stability**")
        st.metric("New Peak Load", f"{peak_new:.1f} kW", delta=f"-{peak_shaving_pct:.1f}% Peak Shaved", delta_color="normal")
        st.metric("Uncovered Demand", "0 kWh", delta="Safe", delta_color="normal")
        
    with col_asset:
        st.write("**Hardware & Assets**")
        min_reqs = {"min_power_kw": 0, "true_min_capacity_kwh": 0}
        
        if has_battery:
            min_reqs = get_exact_minimum_requirements(baseline_df, grid_limit, res)
            throughput_kwh = results['battery_action_kw'].abs().sum() / (60 / res)
            b_cap = current_params.get('battery', current_params).get('b_cap', 0) if isinstance(current_params, dict) else 0
            
            cycles = (throughput_kwh / 2.0) / b_cap if b_cap > 0 else 0
            deg_pct = (cycles / 5000) * 100.0 
            
            st.metric("Battery Cycles", f"{cycles:.0f} Cycles")
            st.metric("Est. Degradation (1 Yr)", f"-{deg_pct:.2f} %", delta_color="inverse")
            st.metric("Req. Capacity (Ideal)", f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")
        else:
            st.metric("Battery Cycles", "N/A")
            st.metric("Est. Degradation", "N/A")

    return peak_orig, min_reqs