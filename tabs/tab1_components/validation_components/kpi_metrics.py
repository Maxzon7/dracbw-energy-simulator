# tabs/tab1_components/validation_components/kpi_metrics.py
import streamlit as st
import pandas as pd

def render_kpi_metrics(df: pd.DataFrame, params: dict):
    """
    Calculates and renders the core performance indicators and grid breach analytics.
    Returns the calculated average load and statistical anomalies for downstream charts.
    """
    grid_limit = params.get('grid_limit', 50.0)
    res = params.get('resolution', 15)
    
    st.write("#### 📊 System Performance Indicators")
    
    # Mathematical Calculations
    hours_factor = res / 60.0
    total_energy_kwh = df['consumption_kw'].sum() * hours_factor
    peak_load = df['consumption_kw'].max()
    avg_load = df['consumption_kw'].mean()
    
    # Grid Breach Analytics
    breach_mask = df['consumption_kw'] > grid_limit
    breach_df = df[breach_mask]
    hours_over_limit = len(breach_df) * hours_factor
    exceeded_energy_kwh = ((breach_df['consumption_kw'] - grid_limit) * hours_factor).sum()
    
    # Render Row 1
    m_row1_1, m_row1_2, m_row1_3 = st.columns(3)
    m_row1_1.metric("Data Resolution", f"{res} min")
    m_row1_2.metric("Maximum Peak Load", f"{peak_load:.1f} kW")
    m_row1_3.metric("Total Annual Energy", f"{total_energy_kwh:,.0f} kWh")
    
    # Render Row 2
    m_row2_1, m_row2_2, m_row2_3 = st.columns(3)
    m_row2_1.metric("Average Base Load", f"{avg_load:.1f} kW")
    
    if hours_over_limit > 0:
        m_row2_2.metric("Grid Limit Overload Duration", f"{hours_over_limit:,.1f} Hours", delta=f"{len(breach_df)} intervals", delta_color="inverse")
        m_row2_3.metric("Total Overload Energy Deficit", f"{exceeded_energy_kwh:,.0f} kWh", delta="Requires Storage", delta_color="inverse")
    else:
        m_row2_2.metric("Grid Limit Overload Duration", "0.0 Hours", delta="No Breaches")
        m_row2_3.metric("Total Overload Energy Deficit", "0 kWh", delta="Grid Safe")

    # Statistical Outlier Scanner (Z-Score)
    std_dev = df['consumption_kw'].std()
    z_scores = (df['consumption_kw'] - avg_load) / std_dev if std_dev > 0 else 0
    statistical_anomalies = df[z_scores > 3.0] 
    
    st.divider()
    if not statistical_anomalies.empty:
        st.warning(f"⚠️ {len(statistical_anomalies)} unusual load peaks detected. Verify grid exposure in charts below.")
    else:
        st.success("✅ Profile validated. No extreme statistical anomalies detected.")
        
    return avg_load, statistical_anomalies