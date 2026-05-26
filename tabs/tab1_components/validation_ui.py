# tabs/tab1_components/validation_ui.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def render_validation_dashboard(df: pd.DataFrame, params: dict, active_scenario: str, is_edit_mode: bool):
    """
    UNIFIED VALIDATION ENGINE (The "Funnel")
    Takes finalized, standardized load profile data (manual or CSV) 
    and renders an identical UX surface with advanced tabbed multi-resolution charting,
    grid violation accounting, and automated data logging.
    """
    # Safely unpack core parameters
    grid_limit = params.get('grid_limit', 50.0)
    res = params.get('resolution', 15)
    col_raw = params.get('col_raw', '#A9A9A9')
    data_source = params.get('data_source', 'Unknown')
    
    st.divider()
    st.write("### ⚡ 3. Baseline Load Profile Validation")
    
    # Ensure correct datetime index/column format
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # 1. Advanced Grid Breach Analytics
    hours_factor = res / 60.0
    
    total_energy_kwh = df['consumption_kw'].sum() * hours_factor
    peak_load = df['consumption_kw'].max()
    avg_load = df['consumption_kw'].mean()
    
    # Calculate exact grid limit violations
    breach_mask = df['consumption_kw'] > grid_limit
    breach_df = df[breach_mask]
    hours_over_limit = len(breach_df) * hours_factor
    exceeded_energy_kwh = ((breach_df['consumption_kw'] - grid_limit) * hours_factor).sum()
    
    # 2. Universal KPI Layout (Expanded to 6 Metrics via 2 rows)
    st.write("#### 📊 System Performance Indicators")
    m_row1_1, m_row1_2, m_row1_3 = st.columns(3)
    m_row1_1.metric("Data Resolution", f"{res} min")
    m_row1_2.metric("Maximum Peak Load", f"{peak_load:.1f} kW")
    m_row1_3.metric("Total Annual Energy", f"{total_energy_kwh:,.0f} kWh")
    
    m_row2_1, m_row2_2, m_row2_3 = st.columns(3)
    m_row2_1.metric("Average Base Load", f"{avg_load:.1f} kW")
    
    # Color code grid violation impact metrics to draw consulting attention
    if hours_over_limit > 0:
        m_row2_2.metric("Grid Limit Overload Duration", f"{hours_over_limit:,.1f} Hours", delta=f"{len(breach_df)} intervals", delta_color="inverse")
        m_row2_3.metric("Total Overload Energy Deficit", f"{exceeded_energy_kwh:,.0f} kWh", delta="Requires Storage", delta_color="inverse")
    else:
        m_row2_2.metric("Grid Limit Overload Duration", "0.0 Hours", delta="No Breaches")
        m_row2_3.metric("Total Overload Energy Deficit", "0 kWh", delta="Grid Safe")

    # ==========================================
    # --- CHAMELEON DASHBOARD: ADVANCED METRICS ---
    # ==========================================
    if params.get("is_manual", False):
        st.divider()
        st.write("### 🔍 Advanced Scenario Assumptions")
        st.info("The following parameters define the structural and behavioral baseline of this synthetic profile.")
        
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
    
    # 3. Statistical Outlier Scanner (Z-Score)
    std_dev = df['consumption_kw'].std()
    z_scores = (df['consumption_kw'] - avg_load) / std_dev if std_dev > 0 else 0
    statistical_anomalies = df[z_scores > 3.0] 
    
    if not statistical_anomalies.empty:
        st.warning(f"⚠️ {len(statistical_anomalies)} unusual load peaks detected. Verify grid exposure in charts below.")
    else:
        st.success("✅ Profile validated. No extreme statistical anomalies detected.")
        
    # 4. MULTI-RESOLUTION INTERACTIVE CHARTING STATION (Tabs System)
    st.write("#### 📈 Multi-Resolution Profile Analytics")
    tab_full, tab_month, tab_week = st.tabs(["📊 Full Horizon Timeline", "📅 Monthly Segment Deep-Dive", "🔄 Typical Weekly Heartbeat"])
    
    # --- TAB 1: FULL HORIZON ---
    with tab_full:
        fig_full = go.Figure()
        fig_full.add_trace(go.Scatter(
            x=df['timestamp'], y=df['consumption_kw'], 
            mode='lines', line=dict(color=col_raw, width=1), 
            name=f'Client Load ({data_source})'
        ))
        if not statistical_anomalies.empty:
            fig_full.add_trace(go.Scatter(
                x=statistical_anomalies['timestamp'], y=statistical_anomalies['consumption_kw'],
                mode='markers', marker=dict(color='red', size=6, symbol='x'),
                name='Outliers (>3 StdDev)'
            ))
        fig_full.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
        fig_full.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
        st.plotly_chart(fig_full, use_container_width=True)
        
    # --- TAB 2: MONTHLY DEEP-DIVE ---
    with tab_month:
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
        }
        df['month_idx'] = df['timestamp'].dt.month
        available_months = sorted(df['month_idx'].unique())
        
        sel_month_idx = st.selectbox("Select Target Month for Analysis", available_months, 
                                     format_func=lambda x: month_names.get(x, f"Month {x}"))
        
        sub_df_month = df[df['month_idx'] == sel_month_idx].copy()
        
        fig_month = go.Figure()
        # Invisible baseline at grid limit for filling threshold breaches
        fig_month.add_trace(go.Scatter(
            x=sub_df_month['timestamp'], y=[grid_limit] * len(sub_df_month),
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        # Exceeded load filled area (Glowing Breach)
        fig_month.add_trace(go.Scatter(
            x=sub_df_month['timestamp'], y=np.maximum(sub_df_month['consumption_kw'], grid_limit),
            fill='tonexty', fillcolor='rgba(255, 65, 54, 0.35)', 
            line=dict(width=0), name='Grid Overload Area'
        ))
        # Actual client load profile curve
        fig_month.add_trace(go.Scatter(
            x=sub_df_month['timestamp'], y=sub_df_month['consumption_kw'], 
            mode='lines', line=dict(color=col_raw, width=1.5), 
            name='Client Load'
        ))
        
        fig_month.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
        fig_month.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
        st.plotly_chart(fig_month, use_container_width=True)
        
    # --- TAB 3: TYPICAL WEEKLY HEARTBEAT ---
    with tab_week:
        st.info("This view aggregates all data points across the entire horizon to extract the average weekly business footprint.")
        
        df_week = df.copy()
        df_week['dayofweek'] = df_week['timestamp'].dt.dayofweek # 0=Monday, 6=Sunday
        df_week['time_key'] = df_week['timestamp'].dt.time
        
        # Average identical time slots across the dataset
        weekly_profile = df_week.groupby(['dayofweek', 'time_key'], as_index=False)['consumption_kw'].mean()
        
        # Build synthetic uniform timestamp array starting at a fictional Monday (2026-01-05) for linear time-series plotting
        monday_start = pd.to_datetime("2026-01-05 00:00:00")
        weekly_profile['synthetic_timestamp'] = weekly_profile.apply(
            lambda r: monday_start + pd.Timedelta(days=int(r['dayofweek'])) + pd.Timedelta(hours=r['time_key'].hour, minutes=r['time_key'].minute),
            axis=1
        )
        weekly_profile.sort_values('synthetic_timestamp', inplace=True)
        
        fig_week = go.Figure()
        # Invisible baseline threshold at grid limit
        fig_week.add_trace(go.Scatter(
            x=weekly_profile['synthetic_timestamp'], y=[grid_limit] * len(weekly_profile),
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ))
        # Exceeded load filled area
        fig_week.add_trace(go.Scatter(
            x=weekly_profile['synthetic_timestamp'], y=np.maximum(weekly_profile['consumption_kw'], grid_limit),
            fill='tonexty', fillcolor='rgba(255, 65, 54, 0.35)', 
            line=dict(width=0), name='Average Overload Area'
        ))
        # Normalized average curve
        fig_week.add_trace(go.Scatter(
            x=weekly_profile['synthetic_timestamp'], y=weekly_profile['consumption_kw'], 
            mode='lines', line=dict(color=col_raw, width=2), 
            name='Mean Weekly Footprint'
        ))
        
        fig_week.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
        fig_week.update_layout(
            height=400, margin=dict(l=0, r=0, t=20, b=0), 
            yaxis_title="Power (kW)", hovermode="x unified"
        )
        # Reformat x-axis ticks to display localized weekday names and hours clearly
        fig_week.update_xaxes(tickformat="%A %H:%M")
        st.plotly_chart(fig_week, use_container_width=True)

    # Clean temporary helper columns to avoid memory contamination during vault serialization
    if 'month_idx' in df.columns:
        df.drop(columns=['month_idx'], inplace=True)

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
        
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
        st.session_state['scenario_vault'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": statistical_anomalies.index.tolist() if not statistical_anomalies.empty else [],
            "data_source": data_source,
            "params": params
        }
        
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"✅ Scenario '{scenario_name}' successfully secured in the vault! You may now proceed to the next tab.")
        st.rerun()