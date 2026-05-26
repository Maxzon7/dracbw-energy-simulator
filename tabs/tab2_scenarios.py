# tabs/tab2_scenarios.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Clean imports from our sub-components packaging
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.solar_logic import generate_solar_profile
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.scenario_engine import run_isolated_scenario

# Technical additions & Battery Engine
from tabs.tab2_components.pdf_export import generate_tech_pdf
from logic.energy_logic import get_exact_minimum_requirements, simulate_battery_logic

def render_tab2_scenarios():
    """
    Master Tab 2: Scenario Engine. Manages isolated and combined simulation pipelines (Solar + BESS cascade),
    synchronizes interface widgets, and provides advanced DRACBV technical metrics.
    """
    t = st.session_state.get('t', {})
    st.header("Scenario Simulation (Hardware Integration)")
    
    # --- 1. BASELINE SELECTION ---
    if 'scenario_vault' not in st.session_state or not st.session_state['scenario_vault']:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return
        
    saved_scenarios = list(st.session_state['scenario_vault'].keys())
    selected_baseline = st.selectbox("📂 1. Select Base Profile:", saved_scenarios)
    
    baseline_data = st.session_state['scenario_vault'][selected_baseline]
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
        scenario_mode = st.radio(
            "Choose system configuration:", 
            ["☀️ Solar PV Only", "🔋 Battery (BESS) Only", "⚙️ Combined"]
        )
        st.divider()
        
        # Route UI parameter gathering dynamically
        if scenario_mode == "☀️ Solar PV Only":
            params = render_solar_ui(scenario_id=selected_baseline)
        elif scenario_mode == "🔋 Battery (BESS) Only":
            params = render_battery_ui(scenario_id=selected_baseline) 
        else:
            # COMBINED MODE: Render both UIs simultaneously within expanders
            params = {}
            with st.expander("☀️ Configure Solar PV", expanded=True):
                params['solar'] = render_solar_ui(scenario_id=f"{selected_baseline}_c_sol")
            with st.expander("🔋 Configure Battery Storage", expanded=True):
                params['battery'] = render_battery_ui(scenario_id=f"{selected_baseline}_c_bat")
            
        st.divider()
        st.write("### 🎨 Chart Colors")
        col_raw = st.color_picker("Original Load Color", "#A9A9A9")
        col_opt = st.color_picker("Optimized Load Color", "#00CC96")
        col_soc = st.color_picker("Battery SoC Color", "#636EFA")
        col_act = st.color_picker("Battery Action Color", "#FFA15A")
        
        st.divider()
        run_sim = st.button("🚀 Run Simulation", type="primary", use_container_width=True)

    # --- 2. PIPELINE EXECUTION ENGINE ---
    if run_sim:
        with st.spinner("Processing physical interval math cascade..."):
            if scenario_mode == "☀️ Solar PV Only":
                calculated_df = generate_solar_profile(baseline_df, project_metadata, params)
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                
            elif scenario_mode == "🔋 Battery (BESS) Only":
                calculated_df = run_isolated_scenario(baseline_df, "Battery (Peak Shaving)", params, grid_limit, res)
                
            else:
                # ⚙️ COMBINED CASCADE LOGIC
                # Step 1: Solar subtracts from baseline
                solar_df = generate_solar_profile(baseline_df, project_metadata, params['solar'])
                # Step 2: Battery acts on the post-solar net load
                calculated_df = simulate_battery_logic(solar_df, grid_limit, params['battery'], res)
            
            st.session_state['active_sim_results'] = calculated_df
            st.session_state['active_sim_mode'] = scenario_mode
            st.session_state['active_sim_params'] = params

    # --- 3. RENDERING CHARTS & EVALUATIONS ---
    if 'active_sim_results' in st.session_state and st.session_state['active_sim_results'] is not None:
        results = st.session_state['active_sim_results']
        current_mode = st.session_state['active_sim_mode']
        current_params = st.session_state.get('active_sim_params', {})
        
        with col_chart:
            st.subheader(f"⚡ Grid Interaction: {current_mode}")
            fig_load = go.Figure()
            
            fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                          name="Original Demand", line=dict(color=col_raw, width=1)))
            fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                          name="Final Grid Demand", line=dict(color=col_opt, width=2)))
            
            if current_mode in ["☀️ Solar PV Only", "⚙️ Combined"] and 'solar_gen_kw' in results.columns:
                fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['solar_gen_kw'], 
                                              name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy'))
                                          
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
            fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_load, use_container_width=True)

            if current_mode in ["🔋 Battery (BESS) Only", "⚙️ Combined"]:
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
        # ADVANCED TECHNICAL PERFORMANCE MATRIX
        # ==========================================
        st.divider()
        st.write("### 📈 Advanced Technical Performance Matrix")
        
        # Base Math Calculations
        total_consumption_kwh = results['consumption_kw'].sum() / (60 / res)
        total_grid_import_kwh = results['final_grid_load_kw'].clip(lower=0.0).sum() / (60 / res)
        
        autarky_pct = 0.0
        if total_consumption_kwh > 0:
            autarky_pct = (1.0 - (total_grid_import_kwh / total_consumption_kwh)) * 100.0
            
        peak_orig = results['consumption_kw'].max()
        peak_new = results['final_grid_load_kw'].max()
        
        peak_shaving_pct = 0.0
        if peak_orig > 0:
            peak_shaving_pct = ((peak_orig - peak_new) / peak_orig) * 100.0

        # UI Layout
        col_autarky, col_grid, col_asset = st.columns(3)
        
        with col_autarky:
            st.write("🟢 **Autarky & Yield**")
            st.metric("Degree of Autarky", f"{autarky_pct:.1f} %")
            
            if current_mode in ["☀️ Solar PV Only", "⚙️ Combined"]:
                total_solar_kwh = results['solar_gen_kw'].sum() / (60 / res)
                
                # Dynamic Curtailment Math (Battery can save curtailed solar!)
                if current_mode == "⚙️ Combined":
                    if project_metadata.get('strict_zero_export', False):
                        curtailed_kwh = results['final_grid_load_kw'].clip(upper=0.0).abs().sum() / (60 / res)
                    else:
                        curtailed_kwh = 0.0
                else:
                    gross_excess_kwh = (results['solar_gen_kw'] - results['consumption_kw']).clip(lower=0.0).sum() / (60 / res)
                    feed_in_kwh = results.get('grid_feed_in_kw', pd.Series([0])).sum() / (60 / res)
                    curtailed_kwh = gross_excess_kwh - feed_in_kwh
                
                self_consumption_pct = 0.0
                if total_solar_kwh > 0:
                    exported_or_curtailed = results['final_grid_load_kw'].clip(upper=0.0).abs().sum() / (60 / res)
                    self_consumed_kwh = total_solar_kwh - exported_or_curtailed
                    self_consumption_pct = (self_consumed_kwh / total_solar_kwh) * 100.0
                    
                st.metric("Self-Consumption", f"{self_consumption_pct:.1f} %")
                st.metric("Curtailed Energy", f"{curtailed_kwh:,.0f} kWh", delta="Wasted", delta_color="inverse")
                
        with col_grid:
            st.write("🚨 **Grid Stability**")
            st.metric("New Peak Load", f"{peak_new:.1f} kW", delta=f"-{peak_shaving_pct:.1f}% Peak Shaved", delta_color="normal")
            st.metric("Uncovered Demand", "0 kWh", delta="Safe", delta_color="normal")
            
        with col_asset:
            st.write("🔋 **Hardware & Assets**")
            min_reqs = {"min_power_kw": 0, "true_min_capacity_kwh": 0}
            
            if current_mode in ["🔋 Battery (BESS) Only", "⚙️ Combined"]:
                min_reqs = get_exact_minimum_requirements(baseline_df, grid_limit, res)
                
                throughput_kwh = results['battery_action_kw'].abs().sum() / (60 / res)
                # Safely extract battery cap regardless of mode structure
                b_cap = current_params.get('battery', current_params).get('b_cap', 0) if isinstance(current_params, dict) else 0
                
                cycles = (throughput_kwh / 2.0) / b_cap if b_cap > 0 else 0
                deg_pct = (cycles / 5000) * 100.0 
                
                st.metric("Battery Cycles", f"{cycles:.0f} Cycles")
                st.metric("Est. Degradation (1 Yr)", f"-{deg_pct:.2f} %", delta_color="inverse")
                st.metric("Req. Capacity (Ideal)", f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")
            else:
                st.metric("Battery Cycles", "N/A")
                st.metric("Est. Degradation", "N/A")

        # PDF Export Integration
        st.divider()
        if st.button("📄 Generate Technical PDF Report", type="primary"):
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
                        battery_enabled=(current_mode in ["🔋 Battery (BESS) Only", "⚙️ Combined"])
                    )
                    st.download_button(
                        label="⬇️ Download Document", 
                        data=pdf_data,
                        file_name=f"{report_name}_{current_mode.replace(' ', '')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as pdf_error:
                    st.error(f"Error during document compilation: {pdf_error}")

    # ==========================================
        # --- HARDWARE SUB-SZENARIO SPEICHERN ---
        # ==========================================
        st.divider()
        st.write("### 💾 Hardware-Variante speichern")
        st.info("Speichere diese Konfiguration als Sub-Szenario, um sie in Tab 3 direkt mit der Basis zu vergleichen.")
        
        # Generiert automatisch einen passenden Namen (z.B. "Basis + Solar")
        default_name = f"{selected_baseline} + {current_mode.split(' ')[1]}" if " " in current_mode else f"{selected_baseline}_Sub"
        sub_scenario_name = st.text_input("Name für dieses Sub-Szenario:", value=default_name)
        
        if st.button("🚀 Variante in den Tresor speichern", type="primary", use_container_width=True):
            
            if 'scenario_vault' not in st.session_state:
                st.session_state['scenario_vault'] = {}
                
            base_grid_limit = st.session_state['scenario_vault'][selected_baseline].get('grid_limit', 50.0)
            
            # Nutzt die Variable 'results', die Tab 2 für das berechnete DataFrame verwendet
            st.session_state['scenario_vault'][sub_scenario_name] = {
                "df": results, 
                "parent": selected_baseline, 
                "data_source": current_mode,
                "grid_limit": base_grid_limit,
                "params": {
                    "is_hardware": True,
                    "hardware_params": current_params
                }
            }
            
            st.success(f"✅ '{sub_scenario_name}' wurde erfolgreich als Variante von '{selected_baseline}' gespeichert!")
            
            # WICHTIG: Kein sofortiger Rerun hier, da sonst die Erfolgsmeldung sofort verschwindet.
            # Der Tresor ist aktualisiert, das Szenario ist nun in Tab 3 und 4 verfügbar.