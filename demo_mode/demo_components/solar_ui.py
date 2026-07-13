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

    return {
        "installed_kwp": installed_kwp,
        "performance_ratio": pr,
        "tilt": tilt,
        "azimuth": azimuth,
        "thermal_loss": thermal_loss
    }
