# tabs/tab1_components/upload.py
import streamlit as st
from logic.energy_logic import load_and_clean_csv, process_consumption_data
import pandas as pd

def render_csv_upload_section():
    """
    Handles CSV file upload, parameter selection, data processing,
    and saving/overwriting within the global Scenario Registry.
    """
    t = st.session_state.get('t', {})
    p = st.session_state.get('loaded_params', {})
    
    st.subheader(t.get("header_data", "Upload Data"))
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
    
    # Dynamischer Report-Titel (Nutzt geladenen Namen oder den Dateinamen)
    default_report_name = p.get('report_name', "Energy_Report")
    if uploaded_file:
        default_report_name = f"Report_{uploaded_file.name.rsplit('.', 1)[0]}"
        
    report_name = st.text_input("Report Title", value=default_report_name)
    st.session_state['report_name'] = report_name
    
    st.subheader(t.get("header_grid", "Grid Parameters"))
    grid_limit = st.number_input(t.get("grid_limit", "Grid Limit (kW)"), value=float(p.get('grid_limit', 50.0)), step=5.0)
    
    # Auflösungs-Auswahl (wird mit geladenem Szenario vorausgefüllt)
    res_options = [1, 5, 15, 60]
    saved_res = p.get('resolution', 15)
    res_index = res_options.index(saved_res) if saved_res in res_options else 2
    res = st.selectbox(t.get("resolution", "Resolution (min)"), res_options, index=res_index)
    
    col_raw = st.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"))
    
    # Parameter für nachgelagerte Tabs im Arbeitsspeicher sichern
    st.session_state['grid_limit'] = grid_limit
    st.session_state['resolution'] = res
    st.session_state['col_raw'] = col_raw

    filtered_df = None

    # FALL A: Eine neue Datei wird gerade hochgeladen
    if uploaded_file:
        try:
            raw_df = load_and_clean_csv(uploaded_file)
            data = process_consumption_data(raw_df, res)
            
            min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
            selected_dates = st.date_input(t.get("analysis_period", "Analysis Period"), [min_date, max_date])
            
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
            
    # FALL B: Keine Datei hochgeladen, aber ein existierendes CSV-Szenario wurde oben ausgewählt
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'CSV':
        filtered_df = st.session_state['filtered_data']
        st.success(f"📦 Currently using active data from loaded scenario: '{st.session_state.get('active_scenario_name')}'")
        
    # --- SPEICHER-MODUL (SAVE ENGINE) ---
    if filtered_df is not None:
        st.divider()
        st.write("### 💾 Save Scenario")
        
        # Holt den aktiven Namen (damit man sofort überschreiben kann) oder schlägt Standard vor
        default_scen_name = st.session_state.get('active_scenario_name', "New_CSV_Scenario")
        if default_scen_name == "[+ Create New Scenario]":
            default_scen_name = "New_CSV_Scenario"
            
        scenario_name = st.text_input("Enter Scenario Name to Save/Overwrite:", value=default_scen_name)
        
        if st.button("Save & Process CSV Scenario", type="primary", use_container_width=True):
            # 1. In den aktiven Arbeitstisch legen
            st.session_state['filtered_data'] = filtered_df
            st.session_state['active_scenario_name'] = scenario_name
            
            # 2. In den Datentresor schreiben (Struktur identisch zu manual.py)
            if 'scenario_registry' not in st.session_state:
                st.session_state['scenario_registry'] = {}
                
            st.session_state['scenario_registry'][scenario_name] = {
                "df": filtered_df,
                "grid_limit": grid_limit,
                "anomalies": [], # CSV ignoriert Anomalien vorerst wie besprochen
                "params": {
                    "data_source": "CSV",
                    "report_name": report_name,
                    "grid_limit": grid_limit,
                    "resolution": res,
                    "col_raw": col_raw
                }
            }
            st.success(f"Scenario '{scenario_name}' successfully generated and saved to registry!")
            st.rerun()