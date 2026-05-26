# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd

# Die richtigen, komplexen Module importieren!
from tabs.tab1_components.manual_components.generation_logic import run_profile_generation
from tabs.tab1_components.manual_components.anomaly_manager import render_anomaly_manager
# Der Trichter
from tabs.tab1_components.validation_ui import render_validation_dashboard

def render_manual_builder(active_scenario: str, is_edit_mode: bool, p: dict):
    t = st.session_state.get('t', {})
    
    st.write("### 🎛️ Advanced Manual Profile Generator")
    st.info("Configure your annual load profile including connections, noise, and anomalies.")
    
    # --- 1. PARAMETER EINGABE (Das volle Programm) ---
    col1, col2 = st.columns(2)
    with col1:
        monthly_consumption = st.number_input("Monthly Consumption (kWh)", value=int(p.get('monthly_consumption', 15000)), step=1000)
        days_per_week = st.slider("Working Days per Week", 1, 7, int(p.get('days_per_week', 5)))
        hours_per_day = st.slider("Working Hours per Day", 1, 24, int(p.get('hours_per_day', 8)))
        base_load_pct = st.slider("Base Load Level (%)", 0, 100, int(p.get('base_load_pct', 15)))
        
    with col2:
        num_connections = st.number_input("Number of Connections", min_value=1, value=int(p.get('num_connections', 1)))
        amperage = st.number_input("Amperage per Connection (A)", min_value=16, value=int(p.get('amperage', 250)), step=10)
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
        enable_noise = st.toggle("Enable realistic load fluctuations", value=p.get('enable_noise', False))
        noise_percentage = st.slider("Fluctuation Intensity (%)", 1, 30, int(p.get('noise_percentage', 5))) if enable_noise else 0.0

    st.divider()
    
    # --- 2. ANOMALIEN ---
    render_anomaly_manager()
    st.divider()

    # --- 3. MONATS-LOGIK ---
    use_custom_months = st.checkbox("Enable custom logic per month", value=p.get('use_custom_months', False))
    monthly_configs = {}
    if use_custom_months:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        saved_configs = p.get("monthly_configs", {})
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            with tab:
                s_cons = saved_configs.get(str(m_idx), {}).get("consumption", monthly_consumption)
                s_days = saved_configs.get(str(m_idx), {}).get("days", days_per_week)
                s_hours = saved_configs.get(str(m_idx), {}).get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh)", value=int(s_cons), key=f"c_{m_idx}")
                m_days = st.slider(f"Working Days", 1, 7, value=int(s_days), key=f"d_{m_idx}")
                m_hours = st.slider(f"Working Hours", 1, 24, value=int(s_hours), key=f"h_{m_idx}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    
    # --- 4. TRICHTER-BASICS ---
    col_g1, col_g2 = st.columns(2)
    # Nutzt standardmäßig den berechneten Ampere-Wert als Netzlimit!
    grid_limit = col_g1.number_input("Set Grid Limit for Analysis (kW)", value=float(p.get('grid_limit', calculated_grid_kw)), step=10.0)
    col_raw = col_g2.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"))
    
    report_name = st.text_input("Report Title", value=p.get('report_name', "Manual_Energy_Report"))

    # --- 5. GENERIERUNG & ÜBERGABE AN DEN TRICHTER ---
    df = None
    if st.button("⚙️ Generate / Update Profile", type="secondary", use_container_width=True):
        with st.spinner("Calculating full annual profile with anomalies..."):
            
            # Wir rufen nur noch den Rechen-Motor auf. Er speichert nichts, er rechnet nur.
            df = run_profile_generation(
                monthly_consumption, days_per_week, hours_per_day, base_load_pct, 
                num_connections, amperage, enable_noise, noise_percentage, 
                use_custom_months, monthly_configs, calculated_grid_kw
            )
            st.session_state['filtered_data'] = df
            st.success("✅ Generated annual profile successfully!")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'Manual':
        df = st.session_state['filtered_data']

    # Die Magie: Wenn wir Daten haben, packen wir den Metadaten-Rucksack
    if df is not None and not df.empty:
        params_to_pass = {
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "Manual",
            "is_manual": True, # WICHTIGER FLAG! Damit weiß das Dashboard später Bescheid
            "report_name": report_name,
            "grid_limit": grid_limit,
            "resolution": 15, # Annual profiles sind hier meist 15 Min
            "col_raw": col_raw,
            # --- ERWEITERTE PARAMETER FÜR DAS DASHBOARD ---
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
            "anomalies": list(st.session_state.get('current_anomalies', []))
        }
        
        # Ab in den Trichter zur Vorschau und Speicherung!
        render_validation_dashboard(df, params_to_pass, active_scenario, is_edit_mode)