
                


# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd
import datetime
import uuid
from tabs.tab1_components.synthetic_load import synthetic_load
from data_models.scenarios import BaselineScenario, AnomalyConfig

def render_manual_profile_generator(active_scenario: str, is_edit_mode: bool, p: dict):
    """
    Renders the UI for generating synthetic 15-min load profiles.
    The gatekeeper logic is now handled strictly top-down in tab1_baseline.py.
    """
    t = st.session_state.get('t', {})

    st.write("### ⚙️ Load Profile Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        monthly_consumption = st.number_input(
            "Monthly Consumption (kWh)", 
            min_value=100, 
            value=int(p.get('monthly_consumption', 15000)), 
            step=1000,
            key=f"m_cons_{active_scenario}"
        )
        days_per_week = st.slider(
            "Working Days per Week", 
            min_value=1, 
            max_value=7, 
            value=int(p.get('days_per_week', 5)),
            key=f"d_week_{active_scenario}"
        )
        hours_per_day = st.slider(
            "Working Hours per Day", 
            min_value=1, 
            max_value=24, 
            value=int(p.get('hours_per_day', 8)),
            key=f"h_day_{active_scenario}"
        )
        base_load_pct = st.slider(
            "Base Load Level (%)", 
            min_value=0, 
            max_value=100, 
            value=int(p.get('base_load_pct', 15)), 
            step=1,
            key=f"b_load_{active_scenario}"
        )
        
    with col2:
        st.write("#### Grid Connection Limit")
        num_connections = st.number_input(
            "Number of Connections", 
            min_value=1, 
            value=int(p.get('num_connections', 1)), 
            step=1,
            key=f"n_conn_{active_scenario}"
        )
        amperage = st.number_input(
            "Amperage per Connection (A)", 
            min_value=16, 
            value=int(p.get('amperage', 250)), 
            step=10,
            key=f"amp_{active_scenario}"
        )
        
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**Calculated Grid Limit**: ~{calculated_grid_kw:,.1f} kW")
        
    st.divider()
    
    # --- NOISE SECTION ---
    st.write("### Profile Load Behavior")
    enable_noise = st.toggle(
        "Enable realistic load fluctuations", 
        value=p.get('enable_noise', False),
        key=f"e_noise_{active_scenario}"
    )
    noise_percentage = 0.0
    if enable_noise:
        noise_percentage = st.slider(
            "Fluctuation Intensity (%)", 
            min_value=1, 
            max_value=30, 
            value=int(p.get('noise_percentage', 5)), 
            step=1,
            key=f"n_pct_{active_scenario}"
        )
        
    st.divider()

    # --- ANOMALY ENGINE CALL ---
    render_anomaly_manager()

    st.divider()

    # --- ADVANCED MONTHLY CUSTOMIZATION WITH DYNAMIC KEYS ---
    st.write("### Advanced: Custom Monthly Profiles")
    use_custom_months = st.checkbox(
        "Enable custom logic per month", 
        value=p.get('use_custom_months', False),
        key=f"u_cust_m_{active_scenario}"
    )
    
    monthly_configs = {}
    if use_custom_months:
        st.info("Values are pre-filled with your standard configuration or loaded memory.")
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        
        saved_configs = p.get("monthly_configs", {})
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            with tab:
                s_cons = saved_configs.get(m_idx, {}).get("consumption", monthly_consumption)
                s_days = saved_configs.get(m_idx, {}).get("days", days_per_week)
                s_hours = saved_configs.get(m_idx, {}).get("hours", hours_per_day)
                
                m_cons = st.number_input(f"Consumption (kWh) - {month_names[i]}", value=int(s_cons), key=f"c_{m_idx}_{active_scenario}")
                m_days = st.slider(f"Working Days - {month_names[i]}", min_value=1, max_value=7, value=int(s_days), key=f"d_{m_idx}_{active_scenario}")
                m_hours = st.slider(f"Working Hours - {month_names[i]}", min_value=1, max_value=24, value=int(s_hours), key=f"h_{m_idx}_{active_scenario}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}

    st.divider()
    
    # ==========================================
    # SAVE & GENERATE ENGINE
    # ==========================================
    st.write("### 💾 Save Scenario")
    default_name = active_scenario if is_edit_mode else f"New_Scenario_{len(st.session_state['scenario_registry']) + 1}"
    scenario_name = st.text_input("Enter Scenario Name to Save/Overwrite:", value=default_name, key=f"scen_name_{active_scenario}")
    
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
            
            # 1. Compute 12 Months
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
            
            # 2. Apply Upgraded Anomalies (Post-Processing)
            if 'current_anomalies' in st.session_state and st.session_state['current_anomalies']:
                annual_df['time_only'] = annual_df['timestamp'].dt.time
                annual_df['date_str'] = annual_df['timestamp'].dt.strftime("%Y-%m-%d")
                annual_df['day_name'] = annual_df['timestamp'].dt.day_name()
                
                for a in st.session_state['current_anomalies']:
                    a_start_time = datetime.datetime.strptime(a.start_time, "%H:%M").time()
                    a_end_time = datetime.datetime.strptime(a.end_time, "%H:%M").time()
                    
                    time_mask = (annual_df['time_only'] >= a_start_time) & (annual_df['time_only'] <= a_end_time)
                    
                    if a.frequency_type == 'regular':
                        day_mask = annual_df['day_name'].isin(a.regular_days)
                    elif a.frequency_type == 'block':
                        day_mask = (annual_df['date_str'] >= a.block_start_date) & (annual_df['date_str'] <= a.block_end_date)
                    elif a.frequency_type == 'random':
                        day_mask = annual_df['date_str'].isin(a.random_dates)
                    else:
                        day_mask = False
                        
                    full_mask = time_mask & day_mask
                    
                    if a.anomaly_type == 'additional_load':
                        annual_df.loc[full_mask, 'consumption_kw'] += a.value_kw
                    elif a.anomaly_type == 'fixed_value':
                        annual_df.loc[full_mask, 'consumption_kw'] = a.value_kw
                    elif a.anomaly_type == 'reduction':
                        annual_df.loc[full_mask, 'consumption_kw'] = (annual_df.loc[full_mask, 'consumption_kw'] - a.value_kw).clip(lower=0.0)
                        
                annual_df.drop(columns=['time_only', 'date_str', 'day_name'], inplace=True)
            
            # 3. Save to Active Session State (For current Charts)
            baseline.load_profile = annual_df
            st.session_state['baseline_scenario'] = baseline
            st.session_state['filtered_data'] = annual_df
            st.session_state['grid_limit'] = calculated_grid_kw
            
            # 4. Save structured metadata package to Scenario Registry
            # Incorporate project metadata and data source directly from the parent tab state
            st.session_state['scenario_registry'][scenario_name] = {
                "df": annual_df,
                "grid_limit": calculated_grid_kw,
                "anomalies": list(st.session_state.get('current_anomalies', [])),
                "data_source": st.session_state.get('current_data_source', 'Manual Profiler'),
                "params": {
                    "project_metadata": st.session_state.get('current_project_metadata', {}),
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
            
            # Reset the trigger track to ensure it stays selected properly
            st.session_state['last_loaded_registry_name'] = scenario_name
            st.session_state['loaded_params'] = st.session_state['scenario_registry'][scenario_name]['params']
            
            st.success(f"Scenario '{scenario_name}' successfully generated and saved to registry!")
            st.rerun()

def render_anomaly_manager():
    """
    Renders the Upgraded Anomaly & Event Manager UI components.
    """
    st.subheader("⚡ Upgraded Anomaly & Event Manager")
    st.info("Inject complex peaks, plant shutdowns, or completely random event blocks into your timeline.")
    
    if 'current_anomalies' not in st.session_state:
        st.session_state['current_anomalies'] = []
    if 'temp_random_dates' not in st.session_state:
        st.session_state['temp_random_dates'] = []

    with st.expander("➕ Create New Dynamic Anomaly", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            anomaly_type = st.selectbox("Load Behavior Profile", 
                options=['additional_load', 'fixed_value', 'reduction'],
                format_func=lambda x: {
                    'additional_load': "📈 Additional Peak Load (+ kW)",
                    'fixed_value': "📌 Set Fixed Constant Load (= kW)",
                    'reduction': "📉 Load Reduction / Shutdown (- kW)"
                }[x]
            )
            value_kw = st.number_input("Target Value (kW)", min_value=0.0, value=50.0, step=10.0)
            
        with col2:
            st.write("**Daily Active Window**")
            start_time = st.time_input("Start Time Raster", value=datetime.time(8, 0))
            end_time = st.time_input("End Time Raster", value=datetime.time(14, 0))

        st.divider()

        frequency_type = st.radio("Frequency & Distribution Pattern", 
            options=['regular', 'block', 'random'],
            format_func=lambda x: {
                'regular': "🔄 Recurring Pattern (Selected Weekdays)",
                'block': "📅 Continuous Block (Date Range Interval)",
                'random': "🎯 Random Selector (Custom Calendar Days)"
            }[x],
            horizontal=True
        )

        regular_days = []
        block_start = None
        block_end = None
        random_dates = []

        if frequency_type == 'regular':
            regular_days = st.multiselect("Select Target Weekdays", 
                options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            )
        elif frequency_type == 'block':
            date_range = st.date_input("Select Event Horizon Duration", 
                                       value=[datetime.date.today(), datetime.date.today() + datetime.timedelta(days=7)])
            if len(date_range) == 2:
                block_start, block_end = date_range
        elif frequency_type == 'random':
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                new_date = st.date_input("Pick Custom Target Date")
            with col_d2:
                st.write("") 
                st.write("") 
                if st.button("➕ Add Day"):
                    if new_date not in st.session_state['temp_random_dates']:
                        st.session_state['temp_random_dates'].append(new_date)
            
            if st.session_state['temp_random_dates']:
                st.write("**Target Days Registered:**")
                for d in st.session_state['temp_random_dates']:
                    st.markdown(f"- {d.strftime('%d.%m.%Y')}")
                random_dates = st.session_state['temp_random_dates']

        if st.button("💾 Save Anomaly to Profile Pipeline", type="primary", use_container_width=True):
            new_anomaly = AnomalyConfig(
                id=str(uuid.uuid4())[:8],
                anomaly_type=anomaly_type,
                value_kw=value_kw,
                frequency_type=frequency_type,
                start_time=start_time.strftime("%H:%M"),
                end_time=end_time.strftime("%H:%M"),
                regular_days=regular_days,
                block_start_date=block_start.strftime("%Y-%m-%d") if block_start else None,
                block_end_date=block_end.strftime("%Y-%m-%d") if block_end else None,
                random_dates=[d.strftime("%Y-%m-%d") for d in random_dates]
            )
            st.session_state['current_anomalies'].append(new_anomaly)
            st.session_state['temp_random_dates'] = [] 
            st.success("Anomaly added to baseline configuration pipeline!")
            st.rerun()

    if st.session_state['current_anomalies']:
        st.write("### 🗃️ Active Anomalies inside this Scenario Configuration")
        for idx, an in enumerate(st.session_state['current_anomalies']):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                type_lbl = {"additional_load": "+kW", "fixed_value": "=kW", "reduction": "-kW"}[an.anomaly_type]
                st.info(f"**{type_lbl}** ({an.value_kw} kW) | {an.start_time} - {an.end_time} | Type: *{an.frequency_type}*")
            with col_del:
                if st.button("❌ Remove", key=f"del_{an.id}", use_container_width=True):
                    st.session_state['current_anomalies'].pop(idx)
                    st.rerun()