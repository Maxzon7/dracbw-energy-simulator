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
        panel_count_val = st.session_state.get(f"sol_panels_{scenario_id}", panel_count)
        panel_wp_val = st.session_state.get(f"sol_wp_{scenario_id}", panel_wp)
        installed_kwp = (panel_count_val * panel_wp_val) / 1000.0
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
    
    st.write("**System Losses & Efficiency**")
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
        
    # --- Advanced parameters expander to match Demo Mode sandbox ---
    with st.expander("Advanced Solar Parameters & Overrides", expanded=False):
        panel_type = st.selectbox(
            "Panel Type / Chemistry",
            ["Monocrystalline Silicon", "Polycrystalline Silicon", "Thin-Film / CdTe"],
            index=["Monocrystalline Silicon", "Polycrystalline Silicon", "Thin-Film / CdTe"].index(existing_params.get("panel_type", "Monocrystalline Silicon")),
            key=f"sol_panel_type_{scenario_id}"
        )
        ghi_source = st.selectbox(
            "Irradiation Data Source",
            ["Open-Meteo API", "Manual specific yield", "Manual sunshine hours"],
            index=["Open-Meteo API", "Manual specific yield", "Manual sunshine hours"].index(existing_params.get("ghi_source", "Open-Meteo API")),
            key=f"sol_ghi_source_{scenario_id}"
        )
        
        specific_yield = float(existing_params.get("specific_yield", 950.0))
        annual_sunshine_hours = float(existing_params.get("annual_sunshine_hours", 1500.0))
        
        if ghi_source == "Manual specific yield":
            specific_yield = st.number_input(
                "Manual Specific Yield (kWh/kWp/year)",
                min_value=100.0, max_value=3000.0, value=specific_yield, step=50.0,
                key=f"sol_specific_yield_{scenario_id}"
            )
        elif ghi_source == "Manual sunshine hours":
            annual_sunshine_hours = st.number_input(
                "Manual Equivalent Full-Load Hours (hrs/year)",
                min_value=100.0, max_value=4000.0, value=annual_sunshine_hours, step=50.0,
                key=f"sol_sun_hours_{scenario_id}"
            )
            
        yield_factor = st.slider(
            "Local Yield Multiplier / Shading Factor",
            min_value=0.5, max_value=1.5, value=float(existing_params.get("yield_factor", 1.0)), step=0.05,
            key=f"sol_yield_factor_{scenario_id}"
        )
        
        st.write("**Detailed Losses Configuration (%)**")
        col_dl1, col_dl2 = st.columns(2)
        loss_inverter = col_dl1.slider("Inverter Losses (%)", 0.0, 10.0, float(existing_params.get("loss_inverter", 3.0)), step=0.5, key=f"sol_loss_inv_{scenario_id}")
        loss_cabling = col_dl2.slider("Cabling Losses (%)", 0.0, 5.0, float(existing_params.get("loss_cabling", 1.5)), step=0.1, key=f"sol_loss_cab_{scenario_id}")
        loss_soiling = col_dl1.slider("Soiling & Dirt Losses (%)", 0.0, 5.0, float(existing_params.get("loss_soiling", 1.0)), step=0.1, key=f"sol_loss_soil_{scenario_id}")
        loss_other = col_dl2.slider("Other System Losses (%)", 0.0, 10.0, float(existing_params.get("loss_other", 2.0)), step=0.5, key=f"sol_loss_oth_{scenario_id}")
        
        temp_coeff = st.slider(
            "Temperature Loss Coefficient (%/°C above 25°C)",
            0.0, 1.0, float(existing_params.get("temp_coeff", 0.25)), step=0.05,
            key=f"sol_temp_coeff_{scenario_id}"
        )

    # --- Financial Estimates (CAPEX/OPEX & Degradation) - Conditional on enable_financials ---
    capex_per_kwp = float(existing_params.get("capex_per_kwp", 850.0))
    opex_pct = float(existing_params.get("opex_pct", 1.0))
    degradation_pct = float(existing_params.get("degradation_pct", 0.5))
    total_solar_capex = installed_kwp * capex_per_kwp

    if st.session_state.get('enable_financials', False):
        st.divider()
        with st.expander("Financial Estimates (CAPEX, OPEX & Degradation)", expanded=True):
            st.write("Configure the estimated capital expenditure, maintenance costs, and physical wear for the ROI analysis.")
            c_fin1, c_fin2, c_fin3 = st.columns(3)
            
            capex_per_kwp = c_fin1.number_input(
                "CAPEX (€ per kWp)", 
                min_value=100.0, max_value=3000.0, 
                value=capex_per_kwp, step=50.0,
                key=f"sol_capex_{scenario_id}"
            )
            opex_pct = c_fin2.number_input(
                "Annual OPEX (% of CAPEX)", 
                min_value=0.0, max_value=10.0, 
                value=opex_pct, step=0.1,
                help="Estimated yearly maintenance, insurance, and cleaning costs.",
                key=f"sol_opex_{scenario_id}"
            )
            degradation_pct = c_fin3.number_input(
                "Annual Degradation (%)", 
                min_value=0.0, max_value=5.0, 
                value=degradation_pct, step=0.1,
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
        "panel_type": panel_type,
        "ghi_source": ghi_source,
        "specific_yield": specific_yield,
        "annual_sunshine_hours": annual_sunshine_hours,
        "yield_factor": yield_factor,
        "loss_inverter": loss_inverter,
        "loss_cabling": loss_cabling,
        "loss_soiling": loss_soiling,
        "loss_other": loss_other,
        "temp_coeff": temp_coeff,
        "capex_per_kwp": capex_per_kwp,
        "opex_pct": opex_pct,
        "degradation_pct": degradation_pct,
        "total_capex": total_solar_capex
    }