# tabs/tab2_scenarios.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import copy

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
        
    vault = st.session_state['scenario_vault']
    saved_scenarios = list(vault.keys())
    
    st.write("### 📂 1. Select Scenario to View or Edit")
    selected_name = st.selectbox("Choose a Base Profile or an existing Sub-Scenario Variant:", saved_scenarios)
    
    current_item = vault[selected_name]
    parent_name = current_item.get('parent')
    
    # DETERMINATION LOGIC: Find the true untouched raw consumption data
    if parent_name and parent_name in vault:
        # We are editing an existing Sub-Scenario Variant!
        baseline_df = vault[parent_name]['df'].copy()
        grid_limit = vault[parent_name].get('grid_limit', 120.0)
        project_metadata = vault[parent_name].get('params', {}).get('project_metadata', {})
        res = vault[parent_name].get('params', {}).get('resolution', 15)
        is_variant_mode = True
    else:
        # We are working on a fresh, clean Base Scenario!
        baseline_df = current_item['df'].copy()
        grid_limit = current_item.get('grid_limit', 120.0)
        project_metadata = current_item.get('params', {}).get('project_metadata', {})
        res = current_item.get('params', {}).get('resolution', 15)
        is_variant_mode = False

    report_name = st.session_state.get('report_name', f"Report_{selected_name}")

    # --- ROUTINE: AUTO-LOAD PREVIOUSLY SAVED STATE ON SELECTION CHANGE ---
    if st.session_state.get('last_selected_scen_tab2') != selected_name:
        st.session_state['last_selected_scen_tab2'] = selected_name
        
        # Load the corresponding widget hardware values into active working memory
        if 'loaded_params' not in st.session_state:
            st.session_state['loaded_params'] = {}
            
        if is_variant_mode:
            st.session_state['loaded_params']['hardware_params'] = current_item.get('params', {}).get('hardware_params', {})
            st.session_state['active_sim_results'] = current_item['df']
            st.session_state['active_sim_mode'] = current_item.get('data_source', 'Battery (BESS) Only')
            st.session_state['active_sim_params'] = current_item['params'].get('hardware_params', {})
        else:
            st.session_state['loaded_params']['hardware_params'] = {}
            st.session_state['active_sim_results'] = None
            st.session_state['active_sim_mode'] = "Battery (BESS) Only"
            st.session_state['active_sim_params'] = {}
        st.rerun()

    st.divider()

    # Layout Setup
    col_input, col_chart = st.columns([1, 2.5])
    
    with col_input:
        st.write("### 2. Configure System Technology")
        
        active_mode = st.session_state.get('active_sim_mode', "Battery (BESS) Only")
        valid_modes = ["Solar PV Only", "Battery (BESS) Only", "Generator Only", "Grid Upgrade Only", "Combined (All)"]
        if active_mode not in valid_modes:
            active_mode = "Battery (BESS) Only"
            
        scenario_mode = st.radio(
            "Choose system configuration:", 
            valid_modes,
            index=valid_modes.index(active_mode)
        )
        st.divider()
        
        hw_draft = st.session_state.get('loaded_params', {}).get('hardware_params', {})
        if hw_draft is None:
            hw_draft = {}
        
        with st.form(key=f"sim_form_{scenario_mode}"):
            params = {}
            if scenario_mode == "Solar PV Only":
                with st.expander("Configure Solar PV", expanded=True):
                    params = render_solar_ui(scenario_id=selected_name)
            elif scenario_mode == "Battery (BESS) Only":
                with st.expander("Configure Battery Storage", expanded=True):
                    params = render_battery_ui(
                        scenario_id=selected_name, 
                        default_grid_limit=grid_limit,
                        existing_params=hw_draft
                    )
            elif scenario_mode == "Generator Only":
                with st.expander("Configure Backup Generator", expanded=True):
                    params = render_generator_ui(scenario_id=selected_name)
            elif scenario_mode == "Grid Upgrade Only":
                with st.expander("Configure Grid Upgrade", expanded=True):
                    params = render_grid_upgrade_ui(scenario_id=selected_name)
            else: 
                with st.expander("Configure Solar PV", expanded=False):
                    params['solar'] = render_solar_ui(scenario_id=f"{selected_name}_c_sol")
                with st.expander("Configure Battery Storage", expanded=False):
                    bat_draft = hw_draft.get('battery', {}) if isinstance(hw_draft, dict) and 'battery' in hw_draft else hw_draft
                    params['battery'] = render_battery_ui(
                        scenario_id=f"{selected_name}_c_bat", 
                        default_grid_limit=grid_limit,
                        existing_params=bat_draft
                    )
                with st.expander("Configure Backup Generator", expanded=False):
                    params['generator'] = render_generator_ui(scenario_id=f"{selected_name}_c_gen")
                
            st.divider()

            with st.expander("🎨 Chart Colors (Settings)", expanded=False):
                col_raw = st.color_picker("Original Load Color", "#A9A9A9")
                col_opt = st.color_picker("Optimized Load Color", "#00CC96")
                col_soc = st.color_picker("Battery SoC Color", "#636EFA")
                col_act = st.color_picker("Battery Action Color", "#FFA15A")
                col_gen = st.color_picker("Generator Output Color", "#8B0000")
            
            st.divider()
            
            button_label = "🔄 Update Variant Data" if is_variant_mode else "🚀 Run Simulation Pipeline"
            run_sim = st.form_submit_button(button_label, type="primary", use_container_width=True)

    # --- 2. PIPELINE EXECUTION ENGINE ---
    if run_sim:
        with st.spinner("Processing physical interval math cascade..."):
            # We strip any historical calculation columns from baseline to avoid pollution loops
            clean_base_df = baseline_df[['timestamp', 'consumption_kw']].copy()
            
            if scenario_mode == "Solar PV Only":
                calculated_df = generate_solar_profile(clean_base_df, project_metadata, params)
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
            elif scenario_mode == "Battery (BESS) Only":
                calculated_df = run_isolated_scenario(clean_base_df, "Battery (Peak Shaving)", params, grid_limit, res)
            elif scenario_mode == "Generator Only":
                calculated_df = simulate_generator_logic(clean_base_df, grid_limit, params, res)
            elif scenario_mode == "Grid Upgrade Only":
                calculated_df = clean_base_df.copy()
                calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
                calculated_df['battery_action_kw'] = 0.0
                calculated_df['solar_gen_kw'] = 0.0
                calculated_df['generator_action_kw'] = 0.0
            else:
                df_1 = generate_solar_profile(clean_base_df, project_metadata, params['solar'])
                df_2 = simulate_battery_logic(df_1, grid_limit, params['battery'], res)
                calculated_df = simulate_generator_logic(df_2, grid_limit, params['generator'], res)
            
            # PIPELINE ROUTING: Determine target destination for saving
            if is_variant_mode:
                # Direct overwrite of the selected variant item
                vault[selected_name]['df'] = calculated_df
                vault[selected_name]['data_source'] = scenario_mode
                vault[selected_name]['params']['hardware_params'] = params
                if scenario_mode == "Grid Upgrade Only":
                    vault[selected_name]['grid_limit'] = params.get("new_grid_limit_kw", grid_limit)
                st.success(f"✅ Sub-Scenario '{selected_name}' successfully updated!")
                save_target_name = selected_name
            else:
                # Creating a brand new separate sub-scenario entity to keep baseline untouched!
                save_target_name = f"{selected_name} + {scenario_mode.split(' ')[0]}"
                vault[save_target_name] = {
                    "df": calculated_df,
                    "parent": selected_name,
                    "data_source": scenario_mode,
                    "grid_limit": params.get("new_grid_limit_kw", grid_limit) if scenario_mode == "Grid Upgrade Only" else grid_limit,
                    "params": {"is_hardware": True, "hardware_params": params}
                }
                st.success(f"✅ Created new variant target: '{save_target_name}' !")
                
            st.session_state['scenario_vault'] = vault
            st.session_state['loaded_params']['hardware_params'] = params
            st.session_state['active_sim_results'] = calculated_df
            st.session_state['active_sim_mode'] = scenario_mode
            st.session_state['active_sim_params'] = params
            st.rerun()

    # --- 3. RENDERING VISUALIZATIONS & METRICS ---
    if 'active_sim_results' in st.session_state and st.session_state['active_sim_results'] is not None:
        results = st.session_state['active_sim_results']
        current_mode = st.session_state['active_sim_mode']
        current_params = st.session_state.get('active_sim_params', {})
        
        with col_chart:
            st.subheader(f"⚡ Live View: {selected_name}")
            render_feasibility_check(results, grid_limit, current_params, current_mode)
            
            fig_load = go.Figure()
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['consumption_kw'], name="Original Demand", line=dict(color=col_raw, width=1)))
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['final_grid_load_kw'], name="Optimized Grid Demand", line=dict(color=col_opt, width=2)))
            
            if current_mode in ["Solar PV Only", "Combined (All)"] and 'solar_gen_kw' in results.columns:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy'))
            if current_mode in ["Generator Only", "Combined (All)"] and 'generator_action_kw' in results.columns:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name="Generator Output", line=dict(color=col_gen, width=1), fill='tozeroy'))
                                          
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
            fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_load, use_container_width=True)

            if current_mode in ["Generator Only", "Combined (All)"] and 'generator_fuel_l' in results.columns:
                total_fuel = results['generator_fuel_l'].sum()
                if total_fuel > 0:
                    st.error(f"🛢️ **Total Diesel Fuel Consumed by Generator:** {total_fuel:,.1f} Liters")
                else:
                    st.success("🌱 No generator fuel required! The system handled all peaks.")

            if current_mode in ["Battery (BESS) Only", "Combined (All)"]:
                c_left, c_right = st.columns(2)
                with c_left:
                    st.write("**Battery Action (kW)**")
                    fig_act = go.Figure()
                    fig_act.add_trace(go.Bar(x=results['timestamp'], y=results['battery_action_kw'], marker_color=col_act))
                    fig_act.update_layout(height=230, margin=dict(t=10, b=10))
                    st.plotly_chart(fig_act, use_container_width=True)
                with c_right:
                    st.write("**Battery State of Charge (kWh)**")
                    fig_soc = go.Figure()
                    fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color=col_soc)))
                    fig_soc.update_layout(height=230, margin=dict(t=10, b=10))
                    st.plotly_chart(fig_soc, use_container_width=True)

        # RETRIEVE METRICS: Safely store outputs from the performance matrix for PDF rendering
        peak_orig, min_reqs = render_performance_matrix(results, baseline_df, grid_limit, res, current_mode, current_params, project_metadata)

        # --- 4. ADVANCED PDF REPORT GENERATION ---
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
                        battery_enabled=(current_mode in ["Battery (BESS) Only", "Combined (All)"])
                    )
                    st.download_button(
                        label="⬇️ Download Document", 
                        data=pdf_data, 
                        file_name=f"{report_name}_{current_mode.replace(' ', '')}.pdf", 
                        mime="application/pdf"
                    )
                except Exception as pdf_error:
                    st.error(f"Error during document compilation: {pdf_error}")

        # --- 5. HARDWARE SUB-SCENARIO STORAGE & CLONING ---
        st.divider()
        st.write("### 💾 Create a Copy (Optional)")
        st.info("Your changes are automatically saved to the active scenario! If you want to keep this setup and experiment with alternatives, save it as a new copy below.")
        
        default_name = f"{selected_name}_Copy"
        sub_scenario_name = st.text_input("Name this Copy:", value=default_name)
        
        name_exists = sub_scenario_name in vault
        save_disabled = False
        
        vault_button_text = "🚀 Save as New Copy"
        if name_exists:
            st.warning(f"⚠️ A variant named '{sub_scenario_name}' already exists. Overwriting will permanently replace the old configuration data.")
            overwrite = st.checkbox("Confirm: Overwrite existing variant", value=False)
            if not overwrite:
                save_disabled = True
            else:
                vault_button_text = "⚠️ OVERWRITE Existing Variant"
        
        if st.button(vault_button_text, type="primary", use_container_width=True, disabled=save_disabled):
            vault[sub_scenario_name] = copy.deepcopy(vault[selected_name])
            st.session_state['scenario_vault'] = vault
            st.success(f"✅ Copy '{sub_scenario_name}' has been successfully created!")
            st.rerun()