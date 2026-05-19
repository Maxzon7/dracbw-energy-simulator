# tabs/tab1_components/chart.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_baseline_chart():
    """
    Renders the main load profile chart based on the global session state data.
    """
    t = st.session_state['t']
    
    if 'filtered_data' in st.session_state and st.session_state['filtered_data'] is not None:
        # 1. Get the full year dataframe from session state
        df = st.session_state['filtered_data']
    
        # Safety check: Ensure 'timestamp' is in datetime format for pandas filtering
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ==========================================
        # UPPER PART: DETAILED MONTHLY CHART
        # ==========================================
        st.write("### 📊 Detailed Monthly View")
    
        # Dropdown to select the month for the upper chart
        month_names = ["January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
    
        selected_month_name = st.selectbox(
            "Select month to inspect:", 
            month_names, 
            index=0 # Default to January
        )
    
        # Map the selected month name back to its numeric index (1 to 12)
        selected_month_idx = month_names.index(selected_month_name) + 1
    
        # Filter the full year dataframe down to just the selected month
        monthly_df = df[df['timestamp'].dt.month == selected_month_idx]
    
        # Render the detailed monthly chart
        # Note: If you use Plotly/Altair here, just pass 'monthly_df' to your custom charting logic
        st.line_chart(data=monthly_df, x="timestamp", y="consumption_kw")
    
        st.divider()

        # ==========================================
        # LOWER PART: FULL YEAR OVERVIEW
        # ==========================================
        st.write("### 📅 Full Year Overview")
    
        # Render the complete 12-month series as a macro-perspective
        st.line_chart(data=df, x="timestamp", y="consumption_kw")
    else:
        st.info("Upload a CSV or generate a manual profile on the left to view data.")