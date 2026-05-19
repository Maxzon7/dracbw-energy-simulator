# tabs/tab2_scenarios.py
import streamlit as st
import plotly.graph_objects as go

# Unsere neuen UI-Komponenten
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.scenario_engine import run_isolated_scenario

# achtung 
from tabs.tab2_components.pdf_export import generate_tech_pdf
from logic.energy_logic import get_exact_minimum_requirements

def render_tab2_scenarios():
    t = st.session_state.get('t', {})
    st.header("Scenario Simulation (Isolated Analysis)")
    
    # --- 1. BASELINE SELECTION ---
    if 'scenario_registry' not in st.session_state or not st.session_state['scenario_registry']:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return
        
    saved_scenarios = list(st.session_state['scenario_registry'].keys())
    selected_baseline = st.selectbox("📂 1. Select Base Profile:", saved_scenarios)
    
    baseline_data = st.session_state['scenario_registry'][selected_baseline]
    baseline_df = baseline_data['df']
    grid_limit = baseline_data['grid_limit']
    res = baseline_data.get('params', {}).get('resolution', 15) 
    report_name = st.session_state.get('report_name', f"Report_{selected_baseline}")
    
    st.divider()

    col_input, col_chart = st.columns([1, 2.5])
    
    with col_input:
        st.write("### 🏗️ 2. Select Technology")
        
        # Der Entweder/Oder Schalter
        scenario_mode = st.radio("Choose isolated system:", ["Solar PV", "Battery (Peak Shaving)"])
        st.divider()
        
        # UI dynamisch laden
        if scenario_mode == "Solar PV":
            params = render_solar_ui()
        else:
            params = render_battery_ui()
            
        st.divider()
        st.write("### 🎨 Chart Colors")
        col_raw = st.color_picker("Original Load Color", "#A9A9A9")
        col_opt = st.color_picker("Optimized Load Color", "#00CC96")
        col_soc = st.color_picker("Battery SoC Color", "#636EFA")
        col_act = st.color_picker("Battery Action Color", "#FFA15A")

    with col_chart:
        # ==========================================
        # ENGINE AUSFÜHREN
        # ==========================================
        results = run_isolated_scenario(baseline_df, scenario_mode, params, grid_limit, res)
        
        # ==========================================
        # PLOTTING
        # ==========================================
        st.subheader(f"⚡ Grid Interaction: {scenario_mode}")
        fig_load = go.Figure()
        
        fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                      name="Original Demand", line=dict(color=col_raw, width=1)))
        fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                      name="Final Grid Demand", line=dict(color=col_opt, width=2)))
                                      
        fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
        fig_load.update_layout(height=350, yaxis_title="kW", margin=dict(t=10, b=10))
        st.plotly_chart(fig_load, use_container_width=True)

        # Batterie-Aktionsgraphen (Nur anzeigen, wenn Batterie-Modus aktiv ist)
        if scenario_mode == "Battery (Peak Shaving)":
            c_left, c_right = st.columns(2)
            with c_left:
                st.write("**Battery Charge/Discharge (kW)**")
                fig_act = go.Figure()
                fig_act.add_trace(go.Bar(x=results['timestamp'], y=results['battery_action_kw'], marker_color=col_act))
                fig_act.update_layout(height=250, margin=dict(t=10, b=10))
                st.plotly_chart(fig_act, use_container_width=True)
                
            with c_right:
                st.write("**Battery State of Charge (kWh)**")
                fig_soc = go.Figure()
                fig_soc.add_trace(go.Scatter(x=results['timestamp'], y=results['battery_soc_kwh'], 
                                             fill='tozeroy', line=dict(color=col_soc)))
                fig_soc.update_layout(height=250, margin=dict(t=10, b=10))
                st.plotly_chart(fig_soc, use_container_width=True)

    # ==========================================
    # METRICS & PDF EXPORT
    # ==========================================
    st.divider()
    st.write("### 📈 Technical Evaluation & Export")
    
    c1, c2, c3, c4 = st.columns(4)
    peak_orig = results['consumption_kw'].max()
    peak_new = results['final_grid_load_kw'].max()
    
    c1.metric("Original Peak Load", f"{peak_orig:.1f} kW")
    c2.metric("New Peak Load", f"{peak_new:.1f} kW", delta=f"{peak_new - peak_orig:.1f} kW", delta_color="inverse")
    
    min_reqs = {"min_power_kw": 0, "true_min_capacity_kwh": 0}
    if scenario_mode == "Battery (Peak Shaving)":
        min_reqs = get_exact_minimum_requirements(baseline_df, grid_limit, res)
        c3.metric("Req. Battery Power", f"{min_reqs['min_power_kw']:.1f} kW")
        c4.metric("Req. Battery Cap.", f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")

    # PDF Export Integration
    if st.button("📄 Generate PDF Report", type="primary"):
        with st.spinner("Compiling technical evaluation..."):
            try:
                pdf_metrics = {
                    "grid_limit": grid_limit,
                    "peak_raw": peak_orig,
                    "min_pwr": min_reqs['min_power_kw'],
                    "min_cap": min_reqs['true_min_capacity_kwh']
                }
                pdf_data = generate_tech_pdf(
                    report_title=f"{report_name}_{scenario_mode.replace(' ', '')}", 
                    metrics=pdf_metrics, 
                    plot_data=results, 
                    battery_enabled=(scenario_mode == "Battery (Peak Shaving)")
                )
                st.download_button(
                    label="⬇️ Download PDF", 
                    data=pdf_data,
                    file_name=f"{report_name}_{scenario_mode.replace(' ', '')}.pdf",
                    mime="application/pdf"
                )
            except Exception as pdf_error:
                st.error(f"Error during document compilation: {pdf_error}")