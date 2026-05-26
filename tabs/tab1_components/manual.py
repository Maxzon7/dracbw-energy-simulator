

# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd

# Import the clean calculation engine and sub-components
from tabs.tab1_components.manual_components.generation_logic import run_profile_generation
from tabs.tab1_components.manual_components.anomaly_manager import render_anomaly_manager
from tabs.tab1_components.validation_ui import render_validation_dashboard

def render_manual_builder(active_scenario: str, is_edit_mode: bool, p: dict):
    """
    Renders the parameters for the manual generator.
    Allows users to optionally select and load an existing scenario from the global vault
    to review or create modified sub-scenarios without automated baseline overrides.
    """
    t = st.session_state.get('t', {})
    
    st.write("### 🎛️ Advanced Manual Profile Generator")
    st.info("Configure your annual load profile. You can start fresh or load an existing scenario from the dropdown below.")
    
    # Ensure the global vault is initialized to prevent structural errors
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {}
        
    vault = st.session_state['scenario_vault']
    
    # ==========================================
    # --- STEP 0: OPTIONAL SCENARIO SELECTOR ---
    # ==========================================
    st.write("#### 📂 Load Configuration Template")
    
    # Filter for scenarios that were generated manually (they have the params backpack)
    available_templates = [name for name, data in vault.items() if data.get("params", {}).get("is_manual", False)]
    
    dropdown_options = ["[+ Create Brand New Profile]"] + available_templates
    selected_template = st.selectbox(
        "Select an existing scenario to view or edit:", 
        options=dropdown_options,
        key=f"template_select_{active_scenario}"
    )
    
    # If the user selects a template, we extract its configurations to pre-fill the inputs below
    if selected_template != "[+ Create Brand New Profile]":
        # Overwrite our parameter dictionary 'p' with the stored parameters from the vault
        p = vault[selected_template].get("params", {})
        st.success(f"📖 Loaded parameters from template: '{selected_template}'. Modifications will be saved as a new scenario unless overwritten.")
    
    st.divider()
    
    # ==========================================
    # --- STEP 1: PARAMETER INPUT FIELDS ---
    # ==========================================
    col1, col2 = st.columns(2)
    with col1:
        monthly_consumption = st.number_input(
            "Monthly Consumption (kWh)", 
            min_value=100, value=int(p.get('monthly_consumption', 15000)), step=1000,
            key=f"m_cons_{active_scenario}"
        )
        days_per_week = st.slider(
            "Working Days per Week", 1, 7, int(p.get('days_per_week', 5)),
            key=f"d_week_{active_scenario}"
        )
        hours_per_day = st.slider(
            "Working Hours per Day", 1, 24, int(p.get('hours_per_day', 8)),
            key=f"h_day_{active_scenario}"
        )
        base_load_pct = st.slider(
            "Base Load Level (%)", 0, 100, int(p.get('base_load_pct', 15)),
            key=f"b_pct_{active_scenario}"
        )
        
    with col2:
        num_connections = st.number_input(
            "Number of Connections", min_value=1, value=int(p.get('num_connections', 1)),
            key=f"n_conn_{active_scenario}"
        )
        amperage = st.number_input(
            "Amperage per Connection (A)", min_value=16, value=int(p.get('amperage', 250)), step=10,
            key=f"amp_{active_scenario}"
        )
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
        enable_noise = st.toggle(
            "Enable realistic load fluctuations", value=p.get('enable_noise', False),
            key=f"noise_toggle_{active_scenario}"
        )
        noise_percentage = st.slider(
            "Fluctuation Intensity (%)", 1, 30, int(p.get('noise_percentage', 5)),
            key=f"noise_pct_{active_scenario}"
        ) if enable_noise else 0.0

    st.divider()
    
    # ==========================================
    # --- STEP 2: ANOMALY MANAGEMENT ---
    # ==========================================
    # If a template was loaded, we inject its anomalies into the active session state if empty
    if selected_template != "[+ Create Brand New Profile]" and 'current_anomalies' in st.session_state:
        if not st.session_state['current_anomalies'] and p.get("anomalies"):
            st.session_state['current_anomalies'] = list(p.get("anomalies", []))

    render_anomaly_manager()
    st.divider()

    # ==========================================
    # --- STEP 3: MONTHLY CUSTOMIZATION ---
    # ==========================================
    use_custom_months = st.checkbox(
        "Enable custom logic per month", value=p.get('use_custom_months', False),
        key=f"cust_month_toggle_{active_scenario}"
    )
    monthly_configs = {}
    
    if use_custom_months:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        saved_configs = p.get("monthly_configs", {})
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            # Standardize string vs integer keys for JSON serialization safety
            str_m_idx = str(m_idx)
            with tab:
                s_cons = saved_configs.get(str_m_idx, saved_configs.get(m_idx, {})).get("consumption", monthly_consumption)
                s_days = saved_configs.get(str_m_idx, saved_configs.get(m_idx, {})).get("days", days_per_week)
                s_hours = saved_configs.get(str_m_idx, saved_configs.get(m_idx, {})).get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh)", value=int(s_cons), key=f"c_{m_idx}_{active_scenario}")
                m_days = st.slider(f"Working Days", 1, 7, value=int(s_days), key=f"d_{m_idx}_{active_scenario}")
                m_hours = st.slider(f"Working Hours", 1, 24, value=int(s_hours), key=f"h_{m_idx}_{active_scenario}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    
    # ==========================================
    # --- STEP 4: ANALYSIS CONFIGURATION ---
    # ==========================================
    col_g1, col_g2 = st.columns(2)
    grid_limit = col_g1.number_input(
        "Set Grid Limit for Analysis (kW)", value=float(p.get('grid_limit', calculated_grid_kw)), step=10.0,
        key=f"grid_limit_field_{active_scenario}"
    )
    col_raw = col_g2.color_picker(
        "Raw Load Color", p.get('col_raw', "#A9A9A9"),
        key=f"color_field_{active_scenario}"
    )
    
    # Default naming logic for saving/sub-scenarios
    suggested_report_name = f"{selected_template}_Sub" if selected_template != "[+ Create Brand New Profile]" else "Manual_Energy_Report"
    report_name = st.text_input("Report Title", value=p.get('report_name', suggested_report_name), key=f"rep_title_{active_scenario}")

    # ==========================================
    # --- STEP 5: GENERATION & TRICHTER PIPELINE ---
    # ==========================================
    df = None
    if st.button("⚙️ Generate / Update Profile", type="secondary", use_container_width=True, key=f"main_gen_btn_{active_scenario}"):
        with st.spinner("Calculating full annual profile with anomalies..."):
            df = run_profile_generation(
                monthly_consumption, days_per_week, hours_per_day, base_load_pct, 
                num_connections, amperage, enable_noise, noise_percentage, 
                use_custom_months, monthly_configs, calculated_grid_kw
            )
            st.session_state['filtered_data'] = df
            st.success("✅ Generated annual profile successfully!")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'Manual':
        df = st.session_state['filtered_data']

    if df is not None and not df.empty:
        params_to_pass = {
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "Manual",
            "is_manual": True,
            "report_name": report_name,
            "grid_limit": grid_limit,
            "resolution": 15,
            "col_raw": col_raw,
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
        
        # Route directly to the unified validation dashboard
        render_validation_dashboard(df, params_to_pass, active_scenario, is_edit_mode)