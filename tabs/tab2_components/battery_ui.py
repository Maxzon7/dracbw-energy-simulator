# tabs/tab2_components/battery_ui.py
import streamlit as st

def render_battery_ui():
    """
    Renders the toggle and input sliders for the Battery BESS module.
    """
    st.write("### 🔋 Battery Storage (Peak Shaving)")
    enable_battery = st.toggle("Enable Battery Simulation", value=True)
    
    b_cap = 0.0
    b_pwr = 0.0
    
    if enable_battery:
        c1, c2 = st.columns(2)
        with c1:
            b_cap = st.slider("Capacity (kWh)", 0, 500, 100)
        with c2:
            b_pwr = st.slider("Max Power (kW)", 0, 200, 50)
            
    return enable_battery, b_cap, b_pwr