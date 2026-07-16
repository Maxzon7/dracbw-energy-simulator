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
from classes.models import SubScenario, FinancialParams, Tariff
from logic.storage_manager import get_all_base_scenarios, get_base_scenario, add_sub_scenario

@st.fragment
def render_charts_fragment(calculated_df, plot_base_df, sim_grid_limit, res, scenario_mode, params, project_metadata, selected_base_name):
    # 1. Resolve colors dynamically from session state or fallbacks
    colors_to_use = {
        'raw': st.session_state.get('cp_raw', '#A9A9A9'),
        'opt': st.session_state.get('cp_opt', '#00CC96'),
        'soc': st.session_state.get('cp_soc', '#636EFA'),
        'act': st.session_state.get('cp_act', '#FFA15A'),
        'chg': st.session_state.get('cp_chg', '#AB63FA'),
        'sol': st.session_state.get('cp_sol', '#FFC107'),
        'gen': st.session_state.get('cp_gen', '#8B0000'),
        'lim': st.session_state.get('cp_lim', '#FF0000'),
        'sol_self': st.session_state.get('cp_self', '#4CAF50'),
        'sol_bat': st.session_state.get('cp_sol_bat', '#AB63FA'),
        'sol_exc': st.session_state.get('cp_exc', '#FF9800')
    }
    # Ensure this is synchronized for saving
    st.session_state['chart_colors'] = colors_to_use

    # 2. Render charts
    render_results_and_charts(
        calculated_df, plot_base_df, sim_grid_limit, res,
        scenario_mode, params, project_metadata, selected_base_name, False, colors_to_use, f"Report_{selected_base_name}"
    )
    
    # 3. Render color pickers
    st.write("") # spacing
    with st.expander("🎨 Chart Colors Customization (Farben anpassen)", expanded=False):
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        raw_c = col_c1.color_picker("Original Demand (Raw)", value=colors_to_use['raw'], key="cp_raw")
        opt_c = col_c2.color_picker("Optimized Grid Demand", value=colors_to_use['opt'], key="cp_opt")
        lim_c = col_c3.color_picker("Grid Limit Line", value=colors_to_use['lim'], key="cp_lim")
        soc_c = col_c4.color_picker("BESS SoC", value=colors_to_use['soc'], key="cp_soc")
        
        act_c = col_c1.color_picker("Battery Discharge", value=colors_to_use['act'], key="cp_act")
        chg_c = col_c2.color_picker("Battery Charge", value=colors_to_use['chg'], key="cp_chg")
        sol_c = col_c3.color_picker("Solar Yield (Main)", value=colors_to_use['sol'], key="cp_sol")
        gen_c = col_c4.color_picker("Generator Output", value=colors_to_use['gen'], key="cp_gen")
        
        self_c = col_c1.color_picker("Solar: Covering Demand", value=colors_to_use['sol_self'], key="cp_self")
        bat_c = col_c2.color_picker("Solar: Charging Battery", value=colors_to_use['sol_bat'], key="cp_sol_bat")
        exc_c = col_c3.color_picker("Solar: Excess (Export/Curtail)", value=colors_to_use['sol_exc'], key="cp_exc")

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

            # Expander removed to render under the chart instead
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
            clean_base_df = plot_base_df.copy()
            calculated_df = clean_base_df.copy()
            calculated_df['solar_gen_kw'] = 0.0
            calculated_df['battery_action_kw'] = 0.0
            calculated_df['battery_soc_kwh'] = 0.0
            calculated_df['generator_action_kw'] = 0.0
            calculated_df['generator_fuel_l'] = 0.0
            calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
            
            # Step 1: Grid Upgrade (resolves the target grid limit used in downstream simulations)
            target_sim_limit = sim_grid_limit
                
            # Step 2: Solar PV Integration
            if enable_solar and 'solar' in params:
                calculated_df = generate_solar_profile(calculated_df, project_metadata, params['solar'])
            else:
                calculated_df['solar_gen_kw'] = 0.0
                calculated_df['net_load_kw'] = calculated_df['consumption_kw']
                calculated_df['grid_feed_in_kw'] = 0.0
                
            # Step 3: Battery (BESS) Simulation
            if enable_battery and 'battery' in params:
                # Ensure battery shaving threshold does not exceed the target grid limit
                bat_params = params['battery'].copy()
                bat_params['shaving_threshold'] = min(float(bat_params.get('shaving_threshold', target_sim_limit)), target_sim_limit)
                calculated_df = simulate_battery_logic(calculated_df, target_sim_limit, bat_params, res)
            else:
                calculated_df['battery_action_kw'] = 0.0
                calculated_df['battery_soc_kwh'] = 0.0
                calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                
            # Step 4: Backup Generator Simulation
            if enable_generator and 'generator' in params:
                calculated_df = simulate_generator_logic(calculated_df, target_sim_limit, params['generator'], res)
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
        financials_active = st.session_state.get('enable_financials', False)
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
                    default_capex += float(params['grid'].get('data', {}).get('upgrade_capex', 0.0) or 0.0)

                capex_input = col1.number_input("Purchase Price (€) [CAPEX]", value=default_capex, step=1000.0)
                opex_input = col2.number_input("Maintenance/Year (€) [OPEX]", value=float(default_capex * 0.02), step=100.0)
                financial_module = FinancialParams(capex=capex_input, opex_yearly=opex_input, lifespan_years=15)

        if st.button("Save Variant", type="primary", use_container_width=True):
            b_kwh = params.get('battery', {}).get('b_cap', 0.0) if enable_battery and 'battery' in params else 0.0
            b_kw = params.get('battery', {}).get('b_pwr', 0.0) if enable_battery and 'battery' in params else 0.0
            s_kwp = params.get('solar', {}).get('installed_kwp', 0.0) if enable_solar and 'solar' in params else 0.0

            custom_t = None
            if enable_grid and 'grid' in params:
                grid_p = params['grid']
                t_data = grid_p['data']
                custom_t = Tariff(
                    name=grid_p['label'],
                    contracted_capacity_kw=grid_p['new_grid_limit_kw'],
                    fixed_costs_per_year=float(t_data.get('fixed_annual_connection_fee', 0.0) or 0.0) + float(t_data.get('fixed_annual_transport_fee', 0.0) or 0.0),
                    price_per_kw_peak=float(t_data.get('peak_capacity_fee_per_kw_month', 0.0) or 0.0),
                    price_per_kwh=float(t_data.get('energy_price_normal_per_kwh', 0.0) or 0.0),
                    is_custom=True
                )

            new_sub = SubScenario(
                name=scenario_name_input,
                battery_kwh=b_kwh, battery_kw=b_kw, solar_kwp=s_kwp,
                custom_tariff=custom_t,
                simulated_profile=calculated_df,
                financials=financial_module,
                tech_params=params
            )
            add_sub_scenario(selected_base_name, new_sub)
            st.success(f"Variant '{scenario_name_input}' successfully saved! Go to Tab 3 for comparison.")
            st.rerun()

    # RENDERING VISUALS (Rechte Seite) - Jetzt immer sichtbar!
    with col_chart:
        render_charts_fragment(
            calculated_df, plot_base_df, sim_grid_limit, res,
            scenario_mode, params, project_metadata, selected_base_name
        )

    # --- 3. SUB-SCENARIOS LISTING & RELOADING ---
    st.divider()
    st.write("### 3. Created Variants & Saved Sub-Scenarios")
    
    if not active_base.sub_scenarios:
        st.info("No sub-scenario variants created yet. Configure and save one above.")
    else:
        cols_sub = st.columns(3)
        for idx, sub in enumerate(active_base.sub_scenarios):
            with cols_sub[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"##### {sub.name}")
                    
                    details = []
                    if sub.solar_kwp > 0: details.append(f"Solar: {sub.solar_kwp:.1f} kWp")
                    if sub.battery_kwh > 0: details.append(f"BESS: {sub.battery_kwh:.1f} kWh / {sub.battery_kw:.1f} kW")
                    if sub.custom_tariff: details.append(f"Tariff: {sub.custom_tariff.name} ({sub.custom_tariff.contracted_capacity_kw:.1f} kW)")
                    else: details.append(f"Tariff: Baseline Limit ({grid_limit:.1f} kW)")
                    
                    st.write(", ".join(details))
                    
                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.button("↻ Reload", key=f"reload_sub_{sub.id}", use_container_width=True):
                        # 1. Resolve tech parameters (supporting both new tech_params format and legacy formats)
                        loaded_params = sub.tech_params if (hasattr(sub, 'tech_params') and sub.tech_params is not None) else {
                            'solar': {'installed_kwp': sub.solar_kwp, 'panel_count': int(sub.solar_kwp * 1000 / 420), 'panel_wp': 420} if sub.solar_kwp > 0 else {},
                            'battery': {'b_cap': sub.battery_kwh, 'b_pwr': sub.battery_kw, 'shaving_threshold': sub.custom_tariff.contracted_capacity_kw if sub.custom_tariff else grid_limit} if sub.battery_kwh > 0 else {},
                            'grid': {'new_grid_limit_kw': sub.custom_tariff.contracted_capacity_kw, 'label': sub.custom_tariff.name} if sub.custom_tariff else {}
                        }
                        
                        st.session_state['active_sim_params'] = loaded_params
                        st.session_state['active_sim_mode'] = {
                            'solar': sub.solar_kwp > 0,
                            'battery': sub.battery_kwh > 0,
                            'generator': 'generator_action_kw' in sub.simulated_profile.columns and sub.simulated_profile['generator_action_kw'].sum() > 0 if sub.simulated_profile is not None else False,
                            'grid': sub.custom_tariff is not None
                        }
                        
                        # 2. Restore simulated profile so we don't need immediate recalculation
                        st.session_state['active_sim_results'] = sub.simulated_profile.copy() if sub.simulated_profile is not None else None
                        st.session_state['last_calculated_project'] = selected_base_name
                        
                        # 3. Explicitly overwrite widget session state keys to bypass Streamlit's state cache
                        p_id = selected_base_name
                        if 'solar' in loaded_params and loaded_params['solar']:
                            s = loaded_params['solar']
                            st.session_state[f"sol_panels_{p_id}_sol"] = int(s.get('panel_count', 500))
                            st.session_state[f"sol_wp_{p_id}_sol"] = int(s.get('panel_wp', 420))
                            st.session_state[f"sol_pr_{p_id}_sol"] = int(s.get('performance_ratio', 85))
                            st.session_state[f"sol_therm_{p_id}_sol"] = bool(s.get('thermal_loss', True))
                            st.session_state[f"sol_az_{p_id}_sol"] = s.get('azimuth', "South (180°)")
                            st.session_state[f"sol_tilt_{p_id}_sol"] = s.get('tilt', "30°")
                            st.session_state[f"sol_panel_type_{p_id}_sol"] = s.get('panel_type', "Monocrystalline Silicon")
                            st.session_state[f"sol_ghi_source_{p_id}_sol"] = s.get('ghi_source', "Open-Meteo API")
                            st.session_state[f"sol_specific_yield_{p_id}_sol"] = float(s.get('specific_yield', 950.0))
                            st.session_state[f"sol_sun_hours_{p_id}_sol"] = float(s.get('annual_sunshine_hours', 1500.0))
                            st.session_state[f"sol_yield_factor_{p_id}_sol"] = float(s.get('yield_factor', 1.0))
                            st.session_state[f"sol_loss_inv_{p_id}_sol"] = float(s.get('loss_inverter', 3.0))
                            st.session_state[f"sol_loss_cab_{p_id}_sol"] = float(s.get('loss_cabling', 1.5))
                            st.session_state[f"sol_loss_soil_{p_id}_sol"] = float(s.get('loss_soiling', 1.0))
                            st.session_state[f"sol_loss_oth_{p_id}_sol"] = float(s.get('loss_other', 2.0))
                            st.session_state[f"sol_temp_coeff_{p_id}_sol"] = float(s.get('temp_coeff', 0.25))
                            st.session_state[f"sol_capex_{p_id}_sol"] = float(s.get('capex_per_kwp', 850.0))
                            st.session_state[f"sol_opex_{p_id}_sol"] = float(s.get('opex_pct', 1.0))
                            st.session_state[f"sol_deg_{p_id}_sol"] = float(s.get('degradation_pct', 0.5))
                            
                        if 'battery' in loaded_params and loaded_params['battery']:
                            b = loaded_params['battery']
                            num_bats = int(b.get('num_batteries', 10))
                            st.session_state[f"bat_num_{p_id}_bat"] = num_bats
                            st.session_state[f"bat_mod_cap_{p_id}_bat"] = float(b.get('cap_per_module', float(b.get('b_cap', 200.0)) / num_bats))
                            st.session_state[f"bat_pwr_{p_id}_bat"] = float(b.get('b_pwr', 100.0))
                            st.session_state[f"bat_thresh_{p_id}_bat"] = float(b.get('shaving_threshold', grid_limit))
                            st.session_state[f"bat_chg_lim_{p_id}_bat"] = int(b.get('charge_pwr_limit', 30))
                            st.session_state[f"bat_chg_start_{p_id}_bat"] = int(b.get('charge_start_hour', 22))
                            st.session_state[f"bat_chg_end_{p_id}_bat"] = int(b.get('charge_end_hour', 6))
                            st.session_state[f"bat_green_{p_id}_bat"] = bool(b.get('green_charging', False))
                            st.session_state[f"bat_eff_{p_id}_bat"] = int(b.get('efficiency', 92))
                            st.session_state[f"bat_soc_init_{p_id}_bat"] = int(b.get('initial_soc_pct', 50))
                            st.session_state[f"bat_type_{p_id}_bat"] = b.get('battery_type', "LFP (Lithium Iron Phosphate)")
                            st.session_state[f"bat_min_soc_{p_id}_bat"] = int(b.get('min_soc_pct', 10))
                            st.session_state[f"bat_max_soc_{p_id}_bat"] = int(b.get('max_soc_pct', 90))
                            st.session_state[f"bat_cycle_life_{p_id}_bat"] = int(b.get('cycle_life', 6000))
                            st.session_state[f"bat_temp_cap_coeff_{p_id}_bat"] = float(b.get('temp_cap_coeff', 0.5))
                            st.session_state[f"bat_capex_kwh_{p_id}_bat"] = float(b.get('capex_per_kwh', 400.0))
                            st.session_state[f"bat_capex_kw_{p_id}_bat"] = float(b.get('capex_per_kw', 150.0))
                            st.session_state[f"bat_opex_{p_id}_bat"] = float(b.get('opex_pct', 1.5))
                            st.session_state[f"bat_deg_{p_id}_bat"] = float(b.get('degradation_pct', 1.5))
                            st.session_state[f"bat_rep_yr_{p_id}_bat"] = int(b.get('replacement_year', 10))
                            st.session_state[f"bat_rep_pct_{p_id}_bat"] = float(b.get('replacement_pct', 100.0))
                            
                        if 'generator' in loaded_params and loaded_params['generator']:
                            g = loaded_params['generator']
                            st.session_state[f"gen_pwr_{p_id}_gen"] = float(g.get('gen_pwr', 250.0))
                            st.session_state[f"gen_fuel_{p_id}_gen"] = float(g.get('fuel_l_per_kwh', 0.28))
                            st.session_state[f"gen_capex_{p_id}_gen"] = float(g.get('capex_per_year', 0.0))
                            st.session_state[f"gen_opex_hr_{p_id}_gen"] = float(g.get('opex_per_hour', 0.0))
                            
                        st.success(f"Config and diagrams for '{sub.name}' successfully restored!")
                        st.rerun()
                        
                    if c_btn2.button("Delete", key=f"del_sub_{sub.id}", use_container_width=True):
                        active_base.sub_scenarios = [s for s in active_base.sub_scenarios if s.id != sub.id]
                        st.success(f"Deleted variant '{sub.name}'")
                        st.rerun()