import streamlit as st

def render_tab3_comparison():
    """
    Renders the cross-scenario analytical overview sheet.
    """
    t = st.session_state['t']
    st.header(t.get("tab_comparison", "3. Comparison Matrix"))
    st.info("The automated comparison matrix for all active configuration models is prepared here.")