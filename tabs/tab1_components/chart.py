# tabs/tab1_components/chart.py
import streamlit as st
import plotly.graph_objects as go

def render_baseline_chart():
    """
    Renders the main load profile chart based on the global session state data.
    """
    t = st.session_state['t']
    
    if 'filtered_data' in st.session_state and st.session_state['filtered_data'] is not None:
        filtered_data = st.session_state['filtered_data']
        grid_limit = st.session_state.get('grid_limit', 50.0)
        col_raw_current = st.session_state.get('col_raw', "#A9A9A9")

        st.subheader(t["chart_load"])
        fig_load = go.Figure()
        fig_load.add_trace(go.Scatter(
            x=filtered_data['timestamp'], 
            y=filtered_data['consumption_kw'], 
            name="Load Profile", 
            line=dict(color=col_raw_current, width=1)
        ))
        fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", name="Grid Limit")
        fig_load.update_layout(height=450, yaxis_title="kW", margin=dict(t=10, b=10))
        
        st.plotly_chart(fig_load, use_container_width=True)
    else:
        st.info("Upload a CSV or generate a manual profile on the left to view data.")