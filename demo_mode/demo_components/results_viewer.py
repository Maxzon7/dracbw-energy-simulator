import streamlit as st
import pandas as pd
from demo_mode.demo_components.results_utils import get_season
from demo_mode.demo_components.results_solar_yield import render_pure_solar_results
from demo_mode.demo_components.results_mini_scenario import render_mini_scenario_results

def render_demo_results(
    results: pd.DataFrame, 
    installed_kwp: float, 
    country: str,
    has_consumption: bool = False,
    grid_limit: float = 0.0,
    has_battery: bool = False,
    has_generator: bool = False,
    has_financials: bool = False,
    fin_params: dict = None
):
    """
    Renders the metrics, charts, and export options for Demo Mode.
    Supports both pure Solar Yield simulations and full load-shaving Mini-Scenarios.
    """
    t = st.session_state.get('t', {})
    st.write(f"### {t.get('demo_results_title', 'Simulation Results & Analytics')}")
    
    # 1-hour intervals, so res = 60
    res_factor = 1.0 # 60 / 60 min = 1 hour
    
    # Render main dashboard based on consumption presence
    if not has_consumption:
        render_pure_solar_results(
            results=results,
            installed_kwp=installed_kwp,
            country=country,
            res_factor=res_factor
        )
    else:
        render_mini_scenario_results(
            results=results,
            installed_kwp=installed_kwp,
            country=country,
            grid_limit=grid_limit,
            has_battery=has_battery,
            has_generator=has_generator,
            has_financials=has_financials,
            fin_params=fin_params,
            res_factor=res_factor
        )

    # Export CSV Section
    st.divider()
    with st.expander(t.get('demo_res_csv_header', "📥 Export Simulated Data as CSV"), expanded=False):
        st.write(t.get('demo_res_csv_subtitle', "Download the simulated hourly profile and solar yield results:"))
        
        cols_to_export = {
            "Timestamp": results['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        }
        if has_consumption:
            cols_to_export["Consumption_kW"] = results['consumption_kw'].round(2)
            cols_to_export["Optimized_Grid_Load_kW"] = results['final_grid_load_kw'].round(2)
        if 'solar_gen_kw' in results.columns:
            cols_to_export["Solar_Yield_kW"] = results['solar_gen_kw'].round(3)
        if 'ghi_w_m2' in results.columns:
            cols_to_export["GHI_W_m2"] = results['ghi_w_m2'].round(1)
        if has_battery and 'battery_action_kw' in results.columns:
            cols_to_export["Battery_Action_kW"] = results['battery_action_kw'].round(2)
            cols_to_export["Battery_SoC_kWh"] = results['battery_soc_kwh'].round(2)
        if has_generator and 'generator_action_kw' in results.columns:
            cols_to_export["Generator_Action_kW"] = results['generator_action_kw'].round(2)
            cols_to_export["Generator_Fuel_L"] = results['generator_fuel_l'].round(2)
            
        export_df = pd.DataFrame(cols_to_export)
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label=t.get('demo_res_csv_btn', "Download CSV File"),
            data=csv_data,
            file_name=f"demo_simulation_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="demo_csv_download"
        )
        st.caption(t.get('demo_res_csv_caption', "The CSV file contains the timestamp index and all active simulation trace values in 1-hour resolution."))
