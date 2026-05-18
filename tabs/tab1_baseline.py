# tabs/tab1_baseline.py
import streamlit as st

# Import the individual Lego bricks
from tabs.tab1_components.toggle import render_data_source_toggle
from tabs.tab1_components.upload import render_csv_upload_section
from tabs.tab1_components.manual import render_manual_profile_generator
from tabs.tab1_components.chart import render_baseline_chart

def render_tab1_baseline():
    """
    Master function to assemble Tab 1. 
    Routes logic to dedicated component files for maximum modularity.
    """
    t = st.session_state['t']
    st.header(t["tab_baseline"])
    
    # 1. Render the top toggle
    data_mode = render_data_source_toggle()
    st.divider()
    
    # 2. Setup the split layout
    col_input, col_chart = st.columns([1.2, 2.5])
    
    with col_input:
        # 3. Route to the correct input module based on toggle
        if data_mode == t.get("csv_upload", "CSV Upload"):
            render_csv_upload_section()
        else:
            render_manual_profile_generator()

    with col_chart:
        # 4. Render the chart (agnostic to data source)
        render_baseline_chart()