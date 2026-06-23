# tabs/tab1_components/validation_components/charts.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def render_multi_resolution_charts(df: pd.DataFrame, params: dict, statistical_anomalies: pd.DataFrame):
    """
    Renders the tabbed chart station (Full Year, Monthly Deep-Dive, Weekly Heartbeat).
    UPGRADE: Dynamically injects sub-meters into Full and Monthly tabs, and disables red warnings for Greenfield (limit=0).
    """
    # SYSTEM MEMORY FIX: Guarantee we grab the live grid_limit, fallback to params if missing
    loaded_params = st.session_state.get('loaded_params', {})
    grid_limit = loaded_params.get('grid_limit', params.get('grid_limit', 50.0))
    
    col_raw = params.get('col_raw', '#A9A9A9')
    data_source = params.get('data_source', 'Unknown')
    
    # 1. Dynamically identify any sub-meters (ignoring standard/math columns)
    excluded_cols = ['timestamp', 'consumption_kw', 'month_idx', 'dayofweek', 'time_key']
    sub_meters = [col for col in df.columns if col not in excluded_cols and pd.api.types.is_numeric_dtype(df[col])]
    
    st.write("#### 📊 Multi-Resolution Profile Analytics")
    tab_full, tab_month, tab_week = st.tabs(["🔭 Full Horizon Timeline", "📅 Monthly Segment Deep-Dive", "🗓️ Typical Weekly Heartbeat"])
    
   # --- TAB 1: FULL HORIZON ---
    with tab_full:
        fig_full = go.Figure()
        sub_configs = params.get('sub_meter_configs', {})
        
        # Add sub-meters as background lines first (if any exist)
        for meter in sub_meters:
            conf = sub_configs.get(meter, {})
            m_name = conf.get('name', f'Sub-Meter: {meter}')
            m_color = conf.get('color', None)
            
            line_dict = dict(width=1)
            if m_color:
                line_dict['color'] = m_color
                
            fig_full.add_trace(go.Scatter(x=df['timestamp'], y=df[meter], mode='lines', line=line_dict, opacity=0.5, name=m_name))
            
        # Add the main aggregated load profile
        fig_full.add_trace(go.Scatter(x=df['timestamp'], y=df['consumption_kw'], mode='lines', line=dict(color=col_raw, width=1.5), name='Total Client Load'))
        
        if not statistical_anomalies.empty:
            fig_full.add_trace(go.Scatter(x=statistical_anomalies['timestamp'], y=statistical_anomalies['consumption_kw'], mode='markers', marker=dict(color='red', size=6, symbol='x'), name='Outliers'))
            
        # Optional Greenfield Limit (Only draw if > 0)
        if grid_limit > 0.0:
            fig_full.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text=f"Grid Limit: {grid_limit} kW")
            
        fig_full.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
        st.plotly_chart(fig_full, use_container_width=True)
        
    # --- TAB 2: MONTHLY DEEP-DIVE ---
    with tab_month:
        month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
        df['month_idx'] = df['timestamp'].dt.month
        available_months = sorted(df['month_idx'].unique())
        
        sel_month_idx = st.selectbox("Select Target Month for Analysis", available_months, format_func=lambda x: month_names.get(x, f"Month {x}"))
        sub_df = df[df['month_idx'] == sel_month_idx].copy()
        
        fig_month = go.Figure()
        sub_configs = params.get('sub_meter_configs', {})
        
        # Optional Greenfield limit shading (Only draw if > 0)
        if grid_limit > 0.0:
            fig_month.add_trace(go.Scatter(x=sub_df['timestamp'], y=[grid_limit] * len(sub_df), line=dict(width=0), showlegend=False, hoverinfo='skip'))
            fig_month.add_trace(go.Scatter(x=sub_df['timestamp'], y=np.maximum(sub_df['consumption_kw'], grid_limit), fill='tonexty', fillcolor='rgba(255, 65, 54, 0.35)', line=dict(width=0), name='Grid Overload Area'))
        
        # Add sub-meters as background lines
        for meter in sub_meters:
            conf = sub_configs.get(meter, {})
            m_name = conf.get('name', f'Sub-Meter: {meter}')
            m_color = conf.get('color', None)
            
            line_dict = dict(width=1)
            if m_color:
                line_dict['color'] = m_color
                
            fig_month.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df[meter], mode='lines', line=line_dict, opacity=0.5, name=m_name))
            
        # Add the main aggregated load profile
        fig_month.add_trace(go.Scatter(x=sub_df['timestamp'], y=sub_df['consumption_kw'], mode='lines', line=dict(color=col_raw, width=2), name='Total Client Load'))
        
        # Optional H-Line
        if grid_limit > 0.0:
            fig_month.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text=f"Grid Limit: {grid_limit} kW")
            
        fig_month.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
        st.plotly_chart(fig_month, use_container_width=True)
    # --- TAB 3: TYPICAL WEEKLY HEARTBEAT (SAFE MODE) ---
    with tab_week:
        df_week = df.copy()
        df_week['dayofweek'] = df_week['timestamp'].dt.dayofweek
        df_week['time_key'] = df_week['timestamp'].dt.time
        
        # SAFE COMPUTATION: We only aggregate the main column to avoid KeyError crash
        weekly_profile = df_week.groupby(['dayofweek', 'time_key'], as_index=False)['consumption_kw'].mean()
        
        monday_start = pd.to_datetime("2026-01-05 00:00:00")
        weekly_profile['synthetic_timestamp'] = weekly_profile.apply(lambda r: monday_start + pd.Timedelta(days=int(r['dayofweek'])) + pd.Timedelta(hours=r['time_key'].hour, minutes=r['time_key'].minute), axis=1)
        weekly_profile.sort_values('synthetic_timestamp', inplace=True)
        
        fig_week = go.Figure()
        
        # Optional Greenfield limit shading (Only draw if > 0)
        if grid_limit > 0.0:
            fig_week.add_trace(go.Scatter(x=weekly_profile['synthetic_timestamp'], y=[grid_limit] * len(weekly_profile), line=dict(width=0), showlegend=False, hoverinfo='skip'))
            fig_week.add_trace(go.Scatter(x=weekly_profile['synthetic_timestamp'], y=np.maximum(weekly_profile['consumption_kw'], grid_limit), fill='tonexty', fillcolor='rgba(255, 65, 54, 0.35)', line=dict(width=0), name='Average Overload Area'))
            
        # Draw ONLY the main aggregated load profile (No sub-meters here)
        fig_week.add_trace(go.Scatter(x=weekly_profile['synthetic_timestamp'], y=weekly_profile['consumption_kw'], mode='lines', line=dict(color=col_raw, width=2.5), name='Mean Weekly Footprint'))
        
        if grid_limit > 0.0:
            fig_week.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text=f"Grid Limit: {grid_limit} kW")
            
        fig_week.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
        fig_week.update_xaxes(tickformat="%A %H:%M")
        st.plotly_chart(fig_week, use_container_width=True)

    if 'month_idx' in df.columns:
        df.drop(columns=['month_idx'], inplace=True)