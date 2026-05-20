# tabs/tab1_baseline.py
import streamlit as st
from tabs.tab1_components.toggle import render_data_source_toggle
from tabs.tab1_components.upload import render_csv_upload_section
from tabs.tab1_components.manual import render_manual_profile_generator
from tabs.tab1_components.chart import render_baseline_chart
from tabs.tab1_components.project_params import render_project_parameters

def render_tab1_baseline():
    """
    Master function to assemble Tab 1. 
    Includes the new Scenario Registry (Memory) for saving and loading profiles.
    """
    t = st.session_state.get('t', {})
    
    st.header(t.get("tab_baseline", "Baseline Profile"))
    
    # ==========================================
    # 0. SCENARIO REGISTRY
    # ==========================================
    if 'scenario_registry' not in st.session_state:
        st.session_state['scenario_registry'] = {}
        
    st.write("### 📁 Scenario Management")
    
    # Dropdown Liste aufbauen (Neu + Alle gespeicherten)
    saved_scenarios = ["[+ Create New Scenario]"] + list(st.session_state['scenario_registry'].keys())
    
    col_sel, col_load = st.columns([2, 1])
    with col_sel:
        selected_scenario = st.selectbox("Choose a saved Scenario or create a new one:", saved_scenarios)
        
    with col_load:
        st.write("") # Spacing alignment
        st.write("")
        if selected_scenario != "[+ Create New Scenario]":
            if st.button("Load Selected Scenario", use_container_width=True):
                # KLON-MAGIE: Wir holen die Parameter und das fertige Profil aus dem Tresor in den Arbeitsspeicher
                saved_data = st.session_state['scenario_registry'][selected_scenario]
                
                st.session_state['active_scenario_name'] = selected_scenario
                st.session_state['loaded_params'] = saved_data.get('params', {})
                st.session_state['anomalies'] = saved_data.get('anomalies', [])
                st.session_state['filtered_data'] = saved_data['df']
                st.session_state['grid_limit'] = saved_data['grid_limit']
                
                st.success(f"Scenario '{selected_scenario}' loaded successfully!")
                st.rerun()
        else:
            if st.button("Reset to Defaults (Clear Table)", use_container_width=True):
                # Putzt den Arbeitstisch komplett sauber
                st.session_state['active_scenario_name'] = "New_Scenario_1"
                st.session_state['loaded_params'] = {}
                st.session_state['anomalies'] = []
                if 'filtered_data' in st.session_state:
                    del st.session_state['filtered_data']
                st.rerun()
                
    st.divider()

    # ==========================================
    # NEU: 0.5 UNIVERSAL PROJECT PARAMETERS
    # ==========================================
    render_project_parameters()
    st.divider()

    # ==========================================
    # 1. UI RENDERING 
    # ==========================================
    data_mode = render_data_source_toggle()
    st.divider()
    
    col_input, col_chart = st.columns([1.2, 2.5])
    
    with col_input:
        if data_mode == t.get("csv_upload", "CSV Upload"):
            render_csv_upload_section()
        else:
            render_manual_profile_generator()

    with col_chart:
        render_baseline_chart()