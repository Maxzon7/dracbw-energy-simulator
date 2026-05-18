import streamlit as st
import plotly.graph_objects as go
from logic.energy_logic import load_and_clean_csv, process_consumption_data

def render_tab1_baseline(t: dict):
    """
    Renders the Baseline tab. Handles file upload, raw data processing,
    and visualizes the initial grid load without battery intervention.
    """
    st.header(t.get("tab_baseline", "1. Baseline (Current State)"))
    
    # Layout with two columns: left for inputs, right for charts
    col_input, col_chart = st.columns([1, 3])
    
    with col_input:
        st.subheader(t["header_data"])
        uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
        
        if uploaded_file:
            # Generate default report name based on the uploaded file
            default_name = uploaded_file.name.rsplit('.', 1)[0]
            report_name = st.text_input("Report Title", value=f"Report_{default_name}")
            
            # Store in session state for other tabs
            st.session_state['report_name'] = report_name
            st.session_state['uploaded_file_name'] = uploaded_file.name
        
        st.subheader(t["header_grid"])
        grid_limit = st.number_input(t["grid_limit"], value=50.0, step=5.0)
        res = st.selectbox(t["resolution"], [1, 5, 15, 60], index=2)
        
        # Color picker for baseline
        col_raw = st.color_picker("Raw Load Color", "#A9A9A9")
        
        # Save critical parameters to session state (our digital notepad)
        st.session_state['grid_limit'] = grid_limit
        st.session_state['resolution'] = res
        st.session_state['col_raw'] = col_raw

    with col_chart:
        if uploaded_file:
            try:
                # 1. Load and process data
                raw_df = load_and_clean_csv(uploaded_file)
                data = process_consumption_data(raw_df, res)
                
                # 2. Date Filtering
                min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
                selected_dates = st.date_input(t["analysis_period"], [min_date, max_date])
                
                if len(selected_dates) == 2:
                    filtered_data = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                         (data['timestamp'].dt.date <= selected_dates[1])]
                    
                    # VERY IMPORTANT: Save the filtered data to session state for Tab 2
                    st.session_state['filtered_data'] = filtered_data
                    
                    # 3. Plot Baseline
                    st.subheader(t["chart_load"])
                    fig_load = go.Figure()
                    fig_load.add_trace(go.Scatter(x=filtered_data['timestamp'], y=filtered_data['consumption_kw'], 
                                             name="Raw Load", line=dict(color=col_raw, width=1)))
                    fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", name="Grid Limit")
                    fig_load.update_layout(height=450, yaxis_title="kW", margin=dict(t=10, b=10))
                    
                    st.plotly_chart(fig_load, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error processing data: {e}")
        else:
            st.info("Please upload a CSV file on the left to begin the analysis.")