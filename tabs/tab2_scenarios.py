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
        valid_modes = ["Solar PV Only", "Battery (BESS) Only", "Generator Only", "Grid Upgrade Only", "Combined (All)"]
        scenario_mode = st.radio("Configuration:", valid_modes, index=valid_modes.index(active_mode if active_mode in valid_modes else "Battery (BESS) Only"))

        with st.form("scenario_tech_form"):
            hw_draft = st.session_state.get('active_sim_params', {})
            params = {}
            
            if scenario_mode == "Solar PV Only":
                with st.expander("Configure Solar PV", True): params = render_solar_ui(selected_base_name)
            elif scenario_mode == "Battery (BESS) Only":
                with st.expander("Configure BESS", True): params = render_battery_ui(selected_base_name, grid_limit, hw_draft)
            elif scenario_mode == "Generator Only":
                with st.expander("Configure Generator", True): params = render_generator_ui(selected_base_name)
            elif scenario_mode == "Grid Upgrade Only":
                with st.expander("Configure Grid", True): params = render_grid_upgrade_ui(selected_base_name)
            else:
                with st.expander("Solar PV", False): params['solar'] = render_solar_ui(f"{selected_base_name}_c_sol")
                with st.expander("BESS", False): params['battery'] = render_battery_ui(f"{selected_base_name}_c_bat", grid_limit, hw_draft.get('battery', hw_draft))
                with st.expander("Generator", False): params['generator'] = render_generator_ui(f"{selected_base_name}_c_gen")

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
                           st.session_state.get('active_sim_mode') != scenario_mode or \
                           'active_sim_results' not in st.session_state

        if should_calculate:
            st.session_state['chart_colors'] = colors
            
            clean_base_df = baseline_df[['timestamp', 'consumption_kw']].copy() if 'timestamp' in baseline_df.columns else baseline_df.copy()
            
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
            else:
                df_1 = generate_solar_profile(clean_base_df, project_metadata, params.get('solar', {}))
                df_2 = simulate_battery_logic(df_1, grid_limit, params.get('battery', {}), res)
                calculated_df = simulate_generator_logic(df_2, grid_limit, params.get('generator', {}), res)

            st.session_state['active_sim_results'] = calculated_df
            st.session_state['active_sim_mode'] = scenario_mode
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
                p = params
                default_capex = 0.0
                if scenario_mode == "Battery (BESS) Only": 
                    default_capex = float(p.get('capacity_kwh', 0.0) * 400)
                elif scenario_mode == "Solar PV Only": 
                    default_capex = float(p.get('system_size_kwp', 0.0) * 800)
                elif scenario_mode == "Combined (All)": 
                    default_capex = float(p.get('battery', {}).get('capacity_kwh', 0.0) * 400) + float(p.get('solar', {}).get('system_size_kwp', 0.0) * 800)

                capex_input = col1.number_input("Purchase Price (€) [CAPEX]", value=default_capex, step=1000.0)
                opex_input = col2.number_input("Maintenance/Year (€) [OPEX]", value=float(default_capex * 0.02), step=100.0)
                financial_module = FinancialParams(capex=capex_input, opex_yearly=opex_input, lifespan_years=15)

        if st.button("Save Variant", type="primary", use_container_width=True):
            b_kwh, b_kw, s_kwp = 0.0, 0.0, 0.0
            if scenario_mode == "Battery (BESS) Only":
                b_kwh = params.get('capacity_kwh', 0.0)
                b_kw = params.get('max_kw', 0.0)
            elif scenario_mode == "Solar PV Only":
                s_kwp = params.get('system_size_kwp', 0.0)
            elif scenario_mode == "Combined (All)":
                b_kwh = params.get('battery', {}).get('capacity_kwh', 0.0)
                b_kw = params.get('battery', {}).get('max_kw', 0.0)
                s_kwp = params.get('solar', {}).get('system_size_kwp', 0.0)

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