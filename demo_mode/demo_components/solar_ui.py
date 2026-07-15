# demo_mode/demo_components/solar_ui.py
import streamlit as st

def render_demo_solar_ui() -> dict:
    """
    Renders the simplified Solar PV configuration panel for Demo Mode.
    Returns configured parameters for solar yield calculation.
    """
    st.write("### ☀️ Solar PV Setup")
    st.info("Configure the solar panels and system layout.")

    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Hardware Specifications**")
        panel_count = st.number_input(
            "Number of Solar Panels", 
            min_value=1, max_value=100000, value=500, step=10,
            key="demo_sol_panels"
        )
        panel_wp = st.slider(
            "Power per Panel (Watt-peak)", 
            min_value=100, max_value=800, value=420, step=5,
            key="demo_sol_wp"
        )
        
        installed_kwp = (panel_count * panel_wp) / 1000.0
        st.success(f"**Total Capacity: {installed_kwp:,.1f} kWp**")

    with col2:
        st.write("**Orientation**")
        azimuth = st.selectbox(
            "Azimuth (Orientation)", 
            options=["South (180°)", "North (0°)", "East (90°)", "West (270°)"],
            index=0,
            key="demo_sol_az"
        )
        tilt = st.selectbox(
            "Inclination (Tilt Angle)", 
            options=["0° (Flat)", "15°", "30°", "45°"],
            index=2,
            key="demo_sol_tilt"
        )

    st.write("**System Losses & Efficiency**")
    col_loss1, col_loss2 = st.columns(2)
    with col_loss1:
        pr = st.slider(
            "System Efficiency (PR %)", 
            min_value=50, max_value=100, value=85,
            help="Accounts for losses like inverter efficiency, dust, and cables.",
            key="demo_sol_pr"
        )
    with col_loss2:
        thermal_loss = st.checkbox(
            "Enable Thermal Losses (>25°C penalty)", 
            value=True,
            help="Reduces performance during hot summer hours.",
            key="demo_sol_therm"
        )

    # Advanced configurations under expander to prevent cluttering simple mode
    with st.expander("Advanced Solar Parameters & Overrides", expanded=False):
        panel_type = st.selectbox(
            "Panel Type / Chemistry",
            ["Monocrystalline Silicon", "Polycrystalline Silicon", "Thin-Film / CdTe"],
            index=0,
            key="demo_sol_panel_type"
        )
        ghi_source = st.selectbox(
            "Irradiation Data Source",
            ["Open-Meteo API", "Manual specific yield", "Manual sunshine hours"],
            index=0,
            key="demo_sol_ghi_source"
        )
        
        specific_yield = 950.0
        annual_sunshine_hours = 1500.0
        if ghi_source == "Manual specific yield":
            specific_yield = st.number_input(
                "Manual Specific Yield (kWh/kWp/year)",
                min_value=100.0, max_value=3000.0, value=950.0, step=50.0,
                key="demo_sol_specific_yield"
            )
        elif ghi_source == "Manual sunshine hours":
            annual_sunshine_hours = st.number_input(
                "Manual Equivalent Full-Load Hours (hrs/year)",
                min_value=100.0, max_value=4000.0, value=1500.0, step=50.0,
                key="demo_sol_sun_hours"
            )
            
        yield_factor = st.slider(
            "Local Yield Multiplier / Shading Factor",
            min_value=0.5, max_value=1.5, value=1.0, step=0.05,
            help="Scales the output to model shadows, local microclimate, etc.",
            key="demo_sol_yield_factor"
        )
        
        st.write("**Detailed Losses Configuration (%)**")
        col_dl1, col_dl2 = st.columns(2)
        loss_inverter = col_dl1.slider("Inverter Losses (%)", 0.0, 10.0, 3.0, step=0.5, key="demo_sol_loss_inv")
        loss_cabling = col_dl2.slider("Cabling Losses (%)", 0.0, 5.0, 1.5, step=0.1, key="demo_sol_loss_cab")
        loss_soiling = col_dl1.slider("Soiling & Dirt Losses (%)", 0.0, 5.0, 1.0, step=0.1, key="demo_sol_loss_soil")
        loss_other = col_dl2.slider("Other System Losses (%)", 0.0, 10.0, 2.0, step=0.5, key="demo_sol_loss_oth")
        
        temp_coeff = st.slider(
            "Temperature Loss Coefficient (%/°C above 25°C)",
            0.0, 1.0, 0.25, step=0.05,
            key="demo_sol_temp_coeff"
        )

    return {
        "installed_kwp": installed_kwp,
        "performance_ratio": pr,
        "tilt": tilt,
        "azimuth": azimuth,
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
        "temp_coeff": temp_coeff
    }
