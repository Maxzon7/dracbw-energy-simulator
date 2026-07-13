# tabs/tab2_scenarios.py
import streamlit as st
import pandas as pd

# Sub-components imports
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.solar_logic import generate_solar_profile
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.generator_ui import render_generator_ui
from tabs.tab2_components.scenario_engine import run_isolated_scenario
from tabs.tab2_components.grid_upgrade_ui import render_grid_upgrade_ui
from tabs.tab2_components.results_viewer import render_results_and_charts

from logic.energy_logic import simulate_battery_logic, simulate_generator_logic

# --- UNSERE NEUEN KLASSEN-TOOLS ---
from classes.models import SubScenario, FinancialParams
from logic.storage_manager import get_all_base_scenarios, get_base_scenario, add_sub_scenario

def render_tab2_scenarios():
    st.header("Scenario Simulation (Hardware Integration)")

    bases = get_all_base_scenarios()
    if not bases:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return

    base_names = [b.name for b in bases]
    selected_base_name = st.selectbox("### 📂 1. Select Project (Baseline)", base_names)
    active_base = get_base_scenario(selected_base_name)

    if active_base.original_profile is None:
        st.info(f"⚠️ Project '{selected_base_name}' has no data yet. Please go to Tab 1 and click 'Process & Save'.")
        return

    baseline_df = active_base.original_profile.copy()
    grid_limit = active_base.base_tariff.contracted_capacity_kw
    project_metadata = {}
    res = 15

    st.divider()
    col_input, col_chart = st.columns([1, 2.5])

    with col_input:
        st.write("### 2. Configure System Technology")
        active_mode = st.session_state.get('active_sim_mode', "Battery (BESS) Only")
        
        # Parse active_mode state to set checkbox defaults
        if isinstance(active_mode, str):
            default_solar = "Solar" in active_mode or "Combined" in active_mode or active_mode == "All"
            default_battery = "Battery" in active_mode or "BESS" in active_mode or "Combined" in active_mode or active_mode == "All"
            default_generator = "Generator" in active_mode or "Combined" in active_mode or active_mode == "All"
            default_grid = "Grid" in active_mode or "Combined" in active_mode or active_mode == "All"
        elif isinstance(active_mode, dict):
            default_solar = active_mode.get('solar', False)
            default_battery = active_mode.get('battery', False)
            default_generator = active_mode.get('generator', False)
            default_grid = active_mode.get('grid', False)
        else:
            default_solar, default_battery, default_generator, default_grid = False, True, False, False

        # Independent Checkboxes for Dynamic Combinations
        enable_solar = st.checkbox("☀️ Integrate Solar PV", value=default_solar)
        enable_battery = st.checkbox("🔋 Integrate Battery (BESS)", value=default_battery)
        enable_generator = st.checkbox("🛢️ Integrate Backup Generator", value=default_generator)
        enable_grid = st.checkbox("⚡ Grid Capacity Upgrade", value=default_grid)

        # Build dynamic scenario mode label
        active_mode_list = []
        if enable_solar: active_mode_list.append("Solar")
        if enable_battery: active_mode_list.append("BESS")
        if enable_generator: active_mode_list.append("Generator")
        if enable_grid: active_mode_list.append("Grid Upgrade")
        
        scenario_mode = " + ".join(active_mode_list) if active_mode_list else "None"
        active_sim_mode_dict = {
            'solar': enable_solar,
            'battery': enable_battery,
            'generator': enable_generator,
            'grid': enable_grid
        }

        with st.form("scenario_tech_form"):
            hw_draft = st.session_state.get('active_sim_params', {})
            params = {}
            
            if enable_solar:
                solar_draft = hw_draft.get('solar', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure Solar PV", True): 
                    params['solar'] = render_solar_ui(selected_base_name + "_sol")
            if enable_battery:
                battery_draft = hw_draft.get('battery', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure BESS (Battery)", True): 
                    params['battery'] = render_battery_ui(selected_base_name + "_bat", grid_limit, battery_draft)
            if enable_generator:
                generator_draft = hw_draft.get('generator', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure Generator", True): 
                    params['generator'] = render_generator_ui(selected_base_name + "_gen")
            if enable_grid:
                grid_draft = hw_draft.get('grid', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure Grid Upgrade", True): 
                    params['grid'] = render_grid_upgrade_ui(selected_base_name + "_grid")

            with st.expander("Chart Colors", expanded=False):
                colors = {
                    'raw': st.color_picker("Original", "#A9A9A9"),
                    'opt': st.color_picker("Optimized", "#00CC96"),
                    'soc': st.color_picker("SoC", "#636EFA"),
                    'act': st.color_picker("Action", "#FFA15A"),
                    'gen': st.color_picker("Generator", "#8B0000")
                }
            
            run_sim = st.form_submit_button("Run / Update Simulation", type="primary", use_container_width=True)

        # Decide whether to run calculations or use cached values
        should_calculate = run_sim or \
                           st.session_state.get('last_calculated_project') != selected_base_name or \
                           st.session_state.get('active_sim_mode') != active_sim_mode_dict or \
                           'active_sim_results' not in st.session_state

        if should_calculate:
            st.session_state['chart_colors'] = colors
            
            clean_base_df = baseline_df[['timestamp', 'consumption_kw']].copy() if 'timestamp' in baseline_df.columns else baseline_df.copy()
            calculated_df = clean_base_df.copy()
            calculated_df['solar_gen_kw'] = 0.0
            calculated_df['battery_action_kw'] = 0.0
            calculated_df['battery_soc_kwh'] = 0.0
            calculated_df['generator_action_kw'] = 0.0
            calculated_df['generator_fuel_l'] = 0.0
            calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
            
            # Step 1: Grid Upgrade (resolves the target grid limit used in downstream simulations)
            sim_grid_limit = grid_limit
            if enable_grid and 'grid' in params:
                sim_grid_limit = params['grid'].get('new_grid_limit_kw', grid_limit)
                
            # Step 2: Solar PV Integration
            if enable_solar and 'solar' in params:
                calculated_df = generate_solar_profile(calculated_df, project_metadata, params['solar'])
            else:
                calculated_df['solar_gen_kw'] = 0.0
                calculated_df['net_load_kw'] = calculated_df['consumption_kw']
                calculated_df['grid_feed_in_kw'] = 0.0
                
            # Step 3: Battery (BESS) Simulation
            if enable_battery and 'battery' in params:
                calculated_df = simulate_battery_logic(calculated_df, sim_grid_limit, params['battery'], res)
            else:
                calculated_df['battery_action_kw'] = 0.0
                calculated_df['battery_soc_kwh'] = 0.0
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                
            # Step 4: Backup Generator Simulation
            if enable_generator and 'generator' in params:
                calculated_df = simulate_generator_logic(calculated_df, sim_grid_limit, params['generator'], res)
            else:
                calculated_df['generator_action_kw'] = 0.0
                calculated_df['generator_fuel_l'] = 0.0
                
            if 'final_grid_load_kw' not in calculated_df.columns:
                calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']

            st.session_state['active_sim_results'] = calculated_df
            st.session_state['active_sim_mode'] = active_sim_mode_dict
            st.session_state['active_sim_params'] = params
            st.session_state['last_calculated_project'] = selected_base_name
        else:
            calculated_df = st.session_state['active_sim_results']
            params = st.session_state['active_sim_params']

        st.divider()
        st.write("### Save Variant")
        scenario_name_input = st.text_input("Name for this variant:", value=f"Option: {scenario_mode}")
        financials_active = st.toggle("Enter financial parameters? (Optional)")
        financial_module = None

        if financials_active:
            with st.container():
                col1, col2 = st.columns(2)
                
                # Sum CAPEX and OPEX dynamically from all active sub-components
                default_capex = 0.0
                if enable_solar and 'solar' in params:
                    default_capex += float(params['solar'].get('total_capex', 0.0))
                if enable_battery and 'battery' in params:
                    default_capex += float(params['battery'].get('total_capex', 0.0))
                if enable_grid and 'grid' in params:
                    default_capex += float(params['grid'].get('upgrade_capex', 0.0))

                capex_input = col1.number_input("Purchase Price (€) [CAPEX]", value=default_capex, step=1000.0)
                opex_input = col2.number_input("Maintenance/Year (€) [OPEX]", value=float(default_capex * 0.02), step=100.0)
                financial_module = FinancialParams(capex=capex_input, opex_yearly=opex_input, lifespan_years=15)

        if st.button("Save Variant", type="primary", use_container_width=True):
            b_kwh = params.get('battery', {}).get('b_cap', 0.0) if enable_battery and 'battery' in params else 0.0
            b_kw = params.get('battery', {}).get('b_pwr', 0.0) if enable_battery and 'battery' in params else 0.0
            s_kwp = params.get('solar', {}).get('installed_kwp', 0.0) if enable_solar and 'solar' in params else 0.0

            new_sub = SubScenario(
                name=scenario_name_input,
                battery_kwh=b_kwh, battery_kw=b_kw, solar_kwp=s_kwp,
                simulated_profile=calculated_df,
                financials=financial_module
            )
            add_sub_scenario(selected_base_name, new_sub)
            st.success(f"Variant '{scenario_name_input}' successfully saved! Go to Tab 3 for comparison.")

    # RENDERING VISUALS (Rechte Seite) - Jetzt immer sichtbar!
    with col_chart:
        colors_to_use = st.session_state.get('chart_colors', {'raw': "#A9A9A9", 'opt': "#00CC96", 'soc': "#636EFA", 'act': "#FFA15A", 'gen': "#8B0000"})
        render_results_and_charts(
            calculated_df, baseline_df, grid_limit, res,
            scenario_mode, params, project_metadata, selected_base_name, False, colors_to_use, f"Report_{selected_base_name}"
        )