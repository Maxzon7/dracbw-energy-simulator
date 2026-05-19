# tabs/tab2_components/solar_ui.py
import streamlit as st

def render_solar_ui():
    """
    Renders the toggle and input sliders for the Solar PV module.
    Returns the activation state and the chosen parameters.
    """
    st.write("### ☀️ Solar PV System")
    enable_solar = st.toggle("Enable Solar PV Simulation", value=False)
    
    capacity_kwp = 0.0
    yield_factor = 0.0
    
    if enable_solar:
        c1, c2 = st.columns(2)
        with c1:
            capacity_kwp = st.number_input(
                "Installed Capacity (kWp)", 
                min_value=0.0, value=100.0, step=10.0,
                help="Total peak power of the solar installation."
            )
        with c2:
            yield_factor = st.number_input(
                "Annual Yield Factor (kWh/kWp)", 
                min_value=500.0, value=1000.0, step=50.0,
                help="Geographic efficiency. How many kWh does 1 kWp produce per year?"
            )
            
    return enable_solar, capacity_kwp, yield_factor