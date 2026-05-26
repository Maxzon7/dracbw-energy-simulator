# tabs/tab1_components/validation_components/save_handler.py
import streamlit as st
import pandas as pd

def render_save_handler(df: pd.DataFrame, params: dict, active_scenario: str, statistical_anomalies: pd.DataFrame):
    """
    Renders the UI for saving the validated scenario to the global scenario vault.
    """
    data_source = params.get('data_source', 'Unknown')
    grid_limit = params.get('grid_limit', 50.0)
    
    st.divider()
    st.write(f"### 💾 Save {data_source} Scenario")
    
    default_scen_name = st.session_state.get('active_scenario_name', f"Scenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"New_{data_source}_Profile"
        
    scenario_name = st.text_input("Scenario Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    if st.button(f"🚀 Securely Save Profile & Continue", type="primary", use_container_width=True, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        st.session_state['manual_df_ready'] = False # FIX: Anker einholen, Speichern war erfolgreich!
        
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
        st.session_state['scenario_vault'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": statistical_anomalies.index.tolist() if not statistical_anomalies.empty else [],
            "data_source": data_source,
            "params": params
        }
        
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"✅ Scenario '{scenario_name}' successfully secured in the vault! You may now proceed to the next tab.")
        st.rerun()