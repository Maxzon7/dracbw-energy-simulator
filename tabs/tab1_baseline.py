

# tabs/tab1_baseline.py
import streamlit as st
from tabs.tab1_components.project_params import render_project_params
from tabs.tab1_components.manual import render_manual_builder
from tabs.tab1_components.upload import render_csv_upload
from tabs.tab1_components.chart import render_baseline_chart

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
    mode = st.radio(
        "Scenario Mode Selector", 
        options=["🟢 Create a New Scenario", "✏️ Edit an Existing Scenario"], 
        horizontal=True
    )
    
    active_scenario = f"New_Scenario_{len(st.session_state['scenario_vault']) + 1}"
    is_edit_mode = False

    if mode == "✏️ Edit an Existing Scenario":
        if not st.session_state['scenario_vault']:
            st.warning("The registry is currently empty. Please create and save a new scenario first.")
            st.session_state['last_loaded_registry_name'] = None
            st.session_state['loaded_params'] = {}
            st.session_state['current_anomalies'] = []
            st.session_state['loaded_data_source'] = "Manual Profiler"
        else:
            options = list(st.session_state['scenario_vault'].keys())
            selected_scenario = st.selectbox("Select Stored Scenario to Load:", options)
            
            # Trigger state sync if selection changed
            if st.session_state.get('last_loaded_registry_name') != selected_scenario:
                st.session_state['last_loaded_registry_name'] = selected_scenario
                
                # Pull stored parameters into session state memory
                registry_item = st.session_state['scenario_vault'][selected_scenario]
                st.session_state['loaded_params'] = registry_item.get('params', {})
                st.session_state['current_anomalies'] = list(registry_item.get('anomalies', []))
                st.session_state['loaded_data_source'] = registry_item.get('data_source', 'Manual Profiler')
                st.rerun()
                
            active_scenario = selected_scenario
            is_edit_mode = True
    else:
        # Create New Scenario Mode
        if st.session_state.get('last_loaded_registry_name') is not None:
            st.session_state['last_loaded_registry_name'] = None
            st.session_state['loaded_params'] = {}
            st.session_state['current_anomalies'] = []
            st.session_state['loaded_data_source'] = "Manual Profiler"
            st.rerun()

    st.divider()

    # Centralize the loaded parameters to pass down to sub-modules
    p = st.session_state.get('loaded_params', {})

    # --- 2. GLOBAL PROJECT PARAMETERS ---
    st.write("### 🌍 Project Parameters")
    # Pass the loaded metadata subset and the dynamic key modifier
    project_metadata = render_project_params(p.get('project_metadata', {}), active_scenario)
    st.session_state['current_project_metadata'] = project_metadata

    st.divider()

    # --- 3. DATA SOURCE SELECTOR ---
    st.write("### 📊 Data Source")
    source_options = ['Manual Profiler', 'CSV Upload']
    default_source = st.session_state.get('loaded_data_source', 'Manual Profiler')
    
    # Safe index finding
    try:
        source_index = source_options.index(default_source)
    except ValueError:
        source_index = 0

    data_source = st.radio(
        "Select your Load Profile Source:", 
        options=source_options,
        index=source_index,
        horizontal=True,
        key=f"data_source_{active_scenario}"
    )
    st.session_state['current_data_source'] = data_source

    st.divider()

    # --- 4. RENDER THE CHOSEN GENERATOR ---
    # We pass the gatekeeper variables down so the sub-modules know what keys to use
    if data_source == 'Manual Profiler':
        render_manual_builder(active_scenario, is_edit_mode, p)
    else:
        render_csv_upload(active_scenario, is_edit_mode, p)
        
    st.divider()

    # --- 5. RENDER THE BASELINE CHART ---
    if 'baseline_scenario' in st.session_state and st.session_state['baseline_scenario']:
        render_baseline_chart()