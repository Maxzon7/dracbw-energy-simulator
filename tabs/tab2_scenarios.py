
# tabs/tab2_scenarios.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Clean imports from our sub-components packaging
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.solar_logic import generate_solar_profile
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.scenario_engine import run_isolated_scenario

# Technical additions
from tabs.tab2_components.pdf_export import generate_tech_pdf
from logic.energy_logic import get_exact_minimum_requirements

def render_tab2_scenarios():
    """
    Master Tab 2: Scenario Engine. Manages isolated simulation pipelines (Solar / BESS),
    synchronizes interface widgets, and provides unified technical metrics and PDF reporting.
    """
    t = st.session_state.get('t', {})
    st.header("Scenario Simulation (Isolated Analysis)")
    
    # --- 1. BASELINE SELECTION ---
    if 'scenario_registry' not in st.session_state or not st.session_state['scenario_registry']:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return
        
    saved_scenarios = list(st.session_state['scenario_registry'].keys())
    selected_baseline = st.selectbox("📂 1. Select Base Profile:", saved_scenarios)
    
    # Extract fundamental data package from vault
    baseline_data = st.session_state['scenario_registry'][selected_baseline]
    baseline_df = baseline_data['df']
    grid_limit = baseline_data['grid_limit']
    project_metadata = baseline_data.get('params', {}).get('project_metadata', {})
    res = baseline_data.get('params', {}).get('resolution', 15) 
    report_name = st.session_state.get('report_name', f"Report_{selected_baseline}")
    
    st.divider()

    # Layout Split: Input panel on the left, interactive visualization on the right
    col_input, col_chart = st.columns([1, 2.5])
    
    with col_input:
        st.write("### 🏗️ 2. Select Technology")
        scenario_mode = st.radio("Choose isolated system:", ["Solar PV Only", "Battery (Peak Shaving)"])
        st.divider()
        
        # Route UI parameter gathering dynamically using the dynamic gatekeeper key
        if scenario_mode == "Solar PV Only":
            params = render_solar_ui(scenario_id=selected_baseline)
        else:
            params = render_battery_ui() # Keeps old battery layout link intact
            
        st.divider()
        st.write("### 🎨 Chart Colors")
        col_raw = st.color_picker("Original Load Color", "#A9A9A9")
        col_opt = st.color_picker("Optimized Load Color", "#00CC96")
        col_soc = st.color_picker("Battery SoC Color", "#636EFA")
        col_act = st.color_picker("Battery Action Color", "#FFA15A")
        
        st.divider()
        # Execution Trigger button
        run_sim = st.button("🚀 Run Isolated Simulation", type="primary", use_container_width=True)

    # --- 2. PIPELINE EXECUTION ENGINE ---
    # Catch computation triggers and park data inside session state memory to survive down-stream re-runs
    if run_sim:
        with st.spinner("Processing physical interval math..."):
            if scenario_mode == "Solar PV Only":
                # Execute our upgraded layer 2 & 3 solar engine
                calculated_df = generate_solar_profile(baseline_df, project_metadata, params)
                # Standardize column name so downstream metrics & PDF logic remain fully compatible
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
            else:
                # Fallback to old isolated scenario router for battery logic
                calculated_df = run_isolated_scenario(baseline_df, "Battery (Peak Shaving)", params, grid_limit, res)
            
            # Lock into session memory
            st.session_state['active_sim_results'] = calculated_df
            st.session_state['active_sim_mode'] = scenario_mode

    # --- 3. RENDERING CHARTS & EVALUATIONS ---
    # Only render visual graphics if a valid simulation run is stored in memory
    if 'active_sim_results' in st.session_state and st.session_state['active_sim_results'] is not None:
        results = st.session_state['active_sim_results']
        current_mode = st.session_state['active_sim_mode']
        
        with col_chart:
            st.subheader(f"⚡ Grid Interaction: {current_mode}")
            fig_load = go.Figure()
            
            # Baseline trace
            fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                          name="Original Demand", line=dict(color=col_raw, width=1)))
            # Optimized trace (Works for both Solar and BESS seamlessly now!)
            fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                          name="Final Grid Demand", line=dict(color=col_opt, width=2)))
            
            # Add solar generation curve as a filled visual area if solar was chosen
            if current_mode == "Solar PV Only" and 'solar_gen_kw' in results.columns:
                fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['solar_gen_kw'], 
                                              name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy'))
                                          
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
            fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_load, use_container_width=True)

            # Battery action charts rendering
            if current_mode == "Battery (Peak Shaving)":
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
        # UNIFIED METRICS & PDF EXPORT
        # ==========================================
        st.divider()
        st.write("### 📈 Technical Evaluation & Export")
        
        c1, c2, c3, c4 = st.columns(4)
        peak_orig = results['consumption_kw'].max()
        peak_new = results['final_grid_load_kw'].max()
        
        c1.metric("Original Peak Load", f"{peak_orig:.1f} kW")
        c2.metric("New Peak Load", f"{peak_new:.1f} kW", delta=f"{peak_new - peak_orig:.1f} kW", delta_color="inverse")
        
        min_reqs = {"min_power_kw": 0, "true_min_capacity_kwh": 0}
        if current_mode == "Battery (Peak Shaving)":
            min_reqs = get_exact_minimum_requirements(baseline_df, grid_limit, res)
            c3.metric("Req. Battery Power", f"{min_reqs['min_power_kw']:.1f} kW")
            c4.metric("Req. Battery Cap.", f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")
        else:
            # Display nice placeholders or solar specific data if applicable
            c3.metric("Req. Battery Power", "N/A (Solar Mode)")
            c4.metric("Req. Battery Cap.", "N/A (Solar Mode)")

        # Secure PDF Export Integration
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
                        report_title=f"{report_name}_{current_mode.replace(' ', '')}", 
                        metrics=pdf_metrics, 
                        plot_data=results, 
                        battery_enabled=(current_mode == "Battery (Peak Shaving)")
                    )
                    st.download_button(
                        label="⬇️ Download PDF", 
                        data=pdf_data,
                        file_name=f"{report_name}_{current_mode.replace(' ', '')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as pdf_error:
                    st.error(f"Error during document compilation: {pdf_error}")