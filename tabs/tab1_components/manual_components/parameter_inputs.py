# tabs/tab1_components/manual_components/parameter_inputs.py
import streamlit as st

def render_scenario_selector(active_scenario: str) -> tuple:
    """
    Der alte, doppelte Dropdown wurde entfernt, da er mit dem globalen Gatekeeper in Tab 1
    kollidiert ist und die Werte überschrieben hat. Wir holen uns die Daten jetzt 
    direkt aus dem globalen Gedächtnis (loaded_params).
    """
    p = st.session_state.get('loaded_params', {})
    
    # Zeige dem User kurz an, dass er im richtigen Profil arbeitet
    if st.session_state.get('last_loaded_registry_name'):
        st.info(f"✏️ Bearbeite aktuell das Profil: **{st.session_state.get('last_loaded_registry_name')}**")
    else:
        st.info(f"🆕 Erstelle ein neues Profil: **{active_scenario}**")
        
    return active_scenario, p

def render_all_input_fields(p: dict, active_scenario: str, selected_template: str) -> dict:
    """
    Renders all physical sliders, inputs, and custom monthly tabs.
    Returns a consolidated dictionary of all user selections and synchronizes 
    them with the global state to prevent data loss.
    """
    # 1. GENERAL PARAMETERS
    col1, col2 = st.columns(2)
    with col1:
        monthly_consumption = st.number_input("Monthly Consumption (kWh)", min_value=100, value=int(p.get('monthly_consumption', 15000)), step=1000, key=f"m_cons_{active_scenario}")
        days_per_week = st.slider("Working Days per Week", 1, 7, int(p.get('days_per_week', 5)), key=f"d_week_{active_scenario}")
        hours_per_day = st.slider("Working Hours per Day", 1, 24, int(p.get('hours_per_day', 8)), key=f"h_day_{active_scenario}")
        base_load_pct = st.slider("Base Load Level (%)", 0, 100, int(p.get('base_load_pct', 15)), key=f"b_pct_{active_scenario}")
        
    with col2:
        num_connections = st.number_input("Number of Connections", min_value=1, value=int(p.get('num_connections', 1)), key=f"n_conn_{active_scenario}")
        amperage = st.number_input("Amperage per Connection (A)", min_value=16, value=int(p.get('amperage', 250)), step=10, key=f"amp_{active_scenario}")
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
        enable_noise = st.toggle("Enable realistic load fluctuations", value=bool(p.get('enable_noise', False)), key=f"noise_toggle_{active_scenario}")
        noise_percentage = st.slider("Fluctuation Intensity (%)", 1, 30, int(p.get('noise_percentage', 5)), key=f"noise_pct_{active_scenario}") if enable_noise else 0.0

    st.divider()

    # 2. MONTHLY CUSTOMIZATION
    use_custom_months = st.checkbox("Enable custom logic per month", value=bool(p.get('use_custom_months', False)), key=f"cust_month_toggle_{active_scenario}")
    monthly_configs = {}
    
    if use_custom_months:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        saved_configs = p.get("monthly_configs", {})
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            str_m_idx = str(m_idx)
            with tab:
                # Extrahiere gespeicherte Werte robust
                m_data = saved_configs.get(str_m_idx, saved_configs.get(m_idx, {}))
                if not isinstance(m_data, dict):
                    m_data = {}
                    
                s_cons = m_data.get("consumption", monthly_consumption)
                s_days = m_data.get("days", days_per_week)
                s_hours = m_data.get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh)", value=int(s_cons), key=f"c_{m_idx}_{active_scenario}")
                m_days = st.slider(f"Working Days", 1, 7, value=int(s_days), key=f"d_{m_idx}_{active_scenario}")
                m_hours = st.slider(f"Working Hours", 1, 24, value=int(s_hours), key=f"h_{m_idx}_{active_scenario}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    
    # 3. ANALYSIS CONFIGURATION
    col_g1, col_g2 = st.columns(2)
    grid_limit = col_g1.number_input("Set Grid Limit for Analysis (kW)", value=float(p.get('grid_limit', calculated_grid_kw)), step=10.0, key=f"grid_limit_field_{active_scenario}")
    col_raw = col_g2.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"), key=f"color_field_{active_scenario}")
    
    suggested_report_name = f"{selected_template}_Sub" if selected_template and selected_template != "[+ Create Brand New Profile]" else "Manual_Energy_Report"
    report_name = st.text_input("Report Title", value=p.get('report_name', suggested_report_name), key=f"rep_title_{active_scenario}")

    # Pack everything into a structured dictionary
    result_dict = {
        "monthly_consumption": monthly_consumption,
        "days_per_week": days_per_week,
        "hours_per_day": hours_per_day,
        "base_load_pct": base_load_pct,
        "num_connections": num_connections,
        "amperage": amperage,
        "calculated_grid_kw": calculated_grid_kw,
        "enable_noise": enable_noise,
        "noise_percentage": noise_percentage,
        "use_custom_months": use_custom_months,
        "monthly_configs": monthly_configs,
        "grid_limit": grid_limit,
        "col_raw": col_raw,
        "report_name": report_name,
        "is_manual": True
    }
    
    # --- THE MISSING FEEDBACK LOOP ---
    # Sofortiges Speichern der Eingaben in den globalen Zustand, damit sie bei Tab-Wechsel bleiben!
    if 'loaded_params' not in st.session_state:
        st.session_state['loaded_params'] = {}
        
    for k, v in result_dict.items():
        st.session_state['loaded_params'][k] = v

    return result_dict