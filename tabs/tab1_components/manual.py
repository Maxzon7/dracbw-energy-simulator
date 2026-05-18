# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd
import numpy as np

def render_manual_profile_generator():
    """
    Renders the UI for generating synthetic 24h load profiles without historical data.
    Saves the synthetic dataframe to session_state['filtered_data'].
    """
    t = st.session_state['t']
    
    st.subheader(t.get("manual_input", "Manual Setup"))
    
    # 1. Grid Parameters
    c_conn, c_amp = st.columns(2)
    conns = c_conn.number_input(t.get("grid_connections", "Connections"), min_value=1, value=1, step=1)
    amps = c_amp.number_input(t.get("amperage", "Amperage (A)"), min_value=10, value=63, step=5)
    
    # P = (Connections * Amps * 400V * sqrt(3)) / 1000
    max_grid_kw = conns * amps * 400 * np.sqrt(3) / 1000.0
    st.metric(t.get("max_grid_capacity", "Max Grid Capacity"), f"{max_grid_kw:.1f} kW")
    
    base_load = st.number_input(t.get("base_load", "Base Load (kW)"), min_value=0.0, value=float(max_grid_kw * 0.2), step=5.0)
    
    # 2. Dynamic Peaks Management
    st.subheader(t.get("peaks", "Peaks"))
    
    if 'manual_peaks' not in st.session_state:
        st.session_state['manual_peaks'] = [{"power": max_grid_kw * 0.8, "duration": 2.0}]
        
    for i, peak in enumerate(st.session_state['manual_peaks']):
        p1, p2, p3 = st.columns([2, 2, 1])
        new_pow = p1.number_input(f"{t.get('peak_power', 'Power')} {i+1}", min_value=0.0, value=float(peak['power']), step=5.0, key=f"pow_{i}")
        new_dur = p2.number_input(f"{t.get('peak_duration', 'Duration')} {i+1}", min_value=0.25, max_value=24.0, value=float(peak['duration']), step=0.25, key=f"dur_{i}")
        
        st.session_state['manual_peaks'][i]['power'] = new_pow
        st.session_state['manual_peaks'][i]['duration'] = new_dur
        
        p3.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
        if p3.button("❌", key=f"del_{i}"):
            st.session_state['manual_peaks'].pop(i)
            st.rerun()
            
    if st.button(f"➕ {t.get('add_peak', 'Add Peak')}"):
        st.session_state['manual_peaks'].append({"power": max_grid_kw * 0.5, "duration": 1.0})
        st.rerun()
        
    st.divider()
    col_raw = st.color_picker("Raw Load Color", "#A9A9A9", key="man_col")
    
    # 3. Profile Generation Engine
    if st.button(t.get("generate_profile", "Generate Profile"), type="primary", use_container_width=True):
        st.session_state['grid_limit'] = max_grid_kw
        st.session_state['resolution'] = 15
        st.session_state['col_raw'] = col_raw
        st.session_state['report_name'] = "Manual_Synthetic_Profile"
        
        # Build 24h timeline
        timestamps = pd.date_range("2026-01-01 00:00", periods=96, freq="15min")
        load_array = np.full(96, base_load)
        
        # Inject peaks starting at 08:00 AM (Index 32)
        current_idx = 32
        for peak in st.session_state['manual_peaks']:
            intervals = int(peak['duration'] * 4)
            end_idx = min(current_idx + intervals, 96)
            load_array[current_idx:end_idx] = peak['power']
            current_idx = end_idx
            if current_idx >= 96: break
                
        # Export as standard dataframe format
        df_synthetic = pd.DataFrame({
            "timestamp": timestamps,
            "consumption_kw": load_array
        })
        
        st.session_state['filtered_data'] = df_synthetic
        st.success("Profile successfully generated!")