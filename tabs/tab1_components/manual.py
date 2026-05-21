# tabs/tab1_components/manual.py
import streamlit as st

# --- CLEAN HOOKS TO SUB-COMPONENTS ORDNER ---
from tabs.tab1_components.manual_components.anomaly_manager import render_anomaly_manager
from tabs.tab1_components.manual_components.generation_logic import run_profile_generation

def render_manual_profile_generator(active_scenario: str, is_edit_mode: bool, p: dict):
    """
    Renders the UI for generating synthetic 15-min load profiles.
    Acts as a high-level layout container routing to manual_components package.
    """
    t = st.session_state.get('t', {})
    st.write("### ⚙️ Load Profile Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        monthly_consumption = st.number_input(
            "Monthly Consumption (kWh)", min_value=100, 
            value=int(p.get('monthly_consumption', 15000)), step=1000, key=f"m_cons_{active_scenario}"
        )
        days_per_week = st.slider(
            "Working Days per Week", min_value=1, max_value=7, 
            value=int(p.get('days_per_week', 5)), key=f"d_week_{active_scenario}"
        )
        hours_per_day = st.slider(
            "Working Hours per Day", min_value=1, max_value=24, 
            value=int(p.get('hours_per_day', 8)), key=f"h_day_{active_scenario}"
        )
        base_load_pct = st.slider(
            "Base Load Level (%)", min_value=0, max_value=100, 
            value=int(p.get('base_load_pct', 15)), step=1, key=f"b_load_{active_scenario}"
        )
        
    with col2:
        st.write("#### Grid Connection Limit")
        num_connections = st.number_input(
            "Number of Connections", min_value=1, value=int(p.get('num_connections', 1)), 
            step=1, key=f"n_conn_{active_scenario}"
        )
        amperage = st.number_input(
            "Amperage per Connection (A)", min_value=16, value=int(p.get('amperage', 250)), 
            step=10, key=f"amp_{active_scenario}"
        )
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
    st.divider()
    
    # --- NOISE SECTION ---
    st.write("### Profile Load Behavior")
    enable_noise = st.toggle("Enable realistic load fluctuations", value=p.get('enable_noise', False), key=f"e_noise_{active_scenario}")
    noise_percentage = 0.0
    if enable_noise:
        noise_percentage = st.slider(
            "Fluctuation Intensity (%)", min_value=1, max_value=30, 
            value=int(p.get('noise_percentage', 5)), step=1, key=f"n_pct_{active_scenario}"
        )
        
    st.divider()

    # --- INJECT ROUTED ANOMALY COMPONENT ---
    render_anomaly_manager()

    st.divider()

    # --- ADVANCED MONTHLY CUSTOMIZATION WITH DYNAMIC KEYS ---
    st.write("### Advanced: Custom Monthly Profiles")
    use_custom_months = st.checkbox("Enable custom logic per month", value=p.get('use_custom_months', False), key=f"u_cust_m_{active_scenario}")
    
    monthly_configs = {}
    if use_custom_months:
        st.info("Values are pre-filled with your standard configuration or loaded memory.")
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        saved_configs = p.get("monthly_configs", {})
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            with tab:
                s_cons = saved_configs.get(m_idx, {}).get("consumption", monthly_consumption)
                s_days = saved_configs.get(m_idx, {}).get("days", days_per_week)
                s_hours = saved_configs.get(m_idx, {}).get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh) - {month_names[i]}", value=int(s_cons), key=f"c_{m_idx}_{active_scenario}")
                m_days = st.slider(f"Working Days - {month_names[i]}", min_value=1, max_value=7, value=int(s_days), key=f"d_{m_idx}_{active_scenario}")
                m_hours = st.slider(f"Working Hours - {month_names[i]}", min_value=1, max_value=24, value=int(s_hours), key=f"h_{m_idx}_{active_scenario}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    
    # ==========================================
    # SAVE & GENERATE ENGINE TRIGGER
    # ==========================================
    st.write("### 💾 Save Scenario")
    default_name = active_scenario if is_edit_mode else f"New_Scenario_{len(st.session_state['scenario_registry']) + 1}"
    scenario_name = st.text_input("Enter Scenario Name to Save/Overwrite:", value=default_name, key=f"scen_name_{active_scenario}")
    
    if st.button("Save & Generate Profile", type="primary", use_container_width=True):
        with st.spinner("Processing calculations..."):
            # Route inputs straight to the business logic sub-component
            run_profile_generation(
                scenario_name, active_scenario, monthly_consumption, days_per_week, 
                hours_per_day, base_load_pct, num_connections, amperage, 
                enable_noise, noise_percentage, use_custom_months, monthly_configs, calculated_grid_kw
            )
            st.success(f"Scenario '{scenario_name}' successfully generated and saved to registry!")
            st.rerun()