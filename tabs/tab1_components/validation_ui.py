# tabs/tab1_components/validation_ui.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_validation_dashboard(df: pd.DataFrame, params: dict, active_scenario: str, is_edit_mode: bool):
    """
    UNIFIED VALIDATION ENGINE (The "Funnel")
    Takes finalized, standardized load profile data (manual or CSV) 
    and renders an identical UX surface for validation, charting, and storage.
    """
    # Safely unpack core parameters
    grid_limit = params.get('grid_limit', 50.0)
    res = params.get('resolution', 15)
    col_raw = params.get('col_raw', '#A9A9A9')
    data_source = params.get('data_source', 'Unknown')
    
    st.divider()
    st.write("### ⚡ 3. Baseline Load Profile Validation")
    
    # 1. Mathematical KPI Calculation
    intervals_per_hour = 60 / res
    total_energy_kwh = df['consumption_kw'].sum() / intervals_per_hour
    peak_load = df['consumption_kw'].max()
    avg_load = df['consumption_kw'].mean()
    
    # 2. Universal 4-Column KPI Layout
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resolution", f"{res} min")
    col2.metric("Peak Load", f"{peak_load:.1f} kW")
    col3.metric("Total Load", f"{total_energy_kwh:,.0f} kWh")
    col4.metric("Avg Base Load", f"{avg_load:.1f} kW")

    # ==========================================
    # --- CHAMELEON DASHBOARD: ADVANCED METRICS ---
    # ==========================================
    # Check if the data came from the manual generator (has the metadata backpack)
    if params.get("is_manual", False):
        st.divider()
        st.write("### 🔍 Advanced Scenario Assumptions")
        st.info("The following parameters define the structural and behavioral baseline of this synthetic profile.")
        
        # --- 1. Grid Connection Check ---
        st.write("#### 1. Infrastructure vs. Simulated Peak")
        calc_limit = params.get("calculated_grid_kw", 0.0)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Theoretical Grid Capacity", f"{calc_limit:,.1f} kW", 
                  help=f"{params.get('num_connections', 1)} Connection(s) @ {params.get('amperage', 0)}A")
        c2.metric("Simulated Maximum Peak", f"{peak_load:.1f} kW")
        
        with c3:
            if peak_load > calc_limit:
                st.error(f"⚠️ Bottleneck: Peak exceeds physical capacity by {(peak_load - calc_limit):.1f} kW.")
            else:
                st.success("✅ Capacity Sufficient: Peak remains within physical grid limits.")
                
        # --- 2. Anomaly Gallery ---
        anomalies_list = params.get("anomalies", [])
        if anomalies_list:
            st.write("#### 2. Injected Profile Events (Anomalies)")
            
            # Build a clean list of dictionaries for the dataframe display
            anomaly_data = []
            for a in anomalies_list:
                # Handle potential attribute access safely
                a_type = getattr(a, 'anomaly_type', a.get('anomaly_type', 'N/A')) if isinstance(a, dict) else a.anomaly_type
                a_val = getattr(a, 'value_kw', a.get('value_kw', 0)) if isinstance(a, dict) else a.value_kw
                a_freq = getattr(a, 'frequency_type', a.get('frequency_type', 'N/A')) if isinstance(a, dict) else a.frequency_type
                a_start = getattr(a, 'start_time', a.get('start_time', 'N/A')) if isinstance(a, dict) else a.start_time
                a_end = getattr(a, 'end_time', a.get('end_time', 'N/A')) if isinstance(a, dict) else a.end_time
                
                # Format the type for professional display
                type_label = {
                    "additional_load": "Additional Peak (+)", 
                    "fixed_value": "Fixed Load (=)", 
                    "reduction": "Load Reduction (-)"
                }.get(a_type, a_type)
                
                anomaly_data.append({
                    "Event Type": type_label,
                    "Impact (kW)": a_val,
                    "Frequency Pattern": str(a_freq).capitalize(),
                    "Time Window": f"{a_start} - {a_end}"
                })
                
            st.dataframe(pd.DataFrame(anomaly_data), use_container_width=True, hide_index=True)

        # --- 3. Base Configuration Fingerprint ---
        with st.expander("⚙️ View General Configuration Fingerprint"):
            f_col1, f_col2, f_col3 = st.columns(3)
            f_col1.write(f"**Base Load Level:** {params.get('base_load_pct', 0)}%")
            f_col2.write(f"**Working Hours:** {params.get('hours_per_day', 0)}h / {params.get('days_per_week', 0)} Days")
            noise_status = f"Enabled ({params.get('noise_percentage', 0)}%)" if params.get('enable_noise', False) else "Disabled"
            f_col3.write(f"**Signal Noise:** {noise_status}")
            
            if params.get('use_custom_months', False):
                st.caption("Note: Custom monthly variations are active for this profile.")
    # ==========================================

    st.divider()
    
    # 3. Universal Anomaly Scanner (Z-Score Logic)
    # Searches for statistical outliers deviating more than 3 standard deviations from the mean
    std_dev = df['consumption_kw'].std()
    z_scores = (df['consumption_kw'] - avg_load) / std_dev if std_dev > 0 else 0
    statistical_anomalies = df[z_scores > 3.0] 
    
    if not statistical_anomalies.empty:
        st.warning(f"⚠️ {len(statistical_anomalies)} unusual load peaks detected. Please verify in the chart below.")
    else:
        st.success("✅ Profile validated. No extreme statistical anomalies detected.")
        
    # 4. Universal Interactive Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['consumption_kw'], 
        mode='lines', line=dict(color=col_raw, width=1), 
        name=f'Client Load ({data_source})'
    ))
    
    # Mark detected anomalies with red crosses in the chart
    if not statistical_anomalies.empty:
        fig.add_trace(go.Scatter(
            x=statistical_anomalies['timestamp'], y=statistical_anomalies['consumption_kw'],
            mode='markers', marker=dict(color='red', size=8, symbol='x'),
            name='Statistical Anomalies'
        ))
        
    fig.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), yaxis_title="Power (kW)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Global Scenario Vault Integration
    st.divider()
    st.write(f"### 💾 Save {data_source} Scenario")
    
    default_scen_name = st.session_state.get('active_scenario_name', f"Scenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"New_{data_source}_Profile"
        
    scenario_name = st.text_input("Scenario Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    if st.button(f"🚀 Securely Save Profile & Continue", type="primary", use_container_width=True, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        
        # VERY IMPORTANT: Saving to the unified 'scenario_vault'
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
        st.session_state['scenario_vault'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": statistical_anomalies.index.tolist() if not statistical_anomalies.empty else [],
            "data_source": data_source,
            "params": params
        }
        
        # Reset the popup flag if it was a CSV upload
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"✅ Scenario '{scenario_name}' successfully secured in the vault! You may now proceed to the next tab.")
        st.rerun()