# tabs/tab1_components/validation_components/advanced_metrics.py
import streamlit as st
import pandas as pd

def render_advanced_metrics(df: pd.DataFrame, params: dict):
    """
    Renders the 'Chameleon Dashboard'. Only visible if the profile contains manual metadata.
    """
    if not params.get("is_manual", False):
        return # Skip entirely for pure CSV uploads
        
    st.divider()
    st.write("### 🔍 Advanced Scenario Assumptions")
    st.info("The following parameters define the structural and behavioral baseline of this synthetic profile.")
    
    # 1. Infrastructure vs. Simulated Peak
    st.write("#### 1. Infrastructure vs. Simulated Peak")
    calc_limit = params.get("calculated_grid_kw", 0.0)
    peak_load = df['consumption_kw'].max() if df is not None else 0.0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Theoretical Grid Capacity", f"{calc_limit:,.1f} kW", 
              help=f"{params.get('num_connections', 1)} Connection(s) @ {params.get('amperage', 0)}A")
    c2.metric("Simulated Maximum Peak", f"{peak_load:.1f} kW")
    
    with c3:
        if peak_load > calc_limit:
            st.error(f"⚠️ Bottleneck: Peak exceeds physical capacity by {(peak_load - calc_limit):.1f} kW.")
        else:
            st.success("✅ Capacity Sufficient: Peak remains within physical grid limits.")
            
    # 2. Anomaly Gallery
    anomalies_list = params.get("anomalies", [])
    if anomalies_list:
        st.write("#### 2. Injected Profile Events (Anomalies)")
        anomaly_data = []
        for a in anomalies_list:
            a_type = getattr(a, 'anomaly_type', a.get('anomaly_type', 'N/A')) if isinstance(a, dict) else a.anomaly_type
            a_val = getattr(a, 'value_kw', a.get('value_kw', 0)) if isinstance(a, dict) else a.value_kw
            a_freq = getattr(a, 'frequency_type', a.get('frequency_type', 'N/A')) if isinstance(a, dict) else a.frequency_type
            a_start = getattr(a, 'start_time', a.get('start_time', 'N/A')) if isinstance(a, dict) else a.start_time
            a_end = getattr(a, 'end_time', a.get('end_time', 'N/A')) if isinstance(a, dict) else a.end_time
            
            type_label = {"additional_load": "Additional Peak (+)", "fixed_value": "Fixed Load (=)", "reduction": "Load Reduction (-)"}.get(a_type, a_type)
            
            anomaly_data.append({"Event Type": type_label, "Impact (kW)": a_val, "Frequency Pattern": str(a_freq).capitalize(), "Time Window": f"{a_start} - {a_end}"})
        st.dataframe(pd.DataFrame(anomaly_data), use_container_width=True, hide_index=True)

    # 3. Base Configuration Fingerprint
    with st.expander("⚙️ View General Configuration Fingerprint"):
        f_col1, f_col2, f_col3 = st.columns(3)
        f_col1.write(f"**Base Load Level:** {params.get('base_load_pct', 0)}%")
        f_col2.write(f"**Working Hours:** {params.get('hours_per_day', 0)}h / {params.get('days_per_week', 0)} Days")
        noise_status = f"Enabled ({params.get('noise_percentage', 0)}%)" if params.get('enable_noise', False) else "Disabled"
        f_col3.write(f"**Signal Noise:** {noise_status}")
        if params.get('use_custom_months', False):
            st.caption("Note: Custom monthly variations are active for this profile.")
            
    st.divider()