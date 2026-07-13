# demo_mode/demo_main.py
import streamlit as st
import pandas as pd
from demo_mode.demo_components.location_ui import render_demo_location_ui
from demo_mode.demo_components.solar_ui import render_demo_solar_ui
from demo_mode.demo_components.results_viewer import render_demo_results
from tabs.tab2_components.solar_logic import generate_solar_profile

def render_demo_mode():
    """
    Main orchestrator for the simplified Demo Mode.
    Renders inputs, controls simulation state, and triggers results visualization.
    """
    st.markdown("## 🧪 Demo Mode: Simplified Solar Yield Calculator")
    st.write(
        "Welcome to the simplified Solar Yield Simulator. In this mode, you can quickly evaluate the "
        "energy generation potential of a solar PV installation anywhere in the world. "
        "No baseline consumption data or tariffs required."
    )
    st.divider()

    # Initialize session states to persist results across reruns
    if "demo_results" not in st.session_state:
        st.session_state["demo_results"] = None
    if "demo_installed_kwp" not in st.session_state:
        st.session_state["demo_installed_kwp"] = 0.0
    if "demo_country_val" not in st.session_state:
        st.session_state["demo_country_val"] = ""

    # Split page into left sidebar-like inputs and right results viewer
    col_input, col_results = st.columns([1, 2], gap="large")

    with col_input:
        # Wrap inputs in a form or just clean containers
        with st.container(border=True):
            loc_params = render_demo_location_ui()
            
        st.write("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            sol_params = render_demo_solar_ui()

        st.write("<br>", unsafe_allow_html=True)
        
        # Trigger button
        calc_button = st.button("🚀 Calculate Solar Yield", type="primary", use_container_width=True)

    with col_results:
        if calc_button:
            with st.spinner("Fetching meteorological radiation database and simulating solar physics..."):
                try:
                    # Construct empty 15-minute time series for the year 2022 (reference weather year)
                    timestamps = pd.date_range(start='2022-01-01', end='2022-12-31 23:45:00', freq='15min')
                    baseline_df = pd.DataFrame({
                        'timestamp': timestamps,
                        'consumption_kw': 0.0  # mock consumption is not needed
                    })

                    # Map inputs onto solar logic parameters
                    project_metadata = {
                        'latitude': loc_params['latitude'],
                        'longitude': loc_params['longitude'],
                        'country': loc_params['country'],
                        'strict_zero_export': False
                    }

                    # Execute calculation using recycled solar engine logic
                    results_df = generate_solar_profile(baseline_df, project_metadata, sol_params)
                    
                    # Store results in session state
                    st.session_state["demo_results"] = results_df
                    st.session_state["demo_installed_kwp"] = sol_params["installed_kwp"]
                    st.session_state["demo_country_val"] = loc_params["country"]
                    
                    st.success("🎉 Simulation completed successfully!")
                except Exception as sim_err:
                    st.error(f"Simulation failed: {sim_err}")

        # Render results if available
        if st.session_state["demo_results"] is not None:
            render_demo_results(
                results=st.session_state["demo_results"],
                installed_kwp=st.session_state["demo_installed_kwp"],
                country=st.session_state["demo_country_val"]
            )
        else:
            # Placeholder display
            st.info("👈 Configure the Location and Solar PV Setup on the left, then click **Calculate Solar Yield** to begin the simulation.")
            
            # Add a premium card explaining what happens
            st.markdown(
                """
                <div style="background-color:rgba(255, 193, 7, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(255, 193, 7, 0.2); margin-top:20px;">
                    <h4 style="color:#FF9800; margin-top:0;">⚡ Under the Hood</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Global Weather Database:</strong> We fetch hourly solar radiation data (Global Horizontal Irradiance) from the Open-Meteo API using your exact coordinates.</li>
                        <li><strong>Tilt & Orientation Transposition:</strong> The model adjusts panel angle (tilt) and compass direction (azimuth) relative to the sun path in the given country.</li>
                        <li><strong>Thermal Efficiency Loss:</strong> Computes cell heating degradation in hot summer months.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True
            )
