# tabs/tab1_components/validation_components/save_handler.py
import streamlit as st
import pandas as pd
from tabs.tab1_components.financial_ui import render_financial_projection

def render_save_handler(df: pd.DataFrame, params: dict, active_scenario: str, statistical_anomalies: pd.DataFrame):
    """
    Renders the UI for saving the validated scenario to the global scenario vault.
    Supports establishing hierarchical parent-child relationships for sub-scenarios.
    """
    data_source = params.get('data_source', 'Unknown')
    grid_limit = params.get('grid_limit', 50.0)
    
    st.divider()
    st.write(f"### 💾 Save {data_source} Scenario")
    
    fin_meta = st.session_state.get('current_financial_metadata', {})
    render_financial_projection(df, fin_meta)
    st.write("---")
    
    # 1. Base Naming Suggestion
    default_scen_name = st.session_state.get('active_scenario_name', f"Scenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"New_{data_source}_Profile"
        
    scenario_name = st.text_input("Scenario Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    # --- NEU: Intelligenter Duplikats-Wächter ---
    vault = st.session_state.get('scenario_vault', {})
    existing_scenarios = list(vault.keys())
    name_exists = scenario_name in existing_scenarios
    save_disabled = False
    
    if name_exists:
        st.warning(f"⚠️ A scenario named '{scenario_name}' already exists. Please rename it to save as a copy, or check the box below to overwrite.")
        overwrite = st.checkbox("Overwrite existing scenario", value=False, key=f"ow_{active_scenario}")
        if not overwrite:
            save_disabled = True
    
    # 2. Hierarchical Stammbaum Architecture 
    col_type, col_parent = st.columns(2)
    with col_type:
        save_type = st.radio("Szenario-Typ:", options=["Haupt-Szenario (Basis)", "Sub-Szenario (Variante)"], horizontal=True, key=f"save_type_{active_scenario}")
        
    parent_scen = None
    with col_parent:
        if save_type == "Sub-Szenario (Variante)":
            if existing_scenarios:
                suggested_parent = st.session_state.get('last_loaded_registry_name')
                default_idx = existing_scenarios.index(suggested_parent) if suggested_parent in existing_scenarios else 0
                parent_scen = st.selectbox("Gehört zu Basis-Szenario:", options=existing_scenarios, index=default_idx, key=f"parent_select_{active_scenario}")
            else:
                st.warning("Keine Basis-Szenarien im Tresor. Wird als Haupt-Szenario gespeichert.")
                save_type = "Haupt-Szenario (Basis)"

    # 3. Execution Pipeline (mit disabled=save_disabled)
    if st.button(f"🚀 Securely Save Profile & Continue", type="primary", use_container_width=True, disabled=save_disabled, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        st.session_state['manual_df_ready'] = False 
        
        params['financial_metadata'] = fin_meta
        
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
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
            
        st.success(f"✅ Szenario '{scenario_name}' erfolgreich im Tresor gesichert! Du kannst nun fortfahren.")
        st.rerun()