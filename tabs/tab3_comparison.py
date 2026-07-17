# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from logic.storage_manager import get_all_base_scenarios
from tabs.tab3_components.pdf_comparison_export import render_comparison_pdf_downloader
from tabs.tab3_components.comparison_tech_matrix import render_technical_comparison_matrix
from tabs.tab3_components.comparison_cfo_dashboard import render_cfo_cockpit_from_classes

def render_tab3_comparison():
    st.write("## Advanced Comparison Suite")
    
    bases = get_all_base_scenarios()
    if not bases:
        st.warning("No saved Scenarios found. Please create a Baseline in Tab 1.")
        return
        
    base_options = [b.name for b in bases]
    st.write("### 1. Select the Base Scenario")
    selected_base_name = st.selectbox("Baseline Reference Profile:", options=base_options)
    
    selected_base_obj = next((b for b in bases if b.name == selected_base_name), None)
    
    if not selected_base_obj or selected_base_obj.original_profile is None:
        st.info("No data in this baseline yet. Please process data in Tab 1.")
        return

    linked_subs = selected_base_obj.sub_scenarios
    sub_names = [sub.name for sub in linked_subs]
    
    auto_compare = False
    if sub_names:
        st.success(f"{len(sub_names)} associated variants found for '{selected_base_name}'!")
        auto_compare = st.checkbox("Automatically overlay all associated sub-scenarios", value=True)

    all_options = [selected_base_name] + sub_names
    default_selection = [selected_base_name]
    if auto_compare:
        default_selection.extend(sub_names)
        
    selected_profiles = st.multiselect("Active Scenarios in Comparison:", options=all_options, default=default_selection)

    if not selected_profiles:
        st.warning("Please choose at least one scenario for the comparison.")
        return

    def get_df_for_name(name):
        if name == selected_base_name:
            return selected_base_obj.original_profile
        else:
            sub = next((s for s in linked_subs if s.name == name), None)
            return sub.simulated_profile if sub else None

    # --- 1. THE VISUAL GRAPH OVERLAY ---
    st.write("### Load Profile Overlay")
    fig = go.Figure()
    
    for name in selected_profiles:
        df = get_df_for_name(name)
        if df is not None and not df.empty:
            is_base = (name == selected_base_name)
            l_width = 3 if is_base else 1.5
            l_color = "#333333" if is_base else None 
            
            # Robust extraction of columns to prevent empty charts
            y_col = 'final_grid_load_kw'
            if y_col not in df.columns:
                y_col = 'consumption_kw'
            if y_col not in df.columns:
                y_col = df.columns[-1] # fallback
                
            x_col = df['timestamp'] if 'timestamp' in df.columns else df.index
            
            fig.add_trace(go.Scatter(
                x=x_col, y=df[y_col],
                mode='lines',
                line=dict(width=l_width, color=l_color),
                name=f"🏢 {name} (Base)" if is_base else f"🌿 {name}"
            ))
            
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. THE TECHNICAL COMPARISON MATRIX ---
    render_technical_comparison_matrix(
        selected_profiles=selected_profiles,
        linked_subs=linked_subs,
        selected_base_obj=selected_base_obj,
        selected_base_name=selected_base_name
    )

    # --- 3. THE CFO FINANCIAL DASHBOARD ---
    if st.session_state.get('enable_financials', False):
        active_subs = [s for s in linked_subs if s.name in selected_profiles]
        render_cfo_cockpit_from_classes(selected_base_obj, active_subs)
    
    # --- 4. PROFESSIONAL PDF EXPORTER ---
    st.divider()
    render_comparison_pdf_downloader(selected_base_obj, selected_profiles, linked_subs)