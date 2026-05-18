import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from logic.energy_logic import load_and_clean_csv, process_consumption_data

def render_tab1_baseline():
    """
    Renders the Baseline interface. Handles both CSV uploads and synthetic 
    profile generation based on manual grid/peak parameters.
    """
    t = st.session_state['t']
    st.header(t["tab_baseline"])
    
    # --- DATA SOURCE TOGGLE ---
    data_mode = st.radio(
        t.get("data_source", "Data Source"), 
        [t.get("csv_upload", "CSV Upload"), t.get("manual_input", "Manual Input")], 
        horizontal=True
    )
    st.divider()
    
    # Adjust layout columns to give the chart more space
    col_input, col_chart = st.columns([1.2, 2.5])
    
    with col_input:
        if data_mode == t.get("csv_upload", "CSV Upload"):
            # ==========================================
            # 1. MODE: CSV UPLOAD
            # ==========================================
            st.subheader(t["header_data"])
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
            
            if uploaded_file:
                default_name = uploaded_file.name.rsplit('.', 1)[0]
                st.session_state['report_name'] = st.text_input("Report Title", value=f"Report_{default_name}")
            
            st.subheader(t["header_grid"])
            grid_limit = st.number_input(t["grid_limit"], value=50.0, step=5.0)
            res = st.selectbox(t["resolution"], [1, 5, 15, 60], index=2)
            col_raw = st.color_picker("Raw Load Color", "#A9A9A9")
            
            # Save CSV variables to session state
            st.session_state['grid_limit'] = grid_limit
            st.session_state['resolution'] = res
            st.session_state['col_raw'] = col_raw

        else:
            # ==========================================
            # 2. MODE: MANUAL SYNTHETIC DATA
            # ==========================================
            st.subheader(t.get("manual_input", "Manual Setup"))
            
            # Calculate grid limits mathematically
            c_conn, c_amp = st.columns(2)
            conns = c_conn.number_input(t.get("grid_connections", "Connections"), min_value=1, value=1, step=1)
            amps = c_amp.number_input(t.get("amperage", "Amperage (A)"), min_value=10, value=63, step=5)
            
            # Formel: P = (Connections * Amps * 400V * sqrt(3)) / 1000
            max_grid_kw = conns * amps * 400 * np.sqrt(3) / 1000.0
            st.metric(t.get("max_grid_capacity", "Max Grid Capacity"), f"{max_grid_kw:.1f} kW")
            
            base_load = st.number_input(t.get("base_load", "Base Load (kW)"), min_value=0.0, value=float(max_grid_kw * 0.2), step=5.0)
            
            st.subheader(t.get("peaks", "Peaks"))
            
            # Initialize dynamic peak list in session state
            if 'manual_peaks' not in st.session_state:
                st.session_state['manual_peaks'] = [{"power": max_grid_kw * 0.8, "duration": 2.0}]
                
            # Render input fields for each peak
            for i, peak in enumerate(st.session_state['manual_peaks']):
                p1, p2, p3 = st.columns([2, 2, 1])
                new_pow = p1.number_input(f"{t.get('peak_power', 'Power')} {i+1}", min_value=0.0, value=float(peak['power']), step=5.0, key=f"pow_{i}")
                new_dur = p2.number_input(f"{t.get('peak_duration', 'Duration')} {i+1}", min_value=0.25, max_value=24.0, value=float(peak['duration']), step=0.25, key=f"dur_{i}")
                
                # Update underlying logic
                st.session_state['manual_peaks'][i]['power'] = new_pow
                st.session_state['manual_peaks'][i]['duration'] = new_dur
                
                # Delete button with margin to align it visually with input boxes
                p3.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
                if p3.button("❌", key=f"del_{i}"):
                    st.session_state['manual_peaks'].pop(i)
                    st.rerun()
                    
            if st.button(f"➕ {t.get('add_peak', 'Add Peak')}"):
                st.session_state['manual_peaks'].append({"power": max_grid_kw * 0.5, "duration": 1.0})
                st.rerun()
                
            st.divider()
            col_raw = st.color_picker("Raw Load Color", "#A9A9A9", key="man_col")
            
            if st.button(t.get("generate_profile", "Generate Profile"), type="primary", use_container_width=True):
                # Lock variables into session state for Tab 2
                st.session_state['grid_limit'] = max_grid_kw
                st.session_state['resolution'] = 15 # Enforce 15-minute resolution for manual profiles
                st.session_state['col_raw'] = col_raw
                st.session_state['report_name'] = "Manual_Synthetic_Profile"
                
                # Build 24-hour array (96 intervals of 15 minutes)
                timestamps = pd.date_range("2026-01-01 00:00", periods=96, freq="15min")
                load_array = np.full(96, base_load)
                
                # Distribute peaks sequentially starting at 08:00 AM (Index 32)
                current_idx = 32
                for peak in st.session_state['manual_peaks']:
                    intervals = int(peak['duration'] * 4)
                    end_idx = min(current_idx + intervals, 96)
                    # Set the load to peak power (replacing base load for that duration)
                    load_array[current_idx:end_idx] = peak['power']
                    current_idx = end_idx
                    if current_idx >= 96: break # Stop if it exceeds 24 hours
                        
                # Create DataFrame identical to CSV output
                df_synthetic = pd.DataFrame({
                    "timestamp": timestamps,
                    "consumption_kw": load_array
                })
                
                st.session_state['filtered_data'] = df_synthetic
                st.success("Profile successfully generated!")

    with col_chart:
        # ==========================================
        # CHART RENDERING (Works for both modes)
        # ==========================================
        if 'filtered_data' in st.session_state and st.session_state['filtered_data'] is not None:
            # For CSV mode we still handle date filtering, for Manual we just take the 24h
            if data_mode == t.get("csv_upload", "CSV Upload") and uploaded_file:
                try:
                    raw_df = load_and_clean_csv(uploaded_file)
                    data = process_consumption_data(raw_df, st.session_state['resolution'])
                    
                    min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
                    selected_dates = st.date_input(t["analysis_period"], [min_date, max_date])
                    
                    if len(selected_dates) == 2:
                        st.session_state['filtered_data'] = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                                                 (data['timestamp'].dt.date <= selected_dates[1])]
                except Exception as e:
                    st.error(f"CSV Error: {e}")
                    
            # Render the universally stored filtered_data
            filtered_data = st.session_state['filtered_data']
            grid_limit = st.session_state.get('grid_limit', 50)
            col_raw_current = st.session_state.get('col_raw', "#A9A9A9")

            st.subheader(t["chart_load"])
            fig_load = go.Figure()
            fig_load.add_trace(go.Scatter(x=filtered_data['timestamp'], y=filtered_data['consumption_kw'], 
                                     name="Load Profile", line=dict(color=col_raw_current, width=1)))
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", name="Grid Limit")
            fig_load.update_layout(height=450, yaxis_title="kW", margin=dict(t=10, b=10))
            st.plotly_chart(fig_load, use_container_width=True)
        else:
            st.info("Upload a CSV or generate a manual profile on the left to view data.")