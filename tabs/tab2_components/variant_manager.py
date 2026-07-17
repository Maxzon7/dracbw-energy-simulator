import streamlit as st
import pandas as pd
from classes.models import SubScenario, FinancialParams, Tariff
from logic.storage_manager import add_sub_scenario

def render_save_variant_section(
    scenario_mode: str,
    enable_solar: bool,
    enable_battery: bool,
    enable_grid: bool,
    params: dict,
    calculated_df: pd.DataFrame,
    selected_base_name: str
):
    """Renders the section to configure and save a simulated scenario as a variant."""
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

def render_saved_variants_section(active_base, selected_base_name: str, grid_limit: float):
    """Renders the dashboard cards for all saved sub-scenarios / variants."""
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
