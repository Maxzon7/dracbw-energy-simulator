# tabs/tab1_components/validation_components/save_handler.py
import streamlit as st
import pandas as pd

def render_save_handler(df: pd.DataFrame, params: dict, active_scenario: str, statistical_anomalies: pd.DataFrame):
    """
    Renders the UI for saving the validated scenario to the global scenario vault.
    Supports establishing hierarchical parent-child relationships for sub-scenarios.
    """
    data_source = params.get('data_source', 'Unknown')
    grid_limit = params.get('grid_limit', 50.0)
    
    st.divider()
    st.write(f"### 💾 Save {data_source} Scenario")
    
    # 1. Base Naming Suggestion
    default_scen_name = st.session_state.get('active_scenario_name', f"Scenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"New_{data_source}_Profile"
        
    scenario_name = st.text_input("Scenario Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    # 2. Hierarchical Stammbaum Architecture
    vault = st.session_state.get('scenario_vault', {})
    existing_scenarios = list(vault.keys())
    
    col_type, col_parent = st.columns(2)
    with col_type:
        save_type = st.radio(
            "Scenario Type:", 
            options=["Main Scenario (Base)", "Sub-Scenario (Variant)"],
            horizontal=True,
            key=f"save_type_{active_scenario}"
        )
        
    parent_scen = None
    with col_parent:
        if save_type == "Sub-Scenario (Variant)":
            if existing_scenarios:
                # Suggest the currently loaded or edited scenario as default parent
                suggested_parent = st.session_state.get('last_loaded_registry_name')
                default_idx = existing_scenarios.index(suggested_parent) if suggested_parent in existing_scenarios else 0
                
                parent_scen = st.selectbox(
                    "Belongs to Base Scenario:", 
                    options=existing_scenarios,
                    index=default_idx,
                    key=f"parent_select_{active_scenario}"
                )
            else:
                st.warning("No base scenarios in the vault. Saving as Main Scenario.")
                save_type = "Main Scenario (Base)"

    # 3. Execution Pipeline
    if st.button(f"🚀 Securely Save Profile & Continue", type="primary", use_container_width=True, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        st.session_state['manual_df_ready'] = False 
        
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
        # Write the unified data package into the vault
        st.session_state['scenario_vault'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": statistical_anomalies.index.tolist() if not statistical_anomalies.empty else [],
            "data_source": data_source,
            "parent": parent_scen,
            "params": params
        }
        
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"✅ Scenario '{scenario_name}' successfully saved in the vault.")
        st.rerun()