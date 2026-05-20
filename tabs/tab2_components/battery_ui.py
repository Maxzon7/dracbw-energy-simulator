# tabs/tab2_components/battery_ui.py
import streamlit as st

def render_battery_ui():
    """
    Renders the advanced input fields for the Battery BESS module.
    """
    st.write("### 🔋 Battery Storage (Peak Shaving)")
    enable_battery = st.toggle("Enable Battery Simulation", value=True)
    
    # Standard-Wörterbuch (Dictionary) anlegen, damit immer Werte existieren
    b_params = {
        "b_cap": 0.0, "b_pwr": 0.0, "eff": 90.0,
        "min_soc": 10.0, "max_soc": 100.0, "init_soc": 50.0,
        "cal_deg": 1.5, "cyc_deg": 2.0
    }
    
    if enable_battery:
        st.write("#### 1. Hardware Specifications")
        c1, c2, c3 = st.columns(3)
        with c1:
            b_params["b_cap"] = st.number_input("Capacity (kWh)", min_value=0.0, value=100.0, step=10.0)
        with c2:
            b_params["b_pwr"] = st.number_input("Max Power (kW)", min_value=0.0, value=50.0, step=5.0)
        with c3:
            b_params["eff"] = st.number_input("Round-Trip Efficiency (%)", min_value=50.0, max_value=100.0, value=90.0, step=1.0)
            
        st.write("#### 2. Operational Limits (SoC)")
        c4, c5, c6 = st.columns(3)
        with c4:
            b_params["min_soc"] = st.number_input("Min SoC (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
        with c5:
            b_params["max_soc"] = st.number_input("Max SoC (%)", min_value=0.0, max_value=100.0, value=95.0, step=1.0)
        with c6:
            b_params["init_soc"] = st.number_input("Initial SoC (%)", min_value=0.0, max_value=100.0, value=50.0, step=1.0)

        st.write("#### 3. Degradation Parameters")
        c7, c8 = st.columns(2)
        with c7:
            b_params["cal_deg"] = st.number_input("Calendar Degradation (%/year)", min_value=0.0, value=1.5, step=0.1)
        with c8:
            b_params["cyc_deg"] = st.number_input("Cyclic Degradation (%/1000 cycles)", min_value=0.0, value=2.0, step=0.1)
            
    # Wir geben jetzt nicht mehr einzelne Werte zurück, sondern das gesamte Paket
    return enable_battery, b_params