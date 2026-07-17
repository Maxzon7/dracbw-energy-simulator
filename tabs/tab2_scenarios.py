# tabs/tab2_scenarios.py
import streamlit as st
import pandas as pd

# Sub-components imports
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.generator_ui import render_generator_ui
from tabs.tab2_components.grid_upgrade_ui import render_grid_upgrade_ui
from tabs.tab2_components.scenario_charts_fragment import render_charts_fragment
from tabs.tab2_components.scenario_solver import calculate_scenario
from tabs.tab2_components.variant_manager import render_save_variant_section, render_saved_variants_section

from logic.storage_manager import get_all_base_scenarios, get_base_scenario

def render_tab2_scenarios():
    st.header("Scenario Simulation (Hardware Integration)")

    bases = get_all_base_scenarios()
    if not bases:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return

    base_names = [b.name for b in bases]
    selected_base_name = st.selectbox("### 1. Select Project (Baseline)", base_names)
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
        enable_solar = st.checkbox("Integrate Solar PV", value=default_solar)
        enable_battery = st.checkbox("Integrate Battery (BESS)", value=default_battery)
        enable_generator = st.checkbox("Integrate Backup Generator", value=default_generator)
        enable_grid = st.checkbox("Change Grid Tariff / Upgrade Connection", value=default_grid)

        # Dynamic contract mode selections outside the form for reactive updates
        sub_contract_mode = "Generic AC Connection Tier"
        sub_preset_label = "AC4 (3x80A - 55 kW)"
        sub_preset_data = {}
        sim_grid_limit = grid_limit

        if enable_grid:
            st.write("---")
            st.write("#### Connection Change Settings")
            sub_contract_mode = st.selectbox(
                "New Connection / Contract Mode:",
                [
                    "Generic AC Connection Tier",
                    "Real Contract Preset", 
                    "Generic Grid Limit (No Contract)", 
                    "No Contract (Consumption Only)"
                ],
                index=0,
                key=f"sub_grid_contract_mode_sel_{selected_base_name}"
            )
            
            if sub_contract_mode == "Generic AC Connection Tier":
                from tabs.tab1_components.financial_ui import get_generic_ac_presets
                ac_presets = get_generic_ac_presets()
                ac_keys = list(ac_presets.keys())
                
                # Fetch default if we reloaded a variant
                reloaded_val = st.session_state.get('active_sim_params', {}).get('grid', {}).get('label')
                default_idx = ac_keys.index(reloaded_val) if reloaded_val in ac_keys else 3 # AC4
                
                selected_ac_key = st.selectbox(
                    "Select New Generic AC Tier:", 
                    ac_keys, 
                    index=default_idx,
                    key=f"sub_ac_tier_sel_{selected_base_name}"
                )
                sub_preset_label = selected_ac_key
                sub_preset_data = ac_presets[selected_ac_key]
                sim_grid_limit = sub_preset_data.get("contracted_capacity_kw", grid_limit)
            elif sub_contract_mode == "Real Contract Preset":
                from tabs.tab1_components.financial_ui import render_preset_selector
                sub_preset_label, sub_preset_data = render_preset_selector()
                sim_grid_limit = sub_preset_data.get("contracted_capacity_kw", grid_limit) if sub_preset_data else grid_limit
            elif sub_contract_mode == "Generic Grid Limit (No Contract)":
                sub_preset_label = "Generic Limit"
                reloaded_val = st.session_state.get('active_sim_params', {}).get('grid', {}).get('new_grid_limit_kw', grid_limit)
                sub_limit = st.number_input(
                    "Grid Capacity Limit (kW)", 
                    min_value=5.0, value=float(reloaded_val), step=5.0,
                    key=f"sub_limit_val_{selected_base_name}"
                )
                sub_preset_data = {
                    "contracted_capacity_kw": sub_limit,
                    "fixed_annual_connection_fee": 0.0,
                    "fixed_annual_transport_fee": 0.0,
                    "contracted_capacity_fee_per_kw_year": 0.0,
                    "peak_capacity_fee_per_kw_month": 0.0,
                    "energy_price_normal_per_kwh": 0.20,
                    "energy_price_laag_per_kwh": 0.15,
                    "tariff_mode": "Generic Limit"
                }
                sim_grid_limit = sub_limit
            elif sub_contract_mode == "No Contract (Consumption Only)":
                sub_preset_label = "None (Consumption Only)"
                sub_preset_data = {
                    "contracted_capacity_kw": 0.0,
                    "fixed_annual_connection_fee": 0.0,
                    "fixed_annual_transport_fee": 0.0,
                    "contracted_capacity_fee_per_kw_year": 0.0,
                    "peak_capacity_fee_per_kw_month": 0.0,
                    "energy_price_normal_per_kwh": 0.0,
                    "energy_price_laag_per_kwh": 0.0,
                    "tariff_mode": "None (Consumption Only)"
                }
                sim_grid_limit = 0.0

        # Calculation Resolution Toggle
        st.write("---")
        st.write("#### Calculation Resolution")
        calc_res = st.radio(
            "Select Resolution:",
            ["Hourly (Fast / Schnell)", "15-Minute (High Accuracy / Genau)"],
            index=0,
            key=f"calc_res_sel_{selected_base_name}",
            help="Hourly resolution runs 4x faster. Use 15-Minute resolution for final verification."
        )
        use_15min = "15-Minute" in calc_res
        
        # Build dynamic scenario mode label
        active_mode_list = []
        if enable_solar: active_mode_list.append("Solar")
        if enable_battery: active_mode_list.append("BESS")
        if enable_generator: active_mode_list.append("Generator")
        if enable_grid: active_mode_list.append(sub_preset_label)
        
        scenario_mode = " + ".join(active_mode_list) if active_mode_list else "None"
        active_sim_mode_dict = {
            'solar': enable_solar,
            'battery': enable_battery,
            'generator': enable_generator,
            'grid': enable_grid,
            'res_15min': use_15min
        }

        with st.form("scenario_tech_form"):
            hw_draft = st.session_state.get('active_sim_params', {})
            params = {}
            
            if enable_solar:
                solar_draft = hw_draft.get('solar', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure Solar PV", True): 
                    params['solar'] = render_solar_ui(selected_base_name + "_sol", solar_draft)
            if enable_battery:
                battery_draft = hw_draft.get('battery', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure BESS (Battery)", True): 
                    params['battery'] = render_battery_ui(selected_base_name + "_bat", sim_grid_limit, battery_draft)
            if enable_generator:
                generator_draft = hw_draft.get('generator', hw_draft) if isinstance(hw_draft, dict) else {}
                with st.expander("Configure Generator", True): 
                    params['generator'] = render_generator_ui(selected_base_name + "_gen", generator_draft)
            if enable_grid:
                with st.expander("Configure Tariff Change Detail", True):
                    st.metric("Grid Capacity Limit", f"{sim_grid_limit:.1f} kW")
                    params['grid'] = {
                        "mode": sub_contract_mode,
                        "label": sub_preset_label,
                        "data": sub_preset_data,
                        "new_grid_limit_kw": sim_grid_limit
                    }

            run_sim = st.form_submit_button("Run / Update Simulation", type="primary", use_container_width=True)

        # Prepare the baseline dataframe matching the selected resolution
        plot_base_df = baseline_df[['timestamp', 'consumption_kw']].copy() if 'timestamp' in baseline_df.columns else baseline_df.copy()
        if 'timestamp' in plot_base_df.columns:
            plot_base_df['timestamp'] = pd.to_datetime(plot_base_df['timestamp'])
            
        if not use_15min:
            if 'timestamp' in plot_base_df.columns:
                plot_base_df = plot_base_df.set_index('timestamp').resample('h').max().reset_index()
            res = 60
        else:
            res = 15

        # Decide whether to run calculations or use cached values
        should_calculate = run_sim or \
                           st.session_state.get('last_calculated_project') != selected_base_name or \
                           st.session_state.get('active_sim_mode') != active_sim_mode_dict or \
                           'active_sim_results' not in st.session_state

        if should_calculate:
            with st.spinner("Calculating simulation..."):
                calculated_df = calculate_scenario(
                    plot_base_df=plot_base_df,
                    sim_grid_limit=sim_grid_limit,
                    enable_solar=enable_solar,
                    enable_battery=enable_battery,
                    enable_generator=enable_generator,
                    params=params,
                    project_metadata=project_metadata,
                    res=res
                )
                st.session_state['active_sim_results'] = calculated_df
                st.session_state['active_sim_mode'] = active_sim_mode_dict
                st.session_state['active_sim_params'] = params
                st.session_state['last_calculated_project'] = selected_base_name
        else:
            calculated_df = st.session_state['active_sim_results']
            params = st.session_state['active_sim_params']

        st.divider()
        render_save_variant_section(
            scenario_mode=scenario_mode,
            enable_solar=enable_solar,
            enable_battery=enable_battery,
            enable_grid=enable_grid,
            params=params,
            calculated_df=calculated_df,
            selected_base_name=selected_base_name
        )

    # RENDERING VISUALS (Rechte Seite) - Jetzt immer sichtbar!
    with col_chart:
        render_charts_fragment(
            calculated_df=calculated_df,
            plot_base_df=plot_base_df,
            sim_grid_limit=sim_grid_limit,
            res=res,
            scenario_mode=scenario_mode,
            params=params,
            project_metadata=project_metadata,
            selected_base_name=selected_base_name
        )

    # --- 3. SUB-SCENARIOS LISTING & RELOADING ---
    render_saved_variants_section(
        active_base=active_base,
        selected_base_name=selected_base_name,
        grid_limit=grid_limit
    )