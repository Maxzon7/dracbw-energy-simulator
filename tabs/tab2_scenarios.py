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

# Logik
from logic.energy_logic import simulate_battery_logic, simulate_generator_logic 

def render_tab2_scenarios():
    """
    Master Tab 2: Scenario Engine. Manages isolated and combined simulation pipelines.
    Now uses a strict "Compute & Commit" architecture to protect vault data while ensuring high UI performance.
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

    # --- TÜRSTEHER (Sicherheits-Check) ---
    if 'df' not in current_item:
        st.info("⚠️ This project is still empty. Please go to '1️⃣ Baseline', load or generate a profile, and click 'Save Profile' first.")
        return
    # -------------------------------------------
    
    parent_name = current_item.get('parent')
    
    # DETERMINATION LOGIC: Base vs. Variant
    if parent_name and parent_name in vault:
        # Editing an existing Sub-Scenario Variant
        baseline_df = vault[parent_name]['df'].copy()
        grid_limit = vault[parent_name].get('grid_limit', 120.0)
        project_metadata = vault[parent_name].get('params', {}).get('project_metadata', {})
        res = vault[parent_name].get('params', {}).get('resolution', 15)
        is_variant_mode = True
    else:
        # Working on a pristine Base Scenario
        baseline_df = current_item['df'].copy()
        grid_limit = current_item.get('grid_limit', 120.0)
        project_metadata = current_item.get('params', {}).get('project_metadata', {})
        res = current_item.get('params', {}).get('resolution', 15)
        is_variant_mode = False

    report_name = st.session_state.get('report_name', f"Report_{selected_name}")

    # --- STATE SYNCHRONIZATION (Load Vault -> Memory) ---
    if st.session_state.get('last_selected_scen_tab2') != selected_name:
        st.session_state['last_selected_scen_tab2'] = selected_name
        
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
        
        # =========================================================
        # THE PERFORMANCE FORTRESS (st.form)
        # Prevents constant reruns while dragging sliders.
        # =========================================================
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
            
            # Button just triggers calculation, NOT saving!
            run_sim = st.form_submit_button("🔄 Calculate Preview", type="secondary", use_container_width=True)

        # =========================================================
        # PIPELINE EXECUTION ENGINE (Vorschau generieren)
        # =========================================================
        if run_sim:
            with st.spinner("Processing physical interval math cascade..."):
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
                
                # WRITE TO DRAFT MEMORY ONLY (Schmierblatt)
                st.session_state['loaded_params']['hardware_params'] = params
                st.session_state['active_sim_results'] = calculated_df
                st.session_state['active_sim_mode'] = scenario_mode
                st.session_state['active_sim_params'] = params
                # We do NOT rerun here. We let the script continue so the Draft Monitor below catches it.

        # =========================================================
        # DRAFT MODE MONITOR (Tresor-Vergleich & Commit)
        # =========================================================
        active_preview_mode = st.session_state.get('active_sim_mode')
        active_preview_params = st.session_state.get('active_sim_params')
        is_draft = False
        
        # Check if we have calculated data in memory
        if active_preview_params and active_preview_mode:
            saved_mode = current_item.get('data_source')
            saved_params = current_item.get('params', {}).get('hardware_params', {})
            
            # Compare memory with vault. If they differ, the user has uncommitted changes.
            if active_preview_mode != saved_mode or active_preview_params != saved_params:
                is_draft = True

        if is_draft:
            st.markdown("<br>", unsafe_allow_html=True)
            st.warning("⚠️ **Unsaved Preview!**\nThe charts are showing a temporary draft. Click below to securely save these changes to the vault.")
            
            commit_label = "💾 Update Existing Variant" if is_variant_mode else "💾 Save as New Variant"
            
            # THE COMMIT BUTTON (Outside the form!)
            if st.button(commit_label, type="primary", use_container_width=True):
                if is_variant_mode:
                    # Overwrite existing
                    vault[selected_name]['df'] = st.session_state['active_sim_results']
                    vault[selected_name]['data_source'] = active_preview_mode
                    vault[selected_name]['params']['hardware_params'] = active_preview_params
                    if active_preview_mode == "Grid Upgrade Only":
                        vault[selected_name]['grid_limit'] = active_preview_params.get("new_grid_limit_kw", grid_limit)
                    st.success(f"✅ Variant '{selected_name}' successfully updated!")
                else:
                    # Create new variant
                    save_target_name = f"{selected_name} + {active_preview_mode.split(' ')[0]}"
                    vault[save_target_name] = {
                        "df": st.session_state['active_sim_results'],
                        "parent": selected_name,
                        "data_source": active_preview_mode,
                        "grid_limit": active_preview_params.get("new_grid_limit_kw", grid_limit) if active_preview_mode == "Grid Upgrade Only" else grid_limit,
                        "params": {"is_hardware": True, "hardware_params": active_preview_params}
                    }
                    st.session_state['last_selected_scen_tab2'] = save_target_name
                    st.success(f"✅ New Variant '{save_target_name}' successfully secured!")
                    
                st.session_state['scenario_vault'] = vault
                st.rerun()

    # --- 3. RENDERING VISUALIZATIONS & METRICS ---
    if 'active_sim_results' in st.session_state and st.session_state['active_sim_results'] is not None:
        results = st.session_state['active_sim_results']
        current_mode = st.session_state['active_sim_mode']
        current_params = st.session_state.get('active_sim_params', {})
        
        with col_chart:
            # Show a visual indicator if they are looking at a Draft
            if is_draft:
                st.subheader(f"⚡ Live View: [UNSAVED DRAFT PREVIEW]")
            else:
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

        # RETRIEVE METRICS
        peak_orig, min_reqs = render_performance_matrix(results, baseline_df, grid_limit, res, current_mode, current_params, project_metadata)

        # --- 4. ADVANCED PDF REPORT GENERATION ---
        st.divider()
        if st.button("📄 Generate Technical PDF Report", type="primary"):
            # Only allow PDF export if the data is saved (not in draft mode)
            if is_draft:
                st.error("Please Save (Commit) your changes to the vault before generating a PDF.")
            else:
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
        st.info("Want to keep this setup and experiment with alternatives? Save it as a new copy below.")
        
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
        
        # Only allow copying if the current state is safely committed
        if is_draft:
            st.error("Please commit your current draft before duplicating the scenario.")
        else:
            if st.button(vault_button_text, type="primary", use_container_width=True, disabled=save_disabled):
                vault[sub_scenario_name] = copy.deepcopy(vault[selected_name])
                st.session_state['scenario_vault'] = vault
                st.success(f"✅ Copy '{sub_scenario_name}' has been successfully created!")
                st.rerun()