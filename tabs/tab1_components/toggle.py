# tabs/tab1_components/toggle.py
import streamlit as st

def render_data_source_toggle() -> str:
    """
    Renders the radio buttons to select between CSV Upload and Manual Input.
    Returns the selected string value.
    """
    t = st.session_state['t']
    data_mode = st.radio(
        t.get("data_source", "Data Source"), 
        [t.get("csv_upload", "CSV Upload"), t.get("manual_input", "Manual Input")], 
        horizontal=True
    )
    return data_mode