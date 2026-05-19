

# tabs/tab1_components/chart.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_baseline_chart():
    """
    Renders the baseline load profile charts with dynamic downsampling and on-demand detail.
    Includes technical KPI metrics for the baseline scenario.
    """
    t = st.session_state['t']
    
    if 'filtered_data' in st.session_state and st.session_state['filtered_data'] is not None:
        # Get the full year dataframe from session state
        df = st.session_state['filtered_data']
        
        # Safety check: Ensure 'timestamp' is in datetime format
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ==========================================
        # 0. BASELINE TECHNICAL METRICS (NEW)
        # ==========================================
        st.write("### 📋 Baseline Technical Summary")
        
        # Holt sich das Grid Limit (Fallback 50.0 falls nicht definiert)
        grid_limit = st.session_state.get('grid_limit', 50.0)
        
        # Mathematische Berechnungen (15-Min-Intervalle -> / 4 für Stunden/kWh)
        total_consumption_kwh = df['consumption_kw'].sum() / 4.0
        max_peak_kw = df['consumption_kw'].max()
        
        # Zählt die 15-Minuten-Intervalle, in denen der Peak das Grid Limit sprengt
        violation_intervals = len(df[df['consumption_kw'] > grid_limit])
        violation_hours = violation_intervals / 4.0
        
        # UI: 4 Kennzahlen nebeneinander rendern
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Total Consumption", value=f"{total_consumption_kwh:,.0f} kWh")
        with col2:
            st.metric(label="Max Peak Load", value=f"{max_peak_kw:,.1f} kW")
        with col3:
            st.metric(label="Grid Limit", value=f"{grid_limit:,.1f} kW")
        with col4:
            # Optischer Trick: Wenn > 0, zeige eine rote Warnung ("inverse" Delta)
            if violation_hours > 0:
                st.metric(label="Grid Limit Violations", value=f"{violation_hours:,.1f} h", delta="Overload detected", delta_color="inverse")
            else:
                st.metric(label="Grid Limit Violations", value="0 h", delta="Within limits", delta_color="normal")
                
        st.divider()

        # ==========================================
        # 1. DETAILED MONTHLY VIEW (DEFAULT)
        # ==========================================
        st.write("### 📊 Detailed Monthly View")
        
        month_names = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        
        selected_month_name = st.selectbox("Select month to inspect:", month_names, index=0)
        selected_month_idx = month_names.index(selected_month_name) + 1
        
        # Filter for the selected month (2,880 points -> renders fast)
        monthly_df = df[df['timestamp'].dt.month == selected_month_idx]
        st.line_chart(data=monthly_df, x="timestamp", y="consumption_kw")
        
        st.divider()

        # ==========================================
        # 2. SIMPLIFIED YEARLY OVERVIEW (DEFAULT)
        # ==========================================
        st.write("### 📅 Simplified Yearly Overview (Weekly Average)")
        st.info("Displays the year-long trend aggregated into 1-week intervals to optimize performance.")
        
        # Downsample the 15-min data to weekly averages (52 points -> renders instantly)
        weekly_df = df.resample('W', on='timestamp')['consumption_kw'].mean().reset_index()
        st.line_chart(data=weekly_df, x="timestamp", y="consumption_kw")
        
        st.divider()

        # ==========================================
        # 3. ON-DEMAND ANALYSIS PROFILES
        # ==========================================
        st.write("### 🔍 Advanced Analysis Options")
        
        # Chart 3: Average Work-Week (On Request)
        if st.checkbox("Show Average Work-Week Profile (Monday - Sunday Aggregation)"):
            df_temp = df.copy()
            df_temp['weekday'] = df_temp['timestamp'].dt.dayofweek
            df_temp['time'] = df_temp['timestamp'].dt.time
            
            # Group by weekday and time to get the average
            avg_week = df_temp.groupby(['weekday', 'time'])['consumption_kw'].mean().reset_index()
            
            # Map to a dummy week for a clean X-Axis (Jan 1, 2024 was a Monday)
            base_date = pd.to_datetime("2024-01-01")
            avg_week['plot_time'] = avg_week.apply(
                lambda row: base_date + pd.Timedelta(days=row['weekday'], hours=row['time'].hour, minutes=row['time'].minute), 
                axis=1
            )
            st.line_chart(data=avg_week, x="plot_time", y="consumption_kw")
            st.write("") # Small spacing

        # Chart 4: Full Year Raw Data (On Request)
        if st.checkbox("Show Full 365-Day Raw Data (Warning: High 15-Min Granularity)"):
            st.line_chart(data=df, x="timestamp", y="consumption_kw")
            
    else:
        st.info("Upload a CSV or generate a manual profile on the left to view data.")