# tabs/tab1_components/manual_components/generation_logic.py
import streamlit as st
import pandas as pd
import datetime
from tabs.tab1_components.synthetic_load import synthetic_load
from data_models.scenarios import BaselineScenario

def run_profile_generation(scenario_name, active_scenario, monthly_consumption, days_per_week, 
                           hours_per_day, base_load_pct, num_connections, amperage, 
                           enable_noise, noise_percentage, use_custom_months, monthly_configs, calculated_grid_kw):
    """
    Executes the 34,560 interval generation loop, injects advanced anomalies, 
    and packages results securely into the overarching application registry.
    """
    baseline = BaselineScenario(
        monthly_consumption = monthly_consumption,
        days_per_week = days_per_week,
        hours_per_day = hours_per_day,
        num_connections = num_connections,
        amperage = amperage,
        enable_noise = enable_noise,
        noise_percentage = noise_percentage
    )
    
    # 1. Compute 12 Months sequentially
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
    
    # 3. Save directly to Active Session State (For current Charts)
    baseline.load_profile = annual_df
    st.session_state['baseline_scenario'] = baseline
    st.session_state['filtered_data'] = annual_df
    st.session_state['grid_limit'] = calculated_grid_kw
    
    # 4. Save structured metadata package to Scenario Registry
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
    
    # Synchronize tracking states
    st.session_state['last_loaded_registry_name'] = scenario_name
    st.session_state['loaded_params'] = st.session_state['scenario_registry'][scenario_name]['params']