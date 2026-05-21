# tabs/tab1_components/upload.py
import streamlit as st
from logic.energy_logic import load_and_clean_csv, process_consumption_data
import pandas as pd

def render_csv_upload(active_scenario: str, is_edit_mode: bool, p: dict):
    """
    Renders the UI for uploading and parsing CSV data.
    Properly utilizes dynamic keys and overarching parameters to maintain state synchronization.
    """
    # 1. INITIALIZE TRANSLATION SYSTEM (Fixes the NameError)
    t = st.session_state.get('t', {}) 
    
    st.write("### 📁 CSV Upload Module")
    st.info("Upload your existing load profile data here.")
    
    st.subheader(t.get("header_data", "Upload Data"))
    
    # 2. UNIFIED FILE UPLOADER WITH DYNAMIC KEYS (Prevents widget stickiness & overlap)
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"], key=f"csv_upload_{active_scenario}")
    
    # Dynamic report name configuration (Uses loaded memory or extracts the file name)
    default_report_name = p.get('report_name', "Energy_Report")
    if uploaded_file:
        default_report_name = f"Report_{uploaded_file.name.rsplit('.', 1)[0]}"
        
    report_name = st.text_input("Report Title", value=default_report_name, key=f"report_title_{active_scenario}")
    st.session_state['report_name'] = report_name
    
    st.subheader(t.get("header_grid", "Grid Parameters"))
    grid_limit = st.number_input(
        t.get("grid_limit", "Grid Limit (kW)"), 
        value=float(p.get('grid_limit', 50.0)), 
        step=5.0,
        key=f"grid_limit_csv_{active_scenario}"
    )
    
    # Granular data interval resolution selector
    res_options = [1, 5, 15, 60]
    saved_res = p.get('resolution', 15)
    res_index = res_options.index(saved_res) if saved_res in res_options else 2
    res = st.selectbox(t.get("resolution", "Resolution (min)"), res_options, index=res_index, key=f"res_csv_{active_scenario}")
    
    col_raw = st.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"), key=f"col_raw_csv_{active_scenario}")
    
    # Park values inside global memory for charts and evaluation metrics
    st.session_state['grid_limit'] = grid_limit
    st.session_state['resolution'] = res
    st.session_state['col_raw'] = col_raw

    filtered_df = None

    # CASE A: A new user file is actively uploaded
    if uploaded_file:
        try:
            raw_df = load_and_clean_csv(uploaded_file)
            data = process_consumption_data(raw_df, res)
            
            min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
            selected_dates = st.date_input(
                t.get("analysis_period", "Analysis Period"), 
                [min_date, max_date],
                key=f"date_input_csv_{active_scenario}"
            )
            
            if len(selected_dates) == 2:
                filtered_df = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                   (data['timestamp'].dt.date <= selected_dates[1])]
                
                if len(filtered_df) > 0:
                    start_dt = filtered_df['timestamp'].min()
                    end_dt = filtered_df['timestamp'].max()
                    duration_days = (end_dt.date() - start_dt.date()).days + 1
                    
                    st.info(
                        f"📅 **Selected Timeframe:**\n\n"
                        f"• **Start:** {start_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"• **End:** {end_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"• **Total Duration:** {duration_days} days"
                    )
        except Exception as e:
            st.error(f"CSV Processing Error: {e}")
            
    # CASE B: No active upload file present, but a stored CSV baseline was selected from the gatekeeper
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'CSV':
        filtered_df = st.session_state['filtered_data']
        st.success(f"📦 Currently using active data from loaded scenario: '{st.session_state.get('active_scenario_name')}'")
        
    # --- SAVE & REGISTRY STORAGE ENGINE ---
    if filtered_df is not None:
        st.divider()
        st.write("### 💾 Save Scenario")
        
        default_scen_name = active_scenario if is_edit_mode else f"New_CSV_Scenario_{len(st.session_state.get('scenario_registry', {})) + 1}"
        scenario_name = st.text_input("Enter Scenario Name to Save/Overwrite:", value=default_scen_name, key=f"scen_name_csv_{active_scenario}")
        
        if st.button("Save & Process CSV Scenario", type="primary", use_container_width=True, key=f"save_btn_csv_{active_scenario}"):
            # 1. Update the active workspace data frames
            st.session_state['filtered_data'] = filtered_df
            st.session_state['active_scenario_name'] = scenario_name
            st.session_state['grid_limit'] = grid_limit
            
            # Create a mock shell class matching the manual generator footprint for downstream layout elements
            st.session_state['baseline_scenario'] = type('Baseline', (object,), {'load_profile': filtered_df})()
            
            # 2. Package directly into the global data vault
            if 'scenario_registry' not in st.session_state:
                st.session_state['scenario_registry'] = {}
                
            st.session_state['scenario_registry'][scenario_name] = {
                "df": filtered_df,
                "grid_limit": grid_limit,
                "anomalies": [], # CSV ignores custom manual anomalies as structurally designated
                "data_source": "CSV",
                "params": {
                    "project_metadata": st.session_state.get('current_project_metadata', {}),
                    "data_source": "CSV",
                    "report_name": report_name,
                    "grid_limit": grid_limit,
                    "resolution": res,
                    "col_raw": col_raw
                }
            }
            
            # Align synchronization flags so the main dashboard knows it's loaded safely
            st.session_state['last_loaded_registry_name'] = scenario_name
            st.session_state['loaded_params'] = st.session_state['scenario_registry'][scenario_name]['params']
            st.session_state['loaded_data_source'] = "CSV"
            
            st.success(f"Scenario '{scenario_name}' successfully generated and saved to registry!")
            st.rerun()