# tabs/tab2_scenarios.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Clean imports from our sub-components packaging
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.solar_logic import generate_solar_profile
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.generator_ui import render_generator_ui 
from tabs.tab2_components.scenario_engine import run_isolated_scenario
# NEU IMPORTIERT: Grid Upgrade
from tabs.tab2_components.grid_upgrade_ui import render_grid_upgrade_ui

# Technical additions & Out-sourced Sub-components
from tabs.tab2_components.pdf_export import generate_tech_pdf
from tabs.tab2_components.feasibility_check import render_feasibility_check
from tabs.tab2_components.performance_matrix import render_performance_matrix

# NEU: Wir importieren jetzt auch unsere Generator-Logik
from logic.energy_logic import simulate_battery_logic, simulate_generator_logic 

def render_tab2_scenarios():
    """
    Master Tab 2: Scenario Engine. Manages isolated and combined simulation pipelines (Solar + BESS cascade),
    synchronizes interface widgets, and provides advanced DRACBV technical metrics with dynamic UX controls.
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
        st.write("###  2. Select Technology")
        
        # NEU: Radio Buttons um den Generator erweitert
       # NEU: Radio Buttons um Grid Upgrade erweitert
        scenario_mode = st.radio(
            "Choose system configuration:", 
            ["Solar PV Only", "Battery (BESS) Only", "Generator Only", "Grid Upgrade Only", "Combined (All)"]
        )
        st.divider()
        
        # --- BATCHING FORM: Stops slider-spam from reloading the app repeatedly ---
        with st.form(key=f"sim_form_{scenario_mode}"):
            params = {}
            if scenario_mode == "Solar PV Only":
                with st.expander("Configure Solar PV", expanded=True):
                    params = render_solar_ui(scenario_id=selected_baseline)
                    
            elif scenario_mode == "Battery (BESS) Only":
                with st.expander("Configure Battery Storage", expanded=True):
                    params = render_battery_ui(scenario_id=selected_baseline, default_grid_limit=grid_limit) 
            
            elif scenario_mode == "Generator Only":
                with st.expander("Configure Backup Generator", expanded=True):
                    params = render_generator_ui(scenario_id=selected_baseline)
            elif scenario_mode == "Grid Upgrade Only":
                with st.expander("Configure Grid Upgrade", expanded=True):
                    params = render_grid_upgrade_ui(scenario_id=selected_baseline)
                    
            else: # Combined Mode (Die ultimative Kaskade)
                with st.expander("Configure Solar PV", expanded=False):
                    params['solar'] = render_solar_ui(scenario_id=f"{selected_baseline}_c_sol")
                with st.expander("Configure Battery Storage", expanded=False):
                    params['battery'] = render_battery_ui(scenario_id=f"{selected_baseline}_c_bat", default_grid_limit=grid_limit)
                with st.expander("Configure Backup Generator", expanded=False):
                    params['generator'] = render_generator_ui(scenario_id=f"{selected_baseline}_c_gen")
                
            st.divider()

            with st.expander("🎨 Chart Colors (Settings)", expanded=False):
                col_raw = st.color_picker("Original Load Color", "#A9A9A9")
                col_opt = st.color_picker("Optimized Load Color", "#00CC96")
                col_soc = st.color_picker("Battery SoC Color", "#636EFA")
                col_act = st.color_picker("Battery Action Color", "#FFA15A")
                col_gen = st.color_picker("Generator Output Color", "#8B0000") # Dunkelrot für den Diesel
            
            st.divider()
            
            sim_button_text = "🚀 Run Simulation"
            if 'active_sim_results' in st.session_state and st.session_state['active_sim_results'] is not None:
                sim_button_text = "🔄 Rerun Simulation"
                
            run_sim = st.form_submit_button(sim_button_text, type="primary", use_container_width=True)

    # --- 2. PIPELINE EXECUTION ENGINE ---
    if run_sim:
        with st.spinner("Processing physical interval math cascade..."):
            if scenario_mode == "Solar PV Only":
                calculated_df = generate_solar_profile(baseline_df, project_metadata, params)
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                
            elif scenario_mode == "Battery (BESS) Only":
                calculated_df = run_isolated_scenario(baseline_df, "Battery (Peak Shaving)", params, grid_limit, res)
                
            elif scenario_mode == "Generator Only":
                # Isolierte Generator-Berechnung auf der Baseline
                calculated_df = simulate_generator_logic(baseline_df.copy(), grid_limit, params, res)
            
            elif scenario_mode == "Grid Upgrade Only":
                # Grid Upgrade changes nothing about the load, it just moves the limit up!
                calculated_df = baseline_df.copy()
                calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
                
                # Zero out hardware interactions just to be safe
                if 'battery_action_kw' not in calculated_df.columns:
                    calculated_df['battery_action_kw'] = 0.0
                if 'solar_gen_kw' not in calculated_df.columns:
                    calculated_df['solar_gen_kw'] = 0.0
                if 'generator_action_kw' not in calculated_df.columns:
                    calculated_df['generator_action_kw'] = 0.0
                
            else:
                # DIE KASKADE: Solar -> Batterie -> Generator
                df_1 = generate_solar_profile(baseline_df, project_metadata, params['solar'])
                df_2 = simulate_battery_logic(df_1, grid_limit, params['battery'], res)
                calculated_df = simulate_generator_logic(df_2, grid_limit, params['generator'], res)
            
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
            
            # --- THE NEW FEASIBILITY CHECK COMPONENT ---
            render_feasibility_check(results, grid_limit, current_params, current_mode)
            
            fig_load = go.Figure()
            
            # Basis-Linien
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['consumption_kw'], name="Original Demand", line=dict(color=col_raw, width=1)))
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['final_grid_load_kw'], name="Final Grid Demand", line=dict(color=col_opt, width=2)))
            
            # Solar Einblendung
            if current_mode in ["Solar PV Only", "Combined (All)"] and 'solar_gen_kw' in results.columns:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy'))
            
            # Generator Einblendung (NEU)
            if current_mode in ["Generator Only", "Combined (All)"] and 'generator_action_kw' in results.columns:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name="Generator Output", line=dict(color=col_gen, width=1), fill='tozeroy'))
                                          
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
            fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_load, use_container_width=True)

            # --- DIESEL VERBRAUCHS ANZEIGE (NEU) ---
            if current_mode in ["Generator Only", "Combined (All)"] and 'generator_fuel_l' in results.columns:
                total_fuel = results['generator_fuel_l'].sum()
                if total_fuel > 0:
                    st.error(f"🛢️ **Total Diesel Fuel Consumed by Generator:** {total_fuel:,.1f} Liters")
                else:
                    st.success("🌱 No generator fuel required! The system handled all peaks.")

            if current_mode in ["Battery (BESS) Only", "Combined (All)"]:
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
                    fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color=col_soc)))
                    fig_soc.update_layout(height=250, margin=dict(t=10, b=10))
                    st.plotly_chart(fig_soc, use_container_width=True)

        # --- THE OUTSOURCED PERFORMANCE MATRIX ---
        peak_orig, min_reqs = render_performance_matrix(results, baseline_df, grid_limit, res, current_mode, current_params, project_metadata)

        # PDF Export Integration
        st.divider()
        if st.button("📄 Generate Technical PDF Report", type="primary"):
            with st.spinner("Compiling technical evaluation..."):
                try:
                    pdf_metrics = {"grid_limit": grid_limit, "peak_raw": peak_orig, "min_pwr": min_reqs['min_power_kw'], "min_cap": min_reqs['true_min_capacity_kwh']}
                    pdf_data = generate_tech_pdf(report_title=f"{report_name}_{current_mode.replace(' ', '')}", metrics=pdf_metrics, plot_data=results, battery_enabled=(current_mode in ["🔋 Battery (BESS) Only", "⚙️ Combined"]))
                    st.download_button(label="⬇️ Download Document", data=pdf_data, file_name=f"{report_name}_{current_mode.replace(' ', '')}.pdf", mime="application/pdf")
                except Exception as pdf_error:
                    st.error(f"Error during document compilation: {pdf_error}")

        # --- HARDWARE SUB-SCENARIO STORAGE ---
        st.divider()
        st.write("### 💾 Save this variant")
        st.info("Save this configuration as Subscenario to compare it with the base and alternative Sub scenarios.")
        
        default_name = f"{selected_baseline} + {current_mode.split(' ')[1]}" if " " in current_mode else f"{selected_baseline}_Sub"
        sub_scenario_name = st.text_input("Name this Sub-Scenario:", value=default_name)
        
        vault = st.session_state.get('scenario_vault', {})
        name_exists = sub_scenario_name in vault
        save_disabled = False
        overwrite = False
        
        vault_button_text = "🚀 Put variant in the vault"
        
        if name_exists:
            st.warning(f"⚠️ A variant named '{sub_scenario_name}' already exists. Overwriting will permanently replace the old configuration data.")
            overwrite = st.checkbox("Confirm: Overwrite existing variant", value=False)
            if not overwrite:
                save_disabled = True
            else:
                vault_button_text = "⚠️ OVERWRITE Existing Variant"
        
        if st.button(vault_button_text, type="primary", use_container_width=True, disabled=save_disabled):
            # If we explicitly upgraded the grid, save the new limit to the vault!
            if current_mode == "Grid Upgrade Only":
                active_grid_limit = current_params.get("new_grid_limit_kw", 250.0)
            else:
                active_grid_limit = vault[selected_baseline].get('grid_limit', 50.0)

            vault[sub_scenario_name] = {
                "df": results, 
                "parent": selected_baseline, 
                "data_source": current_mode, 
                "grid_limit": active_grid_limit, # <-- Das hier verwendet jetzt das korrekte Limit!
                "params": {"is_hardware": True, "hardware_params": current_params}
            }
            vault[sub_scenario_name] = {
                "df": results, 
                "parent": selected_baseline, 
                "data_source": current_mode, 
                "grid_limit": base_grid_limit,
                "params": {"is_hardware": True, "hardware_params": current_params}
            }
            st.session_state['scenario_vault'] = vault
            st.success(f"✅ '{sub_scenario_name}' has been successfully saved as a variant of '{selected_baseline}' !")