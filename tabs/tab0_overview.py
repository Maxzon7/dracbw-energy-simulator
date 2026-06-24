import streamlit as st

def render_tab0_overview():
    """
    Renders the Executive Dashboard. 
    This tab acts as a read-only consolidation of the active project.
    """
    st.header("📊 Executive Project Overview")
    st.markdown("---")
    
    st.info("This dashboard will automatically pull data from the active project configuration to display high-level KPIs and export options.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="System Status", value="Loading...")
    with col2:
        st.metric(label="Total Co2 Reduction", value="TBD")
        
    with col3:
        # Obey the financial toggle even here!
        if st.session_state.get('enable_financials', True):
            st.metric(label="Estimated ROI", value="TBD")
        else:
            st.metric(label="Estimated ROI", value="Disabled")
            
    st.markdown("---")
    st.button("📥 Download JSON Configuration")
    st.button("📄 Generate Management Report (PDF)")