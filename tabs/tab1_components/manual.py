# tabs/tab1_components/manual.py
import streamlit as st
from tabs.tab1_components.synthetic_load import synthetic_load
from data_models.scenarios import BaselineScenario
import pandas as pd

def render_manual_profile_generator():
    """
    Renders the UI for generating synthetic 15-min load profiles.
    Connects to the Scenario Registry to load/save complex configurations.
    """
    t = st.session_state.get('t', {})
    
    # --- LADE GEKLONTE PARAMETER ODER STANDARDS ---
    # p ist unser Paket mit den Werten aus dem Tresor (ist leer bei "New Scenario")
    p = st.session_state.get('loaded_params', {})
    
    st.subheader(t.get("manual_input_title", "Manual Load Profile"))
    st.write("Generate a baseline profile or modify a loaded scenario.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        monthly_consumption = st.number_input(
            "Monthly Consumption (kWh)", 
            min_value=100, value=int(p.get('monthly_consumption', 15000)), step=1000
        )
        days_per_week = st.slider(
            "Working Days per Week", 
            min_value=1, max_value=7, value=int(p.get('days_per_week', 5))
        )
        hours_per_day = st.slider(
            "Working Hours per Day", 
            min_value=1, max_value=24, value=int(p.get('hours_per_day', 8))
        )
        base_load_pct = st.slider(
            "Base Load Level (%)", 
            min_value=0, max_value=100, value=int(p.get('base_load_pct', 15)), step=1
        )
        
    with col2:
        st.write("#### Grid Connection")
        num_connections = st.number_input(
            "Number of Connections", min_value=1, value=int(p.get('num_connections', 1)), step=1
        )
        amperage = st.number_input(
            "Amperage per Connection (A)", min_value=16, value=int(p.get('amperage', 250)), step=10
        )
        
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
    st.divider()
    
    # --- NOISE SECTION ---
    st.write("### Profile Load Behavior")
    enable_noise = st.toggle("Enable realistic load fluctuations", value=p.get('enable_noise', False))
    noise_percentage = 0.0
    if enable_noise:
        noise_percentage = st.slider(
            "Fluctuation Intensity (%)", min_value=1, max_value=30, value=int(p.get('noise_percentage', 5)), step=1
        )
        
    st.divider()

    # --- ANOMALY INJECTOR ---
    st.write("### ⚡ Custom Load Anomalies & Peaks")
    st.info("Inject specific peaks, drops, or recurring events into your baseline.")
    
    if 'anomalies' not in st.session_state:
        st.session_state['anomalies'] = []
        
    with st.expander("➕ Add New Profile Anomaly"):
        c1, c2 = st.columns(2)
        with c1:
            a_mode = st.radio("Frequency", ["Single Date", "Recurring Weekday"])
        with c2:
            a_action = st.radio("Action", ["Add Load (+ kW)", "Set Absolute Load (= kW)"])
            
        c3, c4 = st.columns(2)
        with c3:
            if a_mode == "Single Date":
                a_date = st.date_input("Select Date")
                a_day = None
            else:
                day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
                a_day_str = st.selectbox("Select Weekday", list(day_map.keys()))
                a_day = day_map[a_day_str]
                a_date = None
                
            a_val = st.number_input("Value (kW)", min_value=0.0, value=50.0, step=10.0)
            
        with c4:
            a_start = st.time_input("Start Time", value=pd.to_datetime("08:00").time())
            a_end = st.time_input("End Time", value=pd.to_datetime("12:00").time())
            
        if st.button("Save Anomaly", type="secondary"):
            st.session_state['anomalies'].append({
                "mode": a_mode, "date": a_date, "day": a_day, "start": a_start, "end": a_end, "action": a_action, "value": a_val
            })
            st.success("Anomaly added!")
            st.rerun()

    if st.session_state['anomalies']:
        display_data = []
        for i, a in enumerate(st.session_state['anomalies']):
            when = str(a['date']) if a['mode'] == "Single Date" else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][a['day']]
            display_data.append({
                "ID": i + 1, "Type": a['mode'], "When": when, 
                "Time": f"{a['start'].strftime('%H:%M')} - {a['end'].strftime('%H:%M')}",
                "Action": "Add" if "Add" in a['action'] else "Set", "kW": a['value']
            })
        st.dataframe(display_data, use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear All Anomalies"):
            st.session_state['anomalies'] = []
            st.rerun()

    st.divider()

    # --- ADVANCED MONTHLY CUSTOMIZATION ---
    st.write("### Advanced: Custom Monthly Profiles")
    use_custom_months = st.checkbox("Enable custom logic per month", value=p.get('use_custom_months', False))
    
    monthly_configs = {}
    if use_custom_months:
        st.info("Values are pre-filled with your standard configuration or loaded memory.")
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        
        saved_configs = p.get("monthly_configs", {}) # Holt die Monats-Details aus dem Tresor
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            with tab:
                s_cons = saved_configs.get(m_idx, {}).get("consumption", monthly_consumption)
                s_days = saved_configs.get(m_idx, {}).get("days", days_per_week)
                s_hours = saved_configs.get(m_idx, {}).get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh) - {month_names[i]}", value=int(s_cons), key=f"c_{m_idx}")
                m_days = st.slider(f"Working Days - {month_names[i]}", min_value=1, max_value=7, value=int(s_days), key=f"d_{m_idx}")
                m_hours = st.slider(f"Working Hours - {month_names[i]}", min_value=1, max_value=24, value=int(s_hours), key=f"h_{m_idx}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    col_raw = st.color_picker(t.get("color_picker", "Chart Line Color"), "#A9A9A9", key="man_col")
    
    # ==========================================
    # SAVE & GENERATE ENGINE
    # ==========================================
    st.write("### 💾 Save Scenario")
    default_name = st.session_state.get('active_scenario_name', "New_Scenario_1")
    scenario_name = st.text_input("Enter Scenario Name to Save/Overwrite:", value=default_name)
    
    if st.button("Save & Generate Profile", type="primary", use_container_width=True):
        with st.spinner("Generating and saving profile..."):
            
            baseline = BaselineScenario(
                monthly_consumption = monthly_consumption,
                days_per_week = days_per_week,
                hours_per_day = hours_per_day,
                num_connections = num_connections,
                amperage = amperage,
                enable_noise = enable_noise,
                noise_percentage = noise_percentage
            )
            
            # 1. 12 Monate berechnen
            monthly_dfs = []
            for m_idx in range(1, 13):
                config = monthly_configs[m_idx]
                df_month = synthetic_load(
                    monthly_consumption = config["consumption"],
                    days_per_week = config["days"],
                    hours_per_day = config["hours"],
                    base_load_pct = base_load_pct, 
                    year = 2026,
                    month = m_idx,
                    noise_enabled = enable_noise,
                    noise_percentage = noise_percentage
                )
                monthly_dfs.append(df_month)
                
            annual_df = pd.concat(monthly_dfs, ignore_index=True)
            annual_df.sort_values("timestamp", inplace=True)
            annual_df.reset_index(drop=True, inplace=True)
            
            # 2. Anomalien anwenden (Post-Processing)
            if 'anomalies' in st.session_state and st.session_state['anomalies']:
                annual_df['time_only'] = annual_df['timestamp'].dt.time
                annual_df['date_only'] = annual_df['timestamp'].dt.date
                annual_df['day_only'] = annual_df['timestamp'].dt.dayofweek
                
                for a in st.session_state['anomalies']:
                    time_mask = (annual_df['time_only'] >= a['start']) & (annual_df['time_only'] <= a['end'])
                    day_mask = (annual_df['date_only'] == a['date']) if a['mode'] == "Single Date" else (annual_df['day_only'] == a['day'])
                    full_mask = time_mask & day_mask
                    
                    if "Add" in a['action']:
                        annual_df.loc[full_mask, 'consumption_kw'] += a['value']
                    else:
                        annual_df.loc[full_mask, 'consumption_kw'] = a['value']
                        
                annual_df.drop(columns=['time_only', 'date_only', 'day_only'], inplace=True)
            
            # 3. Daten in den aktiven Speicher legen (Für die Charts)
            baseline.load_profile = annual_df
            st.session_state['baseline_scenario'] = baseline
            st.session_state['filtered_data'] = annual_df
            st.session_state['grid_limit'] = calculated_grid_kw
            
            # 4. IN DEN TRESOR SCHREIBEN
            st.session_state['scenario_registry'][scenario_name] = {
                "df": annual_df,
                "grid_limit": calculated_grid_kw,
                "anomalies": st.session_state.get('anomalies', []),
                "params": {
                    "project_metadata": st.session_state.get('project_metadata', {}),
                    "monthly_consumption": monthly_consumption,
                    "days_per_week": days_per_week,
                    "hours_per_day": hours_per_day,
                    "base_load_pct": base_load_pct,
                    "num_connections": num_connections,
                    "amperage": amperage,
                    "enable_noise": enable_noise,
                    "noise_percentage": noise_percentage,
                    "use_custom_months": use_custom_months,
                    "monthly_configs": monthly_configs
                }
            }
            # Setze den aktiven Namen, damit das Dropdown oben ihn erkennt
            st.session_state['active_scenario_name'] = scenario_name
            
            st.success(f"Scenario '{scenario_name}' successfully generated and saved to registry!")
            st.rerun()