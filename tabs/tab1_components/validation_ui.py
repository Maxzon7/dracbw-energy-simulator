# tabs/tab1_components/validation_ui.py
import streamlit as st
import pandas as pd

from tabs.tab1_components.validation_components.kpi_metrics import render_kpi_metrics
from tabs.tab1_components.validation_components.advanced_metrics import render_advanced_metrics
from tabs.tab1_components.validation_components.charts import render_multi_resolution_charts
from tabs.tab1_components.validation_components.save_handler import render_save_handler

def validate_and_process_data(data_source, uploaded_file, upload_params, syn_params, proj_params):
    df = None
    is_valid = False
    msg = ""

    if data_source == "Generate Synthetic Load":
        from tabs.tab1_components.synthetic_load import synthetic_load
        
        if not syn_params:
            return None, False, "Missing parameters."
        
        try:
            df = synthetic_load(
                monthly_consumption=syn_params.get('monthly_consumption', 50000),
                days_per_week=syn_params.get('days_per_week', 5),
                hours_per_day=syn_params.get('hours_per_day', 12),
                base_load_pct=syn_params.get('base_load_pct', 15),
                noise_enabled=syn_params.get('noise_enabled', True),
                noise_percentage=syn_params.get('noise_percentage', 5.0)
            )
            is_valid = True
            msg = "Synthetic data generated successfully."
        except Exception as e:
            msg = f"Error: {e}"
            
    elif data_source == "Upload CSV":
        if uploaded_file is None and 'filtered_data' not in st.session_state:
            msg = "Please upload CSV."
        else:
            is_valid = True
            msg = "CSV validation passed."

    return df, is_valid, msg



def render_validation_dashboard(df: pd.DataFrame, params: dict, active_scenario: str, is_edit_mode: bool):
    """
    UNIFIED VALIDATION ENGINE (The "Funnel" Orchestrator)
    Delegates the rendering of the validated dashboard to highly specialized sub-components
    to maintain clean architecture and file length limits.
    """
    st.divider()
    st.write("### ⚡ 3. Baseline Load Profile Validation")
    
    # Ensure correct datetime index/column format globally for all components
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # 1. Render Core Metrics and retrieve statistics needed for charts
    avg_load, statistical_anomalies = render_kpi_metrics(df, params)
    
    # 2. Render Advanced Assumptions (Only shows if profile is manual)
    render_advanced_metrics(df, params)
    
    # 3. Render the Multi-Tab Charting Station
    render_multi_resolution_charts(df, params, statistical_anomalies)
    
    # 4. Render the Vault Save Execution Block
    render_save_handler(df, params, active_scenario, statistical_anomalies)