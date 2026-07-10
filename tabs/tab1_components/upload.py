# tabs/tab1_components/upload.py
import streamlit as st
import pandas as pd
from logic.energy_logic import load_and_clean_csv, process_consumption_data

TIME_SYNONYMS = ['timestamp', 'zeit', 'datum', 'date', 'time', 'uhrzeit', 'datetime', '#']
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

@st.dialog("📋 Open CSV File & Map Columns", width="large")
def render_csv_mapping_dialog(raw_df, active_scenario):
    st.write("Here is a preview of the first few rows of your CSV file. Please map the columns:")
    st.dataframe(raw_df.head(5), use_container_width=True)
    
    raw_cols = list(raw_df.columns)
    guessed_time, guessed_power = guess_columns(raw_cols)
    
    time_idx = raw_cols.index(guessed_time) if guessed_time in raw_cols else 0
    default_power_list = [guessed_power] if guessed_power in raw_cols else []
    
    # Intelligent automatic guessing for separate time-of-day columns (e.g. Dutch grid data)
    tod_options = ["None (Combined Column)"] + raw_cols
    tod_idx = 0
    for idx, col in enumerate(raw_cols):
        if col.lower() in ['code', 'uhrzeit', 'time_of_day'] and col != guessed_time:
            tod_idx = idx + 1 # Offset by 1 due to the "None" placeholder
            break
    
    st.divider()
    col_map1, col_map2, col_map3 = st.columns(3)
    
    # Primary date/time picker
    final_time_col = col_map1.selectbox("🕒 Primary Date Column", options=raw_cols, index=time_idx, key=f"dlg_time_{active_scenario}")
    
    # NEW: Explicit user control for split time-of-day columns
    final_tod_col = col_map1.selectbox("🕒 Time of Day Column (Optional)", options=tod_options, index=tod_idx, key=f"dlg_tod_{active_scenario}")
    
    final_power_cols = col_map2.multiselect("⚡ Power Column(s) (Select all that apply)", options=raw_cols, default=default_power_list, key=f"dlg_pwr_{active_scenario}")
    
    # NEW: Expanded selection matrix to natively support energy-to-power conversions for kWh files
    unit_mode = col_map3.selectbox("📊 Data Unit in File", options=["Kilowatt (kW)", "Watt (W)", "Kilowatt-hour (kWh)"], index=0, key=f"dlg_unit_{active_scenario}")
    
    final_unit = "kW"
    if "Watt (W)" in unit_mode:
        final_unit = "W"
    elif "Kilowatt-hour (kWh)" in unit_mode:
        final_unit = "kWh"
    
    st.divider()
    if not final_power_cols:
        st.warning("Please select at least one power column to proceed.")
        
    if st.button("🤝 Confirm Mapping & Load Data", type="primary", use_container_width=True, key=f"dlg_confirm_{active_scenario}", disabled=len(final_power_cols)==0):
        st.session_state[f"mapped_time_col_{active_scenario}"] = final_time_col
        st.session_state[f"mapped_time_of_day_col_{active_scenario}"] = None if final_tod_col == "None (Combined Column)" else final_tod_col
        st.session_state[f"mapped_power_col_{active_scenario}"] = final_power_cols 
        st.session_state[f"mapped_unit_{active_scenario}"] = final_unit
        st.session_state[f"csv_mapping_ready_{active_scenario}"] = True
        st.rerun()

def render_upload_ui(active_scenario: str, p: dict):
    """
    Renders the UI for uploading and mapping CSVs.
    Returns: uploaded_file, filtered_df, params_to_pass
    """
    t = st.session_state.get('t', {}) 
    
    st.write("### 📁 CSV Upload Module")
    st.info("Upload any load profile here. Then click the button to map the columns.")
    
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"], key=f"csv_upload_{active_scenario}")
    
    default_report_name = p.get('report_name', "Energy_Report")
    if uploaded_file:
        default_report_name = f"Report_{uploaded_file.name.rsplit('.', 1)[0]}"
        
    report_name = st.text_input("Report Title", value=default_report_name, key=f"report_title_{active_scenario}")
    
    st.subheader(t.get("header_grid", "Grid Parameters"))
    grid_limit = st.number_input("Grid Limit (kW) [0 = Unlimited]", value=float(p.get('grid_limit', 50.0)), min_value=0.0, step=5.0, key=f"grid_limit_csv_{active_scenario}")
    
    res_options = [1, 5, 15, 60]
    saved_res = p.get('resolution', 15)
    res_index = res_options.index(saved_res) if saved_res in res_options else 2
    res = st.selectbox(t.get("resolution", "Resolution (min)"), res_options, index=res_index, key=f"res_csv_{active_scenario}")
    
    col_raw = st.color_picker("Raw Load Color", p.get('col_raw', "#A9A9A9"), key=f"col_raw_csv_{active_scenario}")
    
    sub_meter_configs = {}
    mapped_power_cols = st.session_state.get(f"mapped_power_col_{active_scenario}", [])
    
    if isinstance(mapped_power_cols, list) and len(mapped_power_cols) > 0:
        with st.expander("🎨 Customize Sub-Meters (Names & Colors)", expanded=False):
            default_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
            saved_configs = p.get('sub_meter_configs', {})
            
            for idx, meter in enumerate(mapped_power_cols):
                c1, c2 = st.columns([3, 1])
                saved_meter_conf = saved_configs.get(meter, {})
                def_name = saved_meter_conf.get('name', meter)
                def_color = saved_meter_conf.get('color', default_colors[idx % len(default_colors)])
                
                custom_name = c1.text_input(f"Name: {meter}", value=def_name, key=f"name_{meter}_{active_scenario}")
                custom_color = c2.color_picker(f"Color: {meter}", value=def_color, key=f"color_{meter}_{active_scenario}")
                sub_meter_configs[meter] = {'name': custom_name, 'color': custom_color}
    
    filtered_df = None
    params_to_pass = {}

    if uploaded_file:
        try:
            uploaded_file.seek(0)
            raw_df = load_and_clean_csv(uploaded_file)
            
            st.write("##### 🔍 Data Preview (First 5 Rows)")
            st.dataframe(raw_df.head(5), use_container_width=True)
            
            st.write("")
            if st.button("⚙️ Configure & Map Columns", type="secondary", use_container_width=True, key=f"open_popup_{active_scenario}"):
                render_csv_mapping_dialog(raw_df, active_scenario)
            
            if st.session_state.get(f"csv_mapping_ready_{active_scenario}", False):
                user_time_col = st.session_state[f"mapped_time_col_{active_scenario}"]
                user_tod_col = st.session_state.get(f"mapped_time_of_day_col_{active_scenario}", None)
                user_power_col = st.session_state[f"mapped_power_col_{active_scenario}"]
                user_unit = st.session_state[f"mapped_unit_{active_scenario}"]
                
                # FIX: Explicitly passing the user-selected time-of-day column to the analytical core
                data = process_consumption_data(
                    df=raw_df, 
                    interval_minutes=res, 
                    time_col=user_time_col, 
                    time_of_day_col=user_tod_col, 
                    power_col=user_power_col, 
                    unit=user_unit
                )
                
                min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
                selected_dates = st.date_input(t.get("analysis_period", "Analysis Period"), [min_date, max_date], key=f"dates_csv_{active_scenario}")
                
                if len(selected_dates) == 2:
                    filtered_df = data[(data['timestamp'].dt.date >= selected_dates[0]) & (data['timestamp'].dt.date <= selected_dates[1])]
                    
        except Exception as e:
            st.error(f"CSV Reading Error: {e}")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'CSV':
        filtered_df = st.session_state['filtered_data']
        st.success(f"📦 Currently using active data from loaded scenario: '{st.session_state.get('active_scenario_name')}'")
        
    params_to_pass = {
        "data_source": "CSV",
        "report_name": report_name,
        "grid_limit": grid_limit,
        "resolution": res,
        "col_raw": col_raw,
        "sub_meter_configs": sub_meter_configs
    }
        
    return uploaded_file, filtered_df, params_to_pass