# tabs/tab1_components/upload.py
import streamlit as st
import pandas as pd
from logic.energy_logic import load_and_clean_csv, process_consumption_data

# ---> HIER IST DER NEUE IMPORT <---
from tabs.tab1_components.validation_ui import render_validation_dashboard

TIME_SYNONYMS = ['timestamp', 'zeit', 'datum', 'date', 'time', 'uhrzeit', 'datetime']
POWER_SYNONYMS = ['kw', 'consumption', 'leistung', 'wirkleistung', 'power', 'load', 'verbrauch', 'watt', 'p_tot']

def guess_columns(raw_cols):
    time_col, power_col = None, None
    for col in raw_cols:
        lower_col = col.lower()
        if not time_col and any(syn in lower_col for syn in TIME_SYNONYMS):
            time_col = col
        if not power_col and any(syn in lower_col for syn in POWER_SYNONYMS):
            power_col = col
    return time_col, power_col

@st.dialog("📋 CSV-Datei öffnen & Spalten zuordnen", width="large")
def render_csv_mapping_dialog(raw_df, active_scenario):
    st.write("Hier ist ein Blick in die ersten Zeilen deiner CSV-Datei. Bitte ordne die Spalten zu:")
    st.dataframe(raw_df.head(5), use_container_width=True)
    
    raw_cols = list(raw_df.columns)
    guessed_time, guessed_power = guess_columns(raw_cols)
    
    time_idx = raw_cols.index(guessed_time) if guessed_time in raw_cols else 0
    power_idx = raw_cols.index(guessed_power) if guessed_power in raw_cols else (1 if len(raw_cols) > 1 else 0)
    
    st.divider()
    col_map1, col_map2, col_map3 = st.columns(3)
    final_time_col = col_map1.selectbox("🕒 Zeit/Datum Spalte", options=raw_cols, index=time_idx, key=f"dlg_time_{active_scenario}")
    final_power_col = col_map2.selectbox("⚡ Leistung Spalte", options=raw_cols, index=power_idx, key=f"dlg_pwr_{active_scenario}")
    unit_mode = col_map3.selectbox("📊 Dateneinheit im File", options=["Kilowatt (kW)", "Watt (W)"], index=0, key=f"dlg_unit_{active_scenario}")
    
    final_unit = "kW" if "Kilowatt" in unit_mode else "W"
    
    st.divider()
    if st.button("🤝 Zuordnung bestätigen & Einlesen", type="primary", use_container_width=True, key=f"dlg_confirm_{active_scenario}"):
        st.session_state[f"mapped_time_col_{active_scenario}"] = final_time_col
        st.session_state[f"mapped_power_col_{active_scenario}"] = final_power_col
        st.session_state[f"mapped_unit_{active_scenario}"] = final_unit
        st.session_state[f"csv_mapping_ready_{active_scenario}"] = True
        st.rerun()

def render_csv_upload(active_scenario: str, is_edit_mode: bool, p: dict):
    t = st.session_state.get('t', {}) 
    
    st.write("### 📁 CSV Upload Module")
    st.info("Lade hier ein beliebiges Lastprofil hoch. Klicke danach auf den Button, um die Spalten zuzuordnen.")
    
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"], key=f"csv_upload_{active_scenario}")
    
    default_report_name = p.get('report_name', "Energy_Report")
    if uploaded_file:
        default_report_name = f"Report_{uploaded_file.name.rsplit('.', 1)[0]}"
        
    report_name = st.text_input("Report Title", value=default_report_name, key=f"report_title_{active_scenario}")
    
    st.subheader(t.get("header_grid", "Grid Parameters"))
    grid_limit = st.number_input(t.get("grid_limit", "Grid Limit (kW)"), value=float(p.get('grid_limit', 50.0)), step=5.0, key=f"grid_limit_csv_{active_scenario}")
    
    res_options = [1, 5, 15, 60]
    saved_res = p.get('resolution', 15)
    res_index = res_options.index(saved_res) if saved_res in res_options else 2
    res = st.selectbox(t.get("resolution", "Resolution (min)"), res_options, index=res_index, key=f"res_csv_{active_scenario}")
    
    col_raw = st.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"), key=f"col_raw_csv_{active_scenario}")
    
    filtered_df = None

    if uploaded_file:
        try:
            uploaded_file.seek(0)
            raw_df = load_and_clean_csv(uploaded_file)
            
            st.write("")
            if st.button("🔍 Datei öffnen & Spalten zuordnen", type="secondary", use_container_width=True, key=f"open_popup_{active_scenario}"):
                render_csv_mapping_dialog(raw_df, active_scenario)
            
            if st.session_state.get(f"csv_mapping_ready_{active_scenario}", False):
                user_time_col = st.session_state[f"mapped_time_col_{active_scenario}"]
                user_power_col = st.session_state[f"mapped_power_col_{active_scenario}"]
                user_unit = st.session_state[f"mapped_unit_{active_scenario}"]
                
                data = process_consumption_data(df=raw_df, interval_minutes=res, time_col=user_time_col, power_col=user_power_col, unit=user_unit)
                
                min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
                selected_dates = st.date_input(t.get("analysis_period", "Analysis Period"), [min_date, max_date], key=f"dates_csv_{active_scenario}")
                
                if len(selected_dates) == 2:
                    filtered_df = data[(data['timestamp'].dt.date >= selected_dates[0]) & (data['timestamp'].dt.date <= selected_dates[1])]
        except Exception as e:
            st.error(f"CSV Einlese-Fehler: {e}")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'CSV':
        filtered_df = st.session_state['filtered_data']
        st.success(f"📦 Currently using active data from loaded scenario: '{st.session_state.get('active_scenario_name')}'")
        
    # ==========================================
    # DIE MAGIE: ÜBERGABE AN DEN TRICHTER
    # ==========================================
    if filtered_df is not None and not filtered_df.empty:
        # Wir schnüren ein Paket mit allen Parametern
        params_to_pass = {
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "CSV",
            "report_name": report_name,
            "grid_limit": grid_limit,
            "resolution": res,
            "col_raw": col_raw
        }
        # Wir rufen die externe Station auf. Der Upload-Code bleibt extrem kurz!
        render_validation_dashboard(filtered_df, params_to_pass, active_scenario, is_edit_mode)