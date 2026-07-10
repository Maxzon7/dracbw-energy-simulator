# tabs/tab0_overview.py
import streamlit as st
from logic.storage_manager import get_all_base_scenarios
from tabs.tab1_components.financial_ui import render_financial_summary

def render_tab0_overview():
    """Renders the Executive Dashboard based on the active project portfolio classes."""
    st.header("Executive Project Overview")
    st.markdown("---")
    
    # Retrieve the class-based portfolio from the storage manager
    portfolio = get_all_base_scenarios()
    
    if not portfolio:
        st.info("This project is currently empty. Please head over to 'Baseline' to configure your initial energy profile and tariffs.")
        return
        
    # Select the first available or active baseline as the main reference
    main_baseline = portfolio[0]
    
    # Extract structural configuration properties from the object
    st.write(f"### Active Baseline: {main_baseline.name}")
    
    st.markdown("---")
    st.write("### System Status & Key Metrics")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Active Baseline Profile", value=main_baseline.name)
    with col2:
        st.metric(label="Total Generated Variants", value=str(len(main_baseline.sub_scenarios)))
    with col3:
        if st.session_state.get('enable_financials', True):
            st.metric(label="Financial Evaluation", value="Active")
        else:
            st.metric(label="Financial Evaluation", value="Disabled")
            
    st.markdown("---")
    st.write("### Project Export")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.button("Generate Executive Management Report (PDF)", use_container_width=True)
    with col_dl2:
        st.info("Note: You can download the full project file from the Main Hub (Lobby).")