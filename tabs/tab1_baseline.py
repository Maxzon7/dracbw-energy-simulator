# tabs/tab1_baseline.py
import streamlit as st
from tabs.tab1_components.project_params import render_project_params
from tabs.tab1_components.manual import render_manual_builder
from tabs.tab1_components.upload import render_csv_upload
from tabs.tab1_components.chart import render_baseline_chart
from tabs.tab1_components.validation_ui import render_validation_dashboard
from tabs.tab1_components.financial_ui import render_financial_inputs

def render_tab1_baseline():
    """
    Master Tab 1: Manages the overarching Scenario Gatekeeper, 
    Global Project Parameters, Data Source Selection, and routes to sub-modules.
    """
    t = st.session_state.get('t', {})
    
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {}

    st.header("🏢 Baseline Configuration")
    st.write("Choose whether to build a fresh configuration or edit a previously stored scenario.")

    # --- 1. THE GATEKEEPER UI SELECTOR ---
    mode = st.radio("Scenario Mode Selector", options=["🟢 Create a New Scenario", "✏️ Edit an Existing Scenario"], horizontal=True)
    
    active_scenario = f"New_Scenario_{len(st.session_state['scenario_vault']) + 1}"
    is_edit_mode = False

    if mode == "✏️ Edit an Existing Scenario":
        if not st.session_state['scenario_vault']:
            st.warning("The vault is currently empty. Please create and save a new scenario first.")
            st.session_state['last_loaded_registry_name'] = None
            st.session_state['loaded_params'] = {}
            st.session_state['current_anomalies'] = []
            st.session_state['loaded_data_source'] = "Manual"
            st.session_state['manual_df_ready'] = False
        else:
            options = list(st.session_state['scenario_vault'].keys())
            selected_scenario = st.selectbox("Select Stored Scenario to Load:", options)
            
            if st.session_state.get('last_loaded_registry_name') != selected_scenario:
                st.session_state['last_loaded_registry_name'] = selected_scenario
                registry_item = st.session_state['scenario_vault'][selected_scenario]
                st.session_state['loaded_params'] = registry_item.get('params', {})
                st.session_state['current_anomalies'] = list(registry_item.get('params', {}).get('anomalies', []))
                st.session_state['loaded_data_source'] = registry_item.get('data_source', 'Manual')
                st.session_state['show_loaded_dashboard'] = False 
                st.session_state['manual_df_ready'] = False # FIX: Zurücksetzen bei Wechsel
                st.rerun()
                
            active_scenario = selected_scenario
            is_edit_mode = True
    else:
        if st.session_state.get('last_loaded_registry_name') is not None:
            st.session_state['last_loaded_registry_name'] = None
            st.session_state['loaded_params'] = {}
            st.session_state['current_anomalies'] = []
            st.session_state['loaded_data_source'] = "Manual"
            st.session_state['show_loaded_dashboard'] = False
            st.session_state['manual_df_ready'] = False # FIX: Zurücksetzen bei Wechsel
            st.rerun()

    st.divider()
    p = st.session_state.get('loaded_params', {})

    # --- 2. GLOBAL PROJECT PARAMETERS ---
    st.write("### 🌍 Project Parameters")
    project_metadata = render_project_params(p.get('project_metadata', {}), active_scenario)
    st.session_state['current_project_metadata'] = project_metadata

    # --- 2.5 ECONOMIC BASELINE (NEU) ---
    financial_metadata = render_financial_inputs(p.get('financial_metadata', {}), active_scenario)
    st.session_state['current_financial_metadata'] = financial_metadata
    st.divider()

    # --- 3. DATA SOURCE SELECTOR ---
    st.write("### 📊 Data Source")
    source_options = ['Manual Profiler', 'CSV Upload']
    internal_source = st.session_state.get('loaded_data_source', 'Manual')
    default_source = 'CSV Upload' if internal_source == 'CSV' else 'Manual Profiler'
    
    try:
        source_index = source_options.index(default_source)
    except ValueError:
        source_index = 0

    data_source = st.radio("Select your Load Profile Source:", options=source_options, index=source_index, horizontal=True, key=f"data_source_{active_scenario}")
    st.session_state['current_data_source'] = 'CSV' if data_source == 'CSV Upload' else 'Manual'
    st.divider()

    # --- 4. RENDER THE CHOSEN GENERATOR ---
    if data_source == 'Manual Profiler':
        render_manual_builder(active_scenario, is_edit_mode, p)
    else:
        render_csv_upload(active_scenario, is_edit_mode, p)
        if is_edit_mode and internal_source == 'CSV':
            st.divider()
            st.write("### 🔍 Saved CSV Profile Inspector")
            if st.button("📊 CSV-Diagramme & Analysen einblenden", type="primary", use_container_width=True):
                st.session_state['show_loaded_dashboard'] = True
            if st.session_state.get('show_loaded_dashboard', False):
                vault_item = st.session_state['scenario_vault'].get(active_scenario)
                if vault_item and vault_item.get('df') is not None:
                    render_validation_dashboard(vault_item['df'], vault_item.get('params', {}), active_scenario, is_edit_mode)

    st.divider()
    if 'baseline_scenario' in st.session_state and st.session_state['baseline_scenario']:
        render_baseline_chart()