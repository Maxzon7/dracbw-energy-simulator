# tabs/tab2_components/solar_ui.py
import streamlit as st

def render_solar_ui(scenario_id: str, existing_params: dict = None) -> dict:
    """
    Layer 1: Renders the UI inputs for the Solar PV simulation.
    Returns a dictionary of the configured physical and financial parameters.
    """
    if existing_params is None:
        existing_params = {}

    st.write("### Solar PV Dimensioning")
    st.info("Configure the physical and geographical properties of the solar installation.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Hardware Specifications**")
        panel_count = st.number_input(
            "Number of Solar Panels", 
            min_value=10, max_value=10000, 
            value=int(existing_params.get("panel_count", 500)), step=10,
            key=f"sol_panels_{scenario_id}"
        )
        panel_wp = st.slider(
            "Power per Panel (Watt-peak)", 
            min_value=300, max_value=650, 
            value=int(existing_params.get("panel_wp", 420)), step=5,
            key=f"sol_wp_{scenario_id}"
        )
        
        # Instant mathematical feedback
        installed_kwp = (panel_count * panel_wp) / 1000.0
        st.success(f"**Total Installed Capacity: {installed_kwp:,.1f} kWp**")

    with col2:
        st.write("**Geographical Orientation**")
        azimuth_options = ["South (180°)", "North (0°)", "East (90°)", "West (270°)"]
        az_val = existing_params.get("azimuth", "South (180°)")
        az_idx = azimuth_options.index(az_val) if az_val in azimuth_options else 0
        azimuth = st.selectbox(
            "Azimuth (Orientation)", 
            options=azimuth_options,
            index=az_idx,
            key=f"sol_az_{scenario_id}"
        )
        
        tilt_options = ["0° (Flat)", "15°", "30°", "45°"]
        tilt_val = existing_params.get("tilt", "30°")
        tilt_idx = tilt_options.index(tilt_val) if tilt_val in tilt_options else 2
        tilt = st.selectbox(
            "Inclination (Tilt Angle)", 
            options=tilt_options,
            index=tilt_idx,
            key=f"sol_tilt_{scenario_id}"
        )

    st.divider()
    
    st.write("**System Losses & Degradation**")
    col_loss1, col_loss2 = st.columns(2)
    with col_loss1:
        pr = st.slider(
            "Performance Ratio (System Efficiency %)", 
            min_value=70, max_value=98, 
            value=int(existing_params.get("performance_ratio", 85)),
            help="Accounts for inverter losses, cabling, and dirt.",
            key=f"sol_pr_{scenario_id}"
        )
    with col_loss2:
        thermal_loss = st.checkbox(
            "Enable Thermal Losses (>25°C penalty)", 
            value=existing_params.get("thermal_loss", True),
            help="Reduces midday peak efficiency during hot summer months.",
            key=f"sol_therm_{scenario_id}"
        )
        
    # --- NEU: Financial Estimates (CAPEX/OPEX & Degradation) ---
    st.divider()
    with st.expander("$$ Financial Estimates (CAPEX, OPEX & Degradation)", expanded=False):
        st.write("Configure the estimated capital expenditure, maintenance costs, and physical wear for the ROI analysis.")
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        
        capex_per_kwp = c_fin1.number_input(
            "CAPEX (€ per kWp)", 
            min_value=100.0, max_value=3000.0, 
            value=float(existing_params.get("capex_per_kwp", 850.0)), step=50.0,
            key=f"sol_capex_{scenario_id}"
        )
        opex_pct = c_fin2.number_input(
            "Annual OPEX (% of CAPEX)", 
            min_value=0.0, max_value=10.0, 
            value=float(existing_params.get("opex_pct", 1.0)), step=0.1,
            help="Estimated yearly maintenance, insurance, and cleaning costs.",
            key=f"sol_opex_{scenario_id}"
        )
        degradation_pct = c_fin3.number_input(
            "Annual Degradation (%)", 
            min_value=0.0, max_value=5.0, 
            value=float(existing_params.get("degradation_pct", 0.5)), step=0.1,
            help="Annual physical performance loss of the solar panels.",
            key=f"sol_deg_{scenario_id}"
        )
        
        total_solar_capex = installed_kwp * capex_per_kwp
        st.info(f"**Estimated Solar Investment (CAPEX): {total_solar_capex:,.0f} €**")
        
    return {
        "panel_count": panel_count,
        "panel_wp": panel_wp,
        "installed_kwp": installed_kwp,
        "azimuth": azimuth,
        "tilt": tilt,
        "performance_ratio": pr,
        "thermal_loss": thermal_loss,
        "capex_per_kwp": capex_per_kwp,
        "opex_pct": opex_pct,
        "degradation_pct": degradation_pct,
        "total_capex": total_solar_capex
    }