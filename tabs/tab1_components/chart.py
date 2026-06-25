# tabs/tab1_components/chart.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def create_violation_chart(plot_df, x_col, y_col, grid_limit, title, sub_meters=None):
    """
    Helper function to render a Plotly chart with a base load.
    UPGRADED: Renders optional sub-meters and disables red limit logic if grid_limit is 0.0
    """
    fig = go.Figure()
    
    # 1. Base Load Line (The aggregated total)
    fig.add_trace(go.Scatter(
        x=plot_df[x_col],
        y=plot_df[y_col],
        mode='lines',
        name='Total Load Profile',
        line=dict(color='#1f77b4', width=3)
    ))
    
    # 2. Add individual sub-meters (if multiple were selected)
    if sub_meters:
        for meter in sub_meters:
            if meter in plot_df.columns:
                fig.add_trace(go.Scatter(
                    x=plot_df[x_col],
                    y=plot_df[meter],
                    mode='lines',
                    name=f"Sub-Meter: {meter}",
                    line=dict(width=1.5),
                    opacity=0.6
                ))
    
    # 3. Grid Limit Horizontal Line & Violation Shading (ONLY if limit > 0)
    if grid_limit > 0.0:
        fig.add_hline(
            y=grid_limit, 
            line_dash="dash", 
            line_color="red", 
            annotation_text=f"Grid Limit: {grid_limit:,.1f} kW", 
            annotation_position="top left",
            annotation_font_color="red"
        )
        
        capped_load = plot_df[y_col].clip(upper=grid_limit)
        
        fig.add_trace(go.Scatter(
            x=plot_df[x_col],
            y=capped_load,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_df[x_col],
            y=plot_df[y_col],
            mode='lines',
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.4)',
            line=dict(width=0),
            name='Grid Violation (Overload)',
            hoverinfo='skip'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Power (kW)",
        margin=dict(l=0, r=0, t=40, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    return fig

def render_baseline_chart(df, grid_limit):
    """
    Renders the baseline load profile charts with dynamic downsampling and on-demand detail.
    Includes advanced technical KPI metrics for the baseline scenario and violation visualizers.
    """
    t = st.session_state.get('t', {})
    
    if df is not None and not df.empty:
        df = df.copy()
        
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ==========================================
        # 0. BASELINE TECHNICAL METRICS
        # ==========================================
        st.write("### 📊 Baseline Technical Summary")
        
        # Core Calculations
        total_consumption_kwh = df['consumption_kw'].sum() / 4.0
        max_peak_kw = df['consumption_kw'].max()
        
        # Violation Calculation
        if grid_limit > 0.0:
            df['violation_kw'] = (df['consumption_kw'] - grid_limit).clip(lower=0.0)
        else:
            df['violation_kw'] = 0.0
            
        excluded_cols = ['timestamp', 'violation_kw', 'consumption_kw']
        sub_meters = [col for col in df.columns if col not in excluded_cols and pd.api.types.is_numeric_dtype(df[col])]
        
        max_violation_kw = df['violation_kw'].max()
        violation_volume_kwh = df['violation_kw'].sum() / 4.0
        
        # UI: 5 Metrics side by side
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(label="Total Consumption", value=f"{total_consumption_kwh:,.0f} kWh")
        with col2:
            st.metric(label="Max Peak Load", value=f"{max_peak_kw:,.1f} kW")
        with col3:
            st.metric(label="Grid Limit", value=f"{grid_limit:,.1f} kW")
        with col4:
            if max_violation_kw > 0:
                st.metric(label="Max Peak Violation", value=f"{max_violation_kw:,.1f} kW", delta="Requires Inverter Power", delta_color="inverse")
            else:
                st.metric(label="Max Peak Violation", value="0.0 kW", delta="Safe", delta_color="normal")
        with col5:
            if violation_volume_kwh > 0:
                st.metric(label="Total Violation Volume", value=f"{violation_volume_kwh:,.0f} kWh", delta="Requires Battery Cap", delta_color="inverse")
            else:
                st.metric(label="Total Violation Volume", value="0 kWh", delta="Safe", delta_color="normal")
                
        st.divider()

        # ==========================================
        # 1. FULL 365-DAY RAW DATA VIEW
        # ==========================================
        st.write("### 🌍 Full Year Overview (365 Days)")
        st.info("Displays the complete, unfiltered 15-minute resolution load profile for the entire year.")
        
        fig_raw = create_violation_chart(df, "timestamp", "consumption_kw", grid_limit, "365-Day Raw Data (34,560 intervals)", sub_meters=sub_meters)
        st.plotly_chart(fig_raw, use_container_width=True)
        
        st.divider()

        # ==========================================
        # 2. DETAILED MONTHLY VIEW
        # ==========================================
        st.write("### 📅 Detailed Monthly View")
        
        month_names = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        
        selected_month_name = st.selectbox("Select month to inspect:", month_names, index=0)
        selected_month_idx = month_names.index(selected_month_name) + 1
        
        monthly_df = df[df['timestamp'].dt.month == selected_month_idx]
        
        fig_monthly = create_violation_chart(monthly_df, "timestamp", "consumption_kw", grid_limit, f"Load Profile - {selected_month_name}", sub_meters=sub_meters)
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        st.divider()

        # ==========================================
        # 3. ON-DEMAND ANALYSIS PROFILES
        # ==========================================
        st.write("### 🔍 Advanced Analysis Options")
        
        if st.checkbox("Show Average Work-Week Profile (Monday - Sunday Aggregation)"):
            df_temp = df.copy()
            df_temp['weekday'] = df_temp['timestamp'].dt.dayofweek
            df_temp['time'] = df_temp['timestamp'].dt.time
            
            avg_week = df_temp.groupby(['weekday', 'time']).mean(numeric_only=True).reset_index()
            
            base_date = pd.to_datetime("2024-01-01")
            avg_week['plot_time'] = avg_week.apply(
                lambda row: base_date + pd.Timedelta(days=row['weekday'], hours=row['time'].hour, minutes=row['time'].minute), 
                axis=1
            )
            
            fig_avg_week = create_violation_chart(avg_week, "plot_time", "consumption_kw", grid_limit, "Average Simulated Work-Week", sub_meters=sub_meters)
            st.plotly_chart(fig_avg_week, use_container_width=True)
            st.write("") 
            
    else:
        st.info("No profile data available to display.")
