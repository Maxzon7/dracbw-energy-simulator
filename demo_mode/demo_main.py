# demo_mode/demo_main.py
import streamlit as st
import pandas as pd
import numpy as np
from demo_mode.demo_components.location_ui import render_demo_location_ui
from demo_mode.demo_components.solar_ui import render_demo_solar_ui
from demo_mode.demo_components.results_viewer import render_demo_results
from tabs.tab2_components.solar_logic import generate_solar_profile
from logic.energy_logic import simulate_battery_logic, simulate_generator_logic

def generate_hourly_consumption(
    monthly_consumption: float, 
    days_per_week: int, 
    hours_per_day: int, 
    base_load_pct: int = 15,
    noise_percentage: float = 5.0
) -> pd.DataFrame:
    """Generates an hourly baseline load profile for a full year (2022)."""
    timestamps = pd.date_range(start='2022-01-01', end='2022-12-31 23:00:00', freq='h')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    start_hour = 8
    end_hour = start_hour + hours_per_day
    
    if end_hour > 24:
        op_mask = (df['hour'] >= start_hour) | (df['hour'] < (end_hour % 24))
    else:
        op_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
        
    if hours_per_day == 24:
        op_mask = pd.Series([True] * len(df))
        
    working_days_mask = df['dayofweek'] < days_per_week
    active_mask = op_mask & working_days_mask
    profile[active_mask] = 1.0
    
    # Add noise
    std_dev = noise_percentage / 100.0
    noise = np.random.normal(1.0, std_dev, len(profile))
    profile = profile * noise
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Scale to target (since freq is hourly, sum of profile is energy in kWh)
    annual_target_kwh = monthly_consumption * 12.0
    current_annual_energy = np.sum(profile)
    scaling_factor = annual_target_kwh / current_annual_energy if current_annual_energy > 0 else 1.0
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    return df

def render_demo_mode():
    """
    Main orchestrator for the simplified Demo Mode.
    Renders inputs, controls simulation state, and triggers results visualization.
    Calculations run in 1-hour intervals for optimal performance.
    """
    st.markdown("## 🧪 Demo Mode: Instant Scenario Simulator")
    st.write(
        "Throw together a custom energy scenario in seconds! "
        "Select your technologies, adjust limits, and visualize the output in real-time. "
        "Calculations run in 1-hour resolution for optimal performance."
    )
    st.divider()

    # Initialize session states
    if "demo_results" not in st.session_state:
        st.session_state["demo_results"] = None
    if "demo_installed_kwp" not in st.session_state:
        st.session_state["demo_installed_kwp"] = 0.0
    if "demo_country_val" not in st.session_state:
        st.session_state["demo_country_val"] = ""
    if "demo_has_consumption" not in st.session_state:
        st.session_state["demo_has_consumption"] = False
    if "demo_grid_limit" not in st.session_state:
        st.session_state["demo_grid_limit"] = 0.0
    if "demo_has_battery" not in st.session_state:
        st.session_state["demo_has_battery"] = False
    if "demo_has_generator" not in st.session_state:
        st.session_state["demo_has_generator"] = False

    # Two-column layout: Inputs on the left, Results on the right
    col_input, col_results = st.columns([1, 2], gap="large")

    with col_input:
        # 1. Location Settings
        with st.container(border=True):
            loc_params = render_demo_location_ui()
            
        st.write("<br>", unsafe_allow_html=True)
        
        # 2. Consumption Settings
        with st.container(border=True):
            st.write("### 📈 Consumption & Grid")
            has_consumption = st.checkbox("Add Baseline Consumption Profile", value=st.session_state["demo_has_consumption"])
            
            if has_consumption:
                monthly_cons = st.number_input("Avg. Monthly Consumption (kWh)", min_value=100, value=50000, step=1000)
                col_cons1, col_cons2 = st.columns(2)
                work_days = col_cons1.slider("Working Days / Week", 1, 7, 5)
                work_hours = col_cons2.slider("Working Hours / Day", 1, 24, 12)
                base_load = st.slider("Base Load Percentage (%)", 0, 100, 15)
                
                grid_limit = st.number_input("Grid Connection Limit (kW)", min_value=5.0, value=120.0, step=5.0)
            else:
                monthly_cons, work_days, work_hours, base_load = 0.0, 5, 12, 15
                grid_limit = 0.0

        st.write("<br>", unsafe_allow_html=True)
        
        # 3. Solar PV Setup
        with st.container(border=True):
            st.write("### ☀️ Solar Integration")
            has_solar = st.checkbox("Integrate Solar PV", value=(st.session_state["demo_installed_kwp"] > 0.0 or not has_consumption))
            if has_solar:
                sol_params = render_demo_solar_ui()
                installed_kwp = sol_params["installed_kwp"]
            else:
                sol_params = {}
                installed_kwp = 0.0

        st.write("<br>", unsafe_allow_html=True)
        
        # 4. Battery Storage (Only if Consumption is active)
        with st.container(border=True):
            st.write("### 🔋 Battery Storage (BESS)")
            if has_consumption:
                has_battery = st.checkbox("Integrate Battery (BESS)", value=st.session_state["demo_has_battery"])
                if has_battery:
                    b_cap = st.number_input("Storage Capacity (kWh)", min_value=5.0, value=200.0, step=10.0)
                    b_pwr = st.number_input("Max Inverter Power (kW)", min_value=5.0, value=100.0, step=5.0)
                    chg_pwr = st.slider("Max Recharge Speed (kW)", 5, 200, 30)
                    
                    # We auto-configure a green charging window
                    bat_params = {
                        "b_cap": b_cap,
                        "b_pwr": b_pwr,
                        "shaving_threshold": grid_limit,
                        "charge_pwr_limit": chg_pwr,
                        "charge_start_hour": 22,
                        "charge_end_hour": 6,
                        "green_charging": has_solar,
                        "efficiency": 92.0,
                        "initial_soc_pct": 50.0
                    }
                else:
                    bat_params = {}
            else:
                st.caption("Enable 'Baseline Consumption Profile' to add battery peak shaving.")
                has_battery = False
                bat_params = {}

        st.write("<br>", unsafe_allow_html=True)
        
        # 5. Generator Setup (Only if Consumption is active)
        with st.container(border=True):
            st.write("### 🛢️ Backup Generator")
            if has_consumption:
                has_generator = st.checkbox("Integrate Backup Generator", value=st.session_state["demo_has_generator"])
                if has_generator:
                    gen_pwr = st.number_input("Generator Power (kW)", min_value=5.0, value=100.0, step=5.0)
                    fuel_rate = st.number_input("Fuel Consumption Rate (L/kWh)", min_value=0.05, max_value=2.0, value=0.28, step=0.01)
                    gen_params = {
                        "gen_pwr": gen_pwr,
                        "fuel_l_per_kwh": fuel_rate
                    }
                else:
                    gen_params = {}
            else:
                st.caption("Enable 'Baseline Consumption Profile' to add generator peak shaving.")
                has_generator = False
                gen_params = {}

        st.write("<br>", unsafe_allow_html=True)
        
        calc_button = st.button("🚀 Calculate Scenario", type="primary", use_container_width=True)

    with col_results:
        if calc_button:
            with st.spinner("Simulating scenario timeline..."):
                try:
                    # 1. Generate Baseline consumption (hourly frequency)
                    if has_consumption:
                        baseline_df = generate_hourly_consumption(
                            monthly_consumption=monthly_cons,
                            days_per_week=work_days,
                            hours_per_day=work_hours,
                            base_load_pct=base_load,
                            noise_percentage=5.0
                        )
                    else:
                        timestamps = pd.date_range(start='2022-01-01', end='2022-12-31 23:00:00', freq='h')
                        baseline_df = pd.DataFrame({
                            'timestamp': timestamps,
                            'consumption_kw': 0.0
                        })

                    # Setup metadata
                    project_metadata = {
                        'latitude': loc_params['latitude'],
                        'longitude': loc_params['longitude'],
                        'country': loc_params['country'],
                        'strict_zero_export': False
                    }

                    # Running profile copy
                    calculated_df = baseline_df.copy()
                    calculated_df['solar_gen_kw'] = 0.0
                    calculated_df['battery_action_kw'] = 0.0
                    calculated_df['battery_soc_kwh'] = 0.0
                    calculated_df['generator_action_kw'] = 0.0
                    calculated_df['generator_fuel_l'] = 0.0
                    calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']

                    # 2. Simulate Solar PV
                    if has_solar and installed_kwp > 0.0:
                        calculated_df = generate_solar_profile(calculated_df, project_metadata, sol_params)
                    else:
                        calculated_df['solar_gen_kw'] = 0.0
                        calculated_df['net_load_kw'] = calculated_df['consumption_kw']
                        calculated_df['grid_feed_in_kw'] = 0.0

                    # 3. Simulate Battery (BESS) - res=60 for hourly frequency
                    if has_battery:
                        calculated_df = simulate_battery_logic(calculated_df, grid_limit, bat_params, res=60)
                    else:
                        calculated_df['battery_action_kw'] = 0.0
                        calculated_df['battery_soc_kwh'] = 0.0
                        calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']

                    # 4. Simulate Generator - res=60 for hourly frequency
                    if has_generator:
                        calculated_df = simulate_generator_logic(calculated_df, grid_limit, gen_params, res=60)
                    else:
                        calculated_df['generator_action_kw'] = 0.0
                        calculated_df['generator_fuel_l'] = 0.0
                        
                    if 'final_grid_load_kw' not in calculated_df.columns:
                        calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']

                    # Persist results in session state
                    st.session_state["demo_results"] = calculated_df
                    st.session_state["demo_installed_kwp"] = installed_kwp
                    st.session_state["demo_country_val"] = loc_params["country"]
                    st.session_state["demo_has_consumption"] = has_consumption
                    st.session_state["demo_grid_limit"] = grid_limit
                    st.session_state["demo_has_battery"] = has_battery
                    st.session_state["demo_has_generator"] = has_generator
                    
                    st.success("🎉 Scenario calculated successfully!")
                except Exception as sim_err:
                    st.error(f"Simulation failed: {sim_err}")

        # Render results if available
        if st.session_state["demo_results"] is not None:
            render_demo_results(
                results=st.session_state["demo_results"],
                installed_kwp=st.session_state["demo_installed_kwp"],
                country=st.session_state["demo_country_val"],
                has_consumption=st.session_state["demo_has_consumption"],
                grid_limit=st.session_state["demo_grid_limit"],
                has_battery=st.session_state["demo_has_battery"],
                has_generator=st.session_state["demo_has_generator"]
            )
        else:
            # Placeholder display
            st.info("👈 Configure your location and active technologies on the left, then click **🚀 Calculate Scenario** to run the simulation.")
            
            st.markdown(
                """
                <div style="background-color:rgba(0, 204, 150, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(0, 204, 150, 0.2); margin-top:20px;">
                    <h4 style="color:#00CC96; margin-top:0;">⚡ Instant Prototyping Sandbox</h4>
                    <p style="margin: 0 0 10px 0;">Use this sandbox to test configurations without setting up project folders, raw CSV ingestion, or contracts.</p>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Flexible Load Profiles:</strong> Generate a synthetic factory/office load instantly.</li>
                        <li><strong>Battery Peak Shaving:</strong> Check if a 200 kWh battery is enough to shave peaks down.</li>
                        <li><strong>Solar Self-Consumption:</strong> See when the battery charges from solar surplus.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True
            )
