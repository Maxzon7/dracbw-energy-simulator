# demo_mode/demo_main.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
from demo_mode.demo_components.location_ui import render_demo_location_ui
from demo_mode.demo_components.solar_ui import render_demo_solar_ui
from demo_mode.demo_components.results_viewer import render_demo_results
from tabs.tab2_components.solar_logic import generate_solar_profile
from logic.energy_logic import simulate_battery_logic, simulate_generator_logic

def merge_demo_translations():
    """Dynamically merges the demo-mode specific translations into the global session cache."""
    if 'translations' in st.session_state and 'demo_title' not in st.session_state['t']:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, "config", "demo_translations.json")
            with open(json_path, "r", encoding="utf-8") as file:
                demo_data = json.load(file)
            
            # Merge demo translations for all languages
            for lang, keys in demo_data.items():
                if lang in st.session_state['translations']:
                    st.session_state['translations'][lang].update(keys)
        except Exception as e:
            st.error(f"Error loading demo translations: {e}")

def generate_hourly_consumption(
    monthly_consumption: float, 
    days_per_week: int, 
    hours_per_day: int, 
    base_load_pct: int = 15,
    noise_percentage: float = 5.0
) -> pd.DataFrame:
    """Generates an hourly baseline load profile for a full year (2022)."""
    timestamps = pd.date_range(start='2022-01-01', end='2022-12-31 23:00:00', freq='h')
    df = pd.DataFrame({'timestamp': timestamps})
    
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    
    base_factor = base_load_pct / 100.0
    profile = np.full(len(df), base_factor)
    
    start_hour = 8
    end_hour = start_hour + hours_per_day
    
    if end_hour > 24:
        op_mask = (df['hour'] >= start_hour) | (df['hour'] < (end_hour % 24))
    else:
        op_mask = (df['hour'] >= start_hour) & (df['hour'] < end_hour)
        
    if hours_per_day == 24:
        op_mask = pd.Series([True] * len(df))
        
    working_days_mask = df['dayofweek'] < days_per_week
    active_mask = op_mask & working_days_mask
    profile[active_mask] = 1.0
    
    # Add noise
    std_dev = noise_percentage / 100.0
    noise = np.random.normal(1.0, std_dev, len(profile))
    profile = profile * noise
    profile = np.clip(profile, a_min=base_factor * 0.5, a_max=None)
    
    # Scale to target
    annual_target_kwh = monthly_consumption * 12.0
    current_annual_energy = np.sum(profile)
    scaling_factor = annual_target_kwh / current_annual_energy if current_annual_energy > 0 else 1.0
    
    df['consumption_kw'] = profile * scaling_factor
    df = df.drop(columns=['hour', 'dayofweek'])
    return df

# UI Input Sub-sections for modular multi-layout rendering
def render_location_consumption_inputs(key_suffix: str) -> tuple:
    """Renders location and baseline consumption forms."""
    t = st.session_state.get('t', {})
    
    # 1. Location Settings
    with st.container(border=True):
        loc_params = render_demo_location_ui(key_suffix)
        
    st.write("<br>", unsafe_allow_html=True)
    
    # 2. Consumption Settings
    with st.container(border=True):
        st.write(f"### {t.get('demo_cons_title', 'Consumption & Grid')}")
        has_consumption = st.checkbox(
            t.get('demo_cons_checkbox', 'Add Baseline Consumption Profile'), 
            value=st.session_state.get(f"demo_has_consumption{key_suffix}", False), 
            key=f"demo_has_consumption_check{key_suffix}"
        )
        st.session_state[f"demo_has_consumption{key_suffix}"] = has_consumption
        
        if has_consumption:
            monthly_cons = st.number_input(
                t.get('demo_cons_monthly', 'Avg. Monthly Consumption (kWh)'), 
                min_value=100, value=50000, step=1000, 
                key=f"demo_cons_monthly_input{key_suffix}"
            )
            col_cons1, col_cons2 = st.columns(2)
            work_days = col_cons1.slider(t.get('demo_cons_workdays', 'Working Days / Week'), 1, 7, 5, key=f"demo_cons_workdays_slider{key_suffix}")
            work_hours = col_cons2.slider(t.get('demo_cons_hours', 'Working Hours / Day'), 1, 24, 12, key=f"demo_cons_hours_slider{key_suffix}")
            base_load = st.slider(t.get('demo_cons_baseload', 'Base Load Percentage (%)'), 0, 100, 15, key=f"demo_cons_baseload_slider{key_suffix}")
            
            grid_limit = st.number_input(t.get('demo_grid_limit_demo', 'Grid Connection Limit (kW)'), min_value=5.0, value=120.0, step=5.0, key=f"demo_grid_limit_input{key_suffix}")
        else:
            monthly_cons, work_days, work_hours, base_load = 0.0, 5, 12, 15
            grid_limit = 0.0
            
    return loc_params, has_consumption, monthly_cons, work_days, work_hours, base_load, grid_limit

def render_solar_battery_inputs(key_suffix: str, has_consumption: bool, grid_limit: float) -> tuple:
    """Renders Solar PV and BESS battery configurations."""
    t = st.session_state.get('t', {})
    
    # 3. Solar PV Setup
    with st.container(border=True):
        solar_params_dict = render_demo_solar_ui(key_suffix)
        installed_kwp = solar_params_dict.get("installed_kwp", 0.0)
        has_solar = installed_kwp > 0.0
        sol_params = solar_params_dict

    st.write("<br>", unsafe_allow_html=True)
    
    # 4. Battery Storage
    with st.container(border=True):
        st.write(f"### {t.get('demo_bat_title', 'Battery Storage (BESS)')}")
        if has_consumption:
            has_battery = st.checkbox(
                t.get('demo_bat_checkbox', 'Integrate Battery (BESS)'), 
                value=st.session_state.get(f"demo_has_battery{key_suffix}", False), 
                key=f"demo_has_battery_check{key_suffix}"
            )
            st.session_state[f"demo_has_battery{key_suffix}"] = has_battery
            if has_battery:
                col_b1, col_b2 = st.columns(2)
                num_batteries = col_b1.number_input(t.get('demo_bat_num', 'Number of Batteries'), min_value=1, value=10, step=1, key=f"demo_bat_num{key_suffix}")
                cap_per_module = col_b2.number_input(t.get('demo_bat_mod_cap', 'Capacity per Module (kWh)'), min_value=1.0, value=20.0, step=1.0, key=f"demo_bat_mod_cap{key_suffix}")
                b_cap = float(num_batteries * cap_per_module)
                st.success(f"**{t.get('demo_bat_capacity', 'Total Capacity: ')}{b_cap:,.1f} kWh**")
                
                b_pwr = st.number_input(t.get('demo_bat_inv_pwr', 'Max Inverter Power (kW)'), min_value=5.0, value=100.0, step=5.0, key=f"demo_bat_inv_pwr_input{key_suffix}")
                chg_pwr = st.slider(t.get('demo_bat_chg_spd', 'Max Recharge Speed (kW)'), 5, 200, 30, key=f"demo_bat_chg_spd_slider{key_suffix}")
                
                with st.expander(t.get('demo_bat_advanced', 'Advanced Battery Parameters'), expanded=False):
                    b_type = st.selectbox(
                        t.get('demo_bat_type', 'Battery Type / Chemistry'),
                        ["LFP (Lithium Iron Phosphate)", "NMC (Lithium Nickel Manganese Cobalt)", "Lead-Acid", "Flow Battery"],
                        index=0,
                        key=f"demo_bat_type{key_suffix}"
                    )
                    min_soc_pct = st.slider(t.get('demo_bat_min_soc', 'Min State of Charge (SoC %)'), 0, 50, 10, key=f"demo_bat_min_soc{key_suffix}")
                    max_soc_pct = st.slider(t.get('demo_bat_max_soc', 'Max State of Charge (SoC %)'), 50, 100, 90, key=f"demo_bat_max_soc{key_suffix}")
                    initial_soc_pct = st.slider(t.get('demo_bat_init_soc', 'Initial State of Charge (%)'), 0, 100, 50, key=f"demo_bat_init_soc{key_suffix}")
                    
                    cycle_life = st.number_input(
                        t.get('demo_bat_cycle_life', 'Cycle Life (Expected total cycles)'),
                        min_value=500, max_value=15000, value=6000, step=500,
                        key=f"demo_bat_cycle_life{key_suffix}"
                    )
                    temp_cap_coeff = st.slider(
                        t.get('demo_bat_temp_penalty', 'Temperature Capacity Penalty (%/°C deviation)'),
                        0.0, 2.0, 0.5, step=0.1,
                        help=t.get('demo_bat_temp_penalty_help', 'Capacity loss coefficient per °C deviation from 15°C - 35°C range.'),
                        key=f"demo_bat_temp_cap_coeff{key_suffix}"
                    )
                    efficiency = st.slider(t.get('demo_bat_efficiency', 'Round-Trip Efficiency (%)'), 70, 98, 92, key=f"demo_bat_eff{key_suffix}")
                
                bat_params = {
                    "b_cap": b_cap,
                    "b_pwr": b_pwr,
                    "shaving_threshold": grid_limit,
                    "charge_pwr_limit": chg_pwr,
                    "charge_start_hour": 22,
                    "charge_end_hour": 6,
                    "green_charging": has_solar,
                    "efficiency": float(efficiency),
                    "initial_soc_pct": float(initial_soc_pct),
                    "min_soc_pct": float(min_soc_pct),
                    "max_soc_pct": float(max_soc_pct),
                    "num_batteries": num_batteries,
                    "cap_per_module": cap_per_module,
                    "battery_type": b_type,
                    "cycle_life": cycle_life,
                    "temp_cap_coeff": temp_cap_coeff
                }
            else:
                bat_params = {}
        else:
            st.caption(t.get('demo_res_solar_info', "No battery integrated. Check 'Integrate Battery (BESS)' on the left to simulate storage action."))
            has_battery = False
            bat_params = {}
            
    return sol_params, has_battery, bat_params

def render_generator_financials_inputs(key_suffix: str, has_consumption: bool, grid_limit: float, has_solar: bool) -> tuple:
    """Renders back-up generator and billing financials configurations."""
    t = st.session_state.get('t', {})
    
    # 5. Generator Setup
    with st.container(border=True):
        st.write(f"### {t.get('demo_gen_title', 'Backup Generator')}")
        if has_consumption:
            has_generator = st.checkbox(
                t.get('demo_gen_checkbox', 'Integrate Backup Generator'), 
                value=st.session_state.get(f"demo_has_generator{key_suffix}", False), 
                key=f"demo_has_generator_check{key_suffix}"
            )
            st.session_state[f"demo_has_generator{key_suffix}"] = has_generator
            if has_generator:
                gen_pwr = st.number_input(t.get('demo_gen_power', 'Generator Power (kW)'), min_value=5.0, value=100.0, step=5.0, key=f"demo_gen_power_input{key_suffix}")
                fuel_rate = st.number_input(t.get('demo_gen_fuel_rate', 'Fuel Consumption Rate (L/kWh)'), min_value=0.05, max_value=2.0, value=0.28, step=0.01, key=f"demo_gen_fuel_rate_input{key_suffix}")
                gen_params = {
                    "gen_pwr": gen_pwr,
                    "fuel_l_per_kwh": fuel_rate
                }
            else:
                gen_params = {}
        else:
            st.caption(t.get('demo_gen_enable_caption', "Enable 'Baseline Consumption Profile' to add generator peak shaving."))
            has_generator = False
            gen_params = {}

    st.write("<br>", unsafe_allow_html=True)
    
    # 6. Financials & Tariff Setup
    with st.container(border=True):
        st.write(f"### {t.get('demo_fin_title', '💰 Financials & Grid Tariff Setup')}")
        has_financials = st.checkbox(
            t.get('demo_fin_checkbox', 'Simulate Tariff Billing'), 
            value=st.session_state.get(f"demo_has_financials{key_suffix}", True), 
            key=f"demo_has_fin{key_suffix}", 
            help=t.get('demo_fin_checkbox_help', 'Enable to calculate monthly grid bills and savings using a multi-pillar tariff structure.')
        )
        st.session_state[f"demo_has_financials{key_suffix}"] = has_financials
        if has_financials:
            st.caption(t.get('demo_fin_caption', 'All values are in Euros (€). Default parameters can be customized below.'))
            
            base_fee = st.number_input(t.get('demo_fin_p1', 'Pillar 1: Fixed Service Charge (€/Month)'), value=100.0, step=10.0, key=f"demo_fin_base{key_suffix}", help=t.get('demo_fin_p1_help', 'Fixed connection/service fee billed monthly regardless of energy use.'))
            contracted_kw = st.number_input(t.get('demo_fin_p2_limit', 'Pillar 2: Contracted Capacity Limit (kW)'), value=100.0, step=10.0, key=f"demo_fin_contracted_kw{key_suffix}", help=t.get('demo_fin_p2_limit_help', 'Maximum capacity limit authorized by grid contract.'))
            contract_price = st.number_input(t.get('demo_fin_p2_price', 'Pillar 2: Contracted Capacity Price (€/kW/Month)'), value=5.0, step=0.5, key=f"demo_fin_contract_price{key_suffix}", help=t.get('demo_fin_p2_price_help', 'Monthly fee per kW of contracted capacity.'))
            peak_penalty = st.number_input(t.get('demo_fin_p3_peak', 'Pillar 3: Measured Peak Charge (€/kW/Month)'), value=2.0, step=0.5, key=f"demo_fin_peak_penalty{key_suffix}", help=t.get('demo_fin_p3_peak_help', 'Monthly fee per kW of measured peak load registered during Peak hours.'))
            excess_price = st.number_input(t.get('demo_fin_p4_excess', 'Pillar 4: Excess Capacity Penalty (€/kW/Month)'), value=10.0, step=1.0, key=f"demo_fin_excess{key_suffix}", help=t.get('demo_fin_p4_excess_help', 'Penalty fee per kW for peak load exceeding the contracted limit.'))
            
            st.markdown(f"**{t.get('demo_fin_tou', 'Time-of-Use Active Energy Prices & Active Hours')}**")
            col_t1, col_t2, col_t3 = st.columns(3)
            alta_pr = col_t1.number_input(t.get('demo_fin_peak_pr', 'Peak Price (€/kWh)'), value=0.18, format="%.4f", key=f"demo_fin_alta{key_suffix}", help=t.get('demo_fin_peak_pr_help', 'Energy price per kWh during high-demand/Peak hours.'))
            alta_start = col_t2.number_input(t.get('demo_fin_peak_st', 'Peak Start Hour'), min_value=0, max_value=23, value=18, step=1, key=f"demo_fin_alta_st{key_suffix}", help=t.get('demo_fin_peak_st_help', 'Start hour (0-23) for Peak pricing.'))
            alta_end = col_t3.number_input(t.get('demo_fin_peak_ed', 'Peak End Hour'), min_value=0, max_value=23, value=23, step=1, key=f"demo_fin_alta_ed{key_suffix}", help=t.get('demo_fin_peak_ed_help', 'End hour (0-23) for Peak pricing.'))
            
            col_t4, col_t5, col_t6 = st.columns(3)
            baja_pr = col_t4.number_input(t.get('demo_fin_offpeak_pr', 'Off-Peak Price (€/kWh)'), value=0.10, format="%.4f", key=f"demo_fin_baja{key_suffix}", help=t.get('demo_fin_offpeak_pr_help', 'Off-Peak price per kWh.'))
            baja_start = col_t5.number_input(t.get('demo_fin_offpeak_st', 'Off-Peak Start Hour'), min_value=0, max_value=23, value=23, step=1, key=f"demo_fin_baja_st{key_suffix}", help=t.get('demo_fin_offpeak_st_help', 'Start hour (0-23) for Off-Peak pricing.'))
            baja_end = col_t6.number_input(t.get('demo_fin_offpeak_ed', 'Off-Peak End Hour'), min_value=0, max_value=23, value=5, step=1, key=f"demo_fin_offpeak_ed{key_suffix}", help=t.get('demo_fin_offpeak_ed_help', 'End hour (0-23) for Off-Peak pricing.'))
            
            col_t7 = st.columns(1)[0]
            resto_pr = col_t7.number_input(t.get('demo_fin_midpeak_pr', 'Mid-Peak Price (€/kWh)'), value=0.14, format="%.4f", key=f"demo_fin_resto{key_suffix}", help=t.get('demo_fin_midpeak_pr_help', 'Energy rate for all remaining hours outside Peak and Off-Peak windows.'))
            
            st.markdown(f"**{t.get('demo_fin_taxes', 'Taxes & Duties Configuration')}**")
            st.caption(t.get('demo_fin_taxes_caption', 'Configure VAT and other grid surcharges.'))
            
            default_prov_taxes = [{"Tax Name": "VAT", "Rate (%)": 21.0, "Compound": False}]
            prov_df = pd.DataFrame(default_prov_taxes)
            edited_prov = st.data_editor(
                prov_df, 
                num_rows="dynamic", 
                column_config={
                    "Tax Name": st.column_config.TextColumn("Tax Name"),
                    "Rate (%)": st.column_config.NumberColumn("Rate (%)", min_value=0.0, max_value=100.0, format="%.2f%%"),
                    "Compound": st.column_config.CheckboxColumn("Compound?")
                },
                key=f"demo_fin_prov_editor{key_suffix}"
            )
            prov_taxes = edited_prov.to_dict('records')
            
            st.markdown(f"**{t.get('demo_fin_adj', 'Custom Adjustments (Surcharges & Credits)')}**")
            
            default_adjustments = [
                {"Adjustment Name": "Municipal Lighting Fee", "Amount (€)": 150.0, "Is Pre-tax": False},
                {"Adjustment Name": "Stabilization Credit", "Amount (€)": -500.0, "Is Pre-tax": False}
            ]
            adj_df = pd.DataFrame(default_adjustments)
            edited_adj = st.data_editor(
                adj_df, 
                num_rows="dynamic", 
                column_config={
                    "Adjustment Name": st.column_config.TextColumn("Adjustment Name"),
                    "Amount (€)": st.column_config.NumberColumn("Amount (€)", format="€%.2f"),
                    "Is Pre-tax": st.column_config.CheckboxColumn("Pre-tax?")
                },
                key=f"demo_fin_adj_editor{key_suffix}"
            )
            custom_adjustments = []
            for a in edited_adj.to_dict('records'):
                custom_adjustments.append({
                    "Charge Name": a.get("Adjustment Name", a.get("Charge Name", "")),
                    "Amount (€)": float(a.get("Amount (€)", 0.0) or 0.0),
                    "Is Pre-tax": bool(a.get("Is Pre-tax", False))
                })
            
            monthly_schedule = {}
            for m in range(1, 13):
                monthly_schedule[str(m)] = {
                    "base_fee": base_fee,
                    "contracted_capacity_kw": contracted_kw,
                    "contracted_capacity_price": contract_price,
                    "peak_penalty_price": peak_penalty,
                    "excess_penalty_price": excess_price,
                    "enable_tou": True,
                    "alta": {"price": alta_pr, "start_hour": alta_start, "end_hour": alta_end},
                    "baja": {"price": baja_pr, "start_hour": baja_start, "end_hour": baja_end},
                    "resto": {"price": resto_pr},
                    "tax_pct": 0.0,
                    "provincial_taxes": prov_taxes,
                    "custom_adjustments": custom_adjustments
                }
            fin_params = {"monthly_tariff_schedule": monthly_schedule}
        else:
            fin_params = {}
            
    return has_generator, gen_params, has_financials, fin_params

def render_results_section(
    calc_button: bool,
    loc_params: dict,
    has_consumption: bool,
    monthly_cons: float,
    work_days: int,
    work_hours: int,
    base_load: float,
    grid_limit: float,
    sol_params: dict,
    has_battery: bool,
    bat_params: dict,
    has_generator: bool,
    gen_params: dict,
    has_financials: bool,
    fin_params: dict
):
    """Handles running simulations and rendering results columns in real-time."""
    t = st.session_state.get('t', {})
    
    if calc_button:
        with st.spinner("Simulating scenario timeline..."):
            try:
                # 1. Generate Baseline consumption (hourly frequency)
                if has_consumption:
                    baseline_df = generate_hourly_consumption(
                        monthly_consumption=monthly_cons,
                        days_per_week=work_days,
                        hours_per_day=work_hours,
                        base_load_pct=base_load,
                        noise_percentage=5.0
                    )
                else:
                    timestamps = pd.date_range(start='2022-01-01', end='2022-12-31 23:00:00', freq='h')
                    baseline_df = pd.DataFrame({
                        'timestamp': timestamps,
                        'consumption_kw': 0.0
                    })

                # Setup metadata
                project_metadata = {
                    'latitude': loc_params['latitude'],
                    'longitude': loc_params['longitude'],
                    'country': loc_params['country'],
                    'strict_zero_export': False
                }

                # Running profile copy
                calculated_df = baseline_df.copy()
                calculated_df['solar_gen_kw'] = 0.0
                calculated_df['battery_action_kw'] = 0.0
                calculated_df['battery_soc_kwh'] = 0.0
                calculated_df['generator_action_kw'] = 0.0
                calculated_df['generator_fuel_l'] = 0.0
                calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']

                # 2. Simulate Solar PV
                installed_kwp = sol_params.get("installed_kwp", 0.0)
                has_solar = installed_kwp > 0.0
                if has_solar:
                    calculated_df = generate_solar_profile(calculated_df, project_metadata, sol_params)
                else:
                    calculated_df['solar_gen_kw'] = 0.0
                    calculated_df['net_load_kw'] = calculated_df['consumption_kw']
                    calculated_df['grid_feed_in_kw'] = 0.0

                # 3. Simulate Battery (BESS)
                if has_battery:
                    calculated_df = simulate_battery_logic(calculated_df, grid_limit, bat_params, res=60)
                else:
                    calculated_df['battery_action_kw'] = 0.0
                    calculated_df['battery_soc_kwh'] = 0.0
                    calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']

                # 4. Simulate Generator
                if has_generator:
                    calculated_df = simulate_generator_logic(calculated_df, grid_limit, gen_params, res=60)
                else:
                    calculated_df['generator_action_kw'] = 0.0
                    calculated_df['generator_fuel_l'] = 0.0
                    
                if 'final_grid_load_kw' not in calculated_df.columns:
                    calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']

                # Persist results in session state
                st.session_state["demo_results"] = calculated_df
                st.session_state["demo_installed_kwp"] = installed_kwp
                st.session_state["demo_country_val"] = loc_params["country"]
                st.session_state["demo_has_consumption_saved"] = has_consumption
                st.session_state["demo_grid_limit"] = grid_limit
                st.session_state["demo_has_battery_saved"] = has_battery
                st.session_state["demo_has_generator_saved"] = has_generator
                st.session_state["demo_bat_params"] = bat_params
                st.session_state["demo_sol_params"] = sol_params
                st.session_state["demo_has_financials_saved"] = has_financials
                st.session_state["demo_fin_params"] = fin_params
                
                st.success(t.get('demo_calc_success', "Scenario calculated successfully!"))
            except Exception as sim_err:
                st.error(f"{t.get('demo_calc_fail', 'Simulation failed: ')}{sim_err}")

    # Render results if available
    if st.session_state["demo_results"] is not None:
        render_demo_results(
            results=st.session_state["demo_results"],
            installed_kwp=st.session_state["demo_installed_kwp"],
            country=st.session_state["demo_country_val"],
            has_consumption=st.session_state.get("demo_has_consumption_saved", False),
            grid_limit=st.session_state["demo_grid_limit"],
            has_battery=st.session_state.get("demo_has_battery_saved", False),
            has_generator=st.session_state.get("demo_has_generator_saved", False),
            has_financials=st.session_state.get("demo_has_financials_saved", False),
            fin_params=st.session_state.get("demo_fin_params", None)
        )
    else:
        # Placeholder display
        st.info(t.get('demo_placeholder_info', "Configure your location and active technologies on the left, then click **Calculate Scenario** to run the simulation."))
        st.markdown(
            f"""
            <div style="background-color:rgba(0, 204, 150, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(0, 204, 150, 0.2); margin-top:20px;">
                <h4 style="color:#00CC96; margin-top:0;">{t.get('demo_sandbox_title', 'Instant Prototyping Sandbox')}</h4>
                <p style="margin: 0 0 10px 0;">{t.get('demo_sandbox_desc', 'Use this sandbox to test configurations without setting up project folders, raw CSV ingestion, or contracts.')}</p>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>{t.get('demo_sandbox_li1_strong', 'Flexible Load Profiles:')}</strong> {t.get('demo_sandbox_li1_desc', 'Generate a synthetic factory/office load instantly.')}</li>
                    <li><strong>{t.get('demo_sandbox_li2_strong', 'Battery Peak Shaving:')}</strong> {t.get('demo_sandbox_li2_desc', 'Check if a 200 kWh battery is enough to shave peaks down.')}</li>
                    <li><strong>{t.get('demo_sandbox_li3_strong', 'Solar Self-Consumption:')}</strong> {t.get('demo_sandbox_li3_desc', 'See when the battery charges from solar surplus.')}</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_demo_mode():
    """
    Main orchestrator for the simplified Demo Mode.
    Renders inputs, controls simulation state, and triggers results visualization.
    Calculations run in 1-hour intervals for optimal performance.
    """
    merge_demo_translations()
    t = st.session_state.get('t', {})

    st.markdown(f"## {t.get('demo_title', 'Demo Mode: Instant Scenario Simulator')}")
    st.write(t.get('demo_desc', 'Throw together a custom energy scenario in seconds! Select your technologies, adjust limits, and visualize the output in real-time.'))
    st.divider()

    # Initialize results session state if missing
    if "demo_results" not in st.session_state:
        st.session_state["demo_results"] = None

    # Sidebar layout settings block
    st.sidebar.divider()
    st.sidebar.markdown(f"### {t.get('demo_layout_title', 'Demo Layout')}")
    
    layout_mode_map = {
        t.get('demo_layout_split', 'Split Columns'): "split",
        t.get('demo_layout_stacked', 'Stacked (Full-Width)'): "stacked"
    }
    
    layout_mode_sel = st.sidebar.radio(
        t.get('demo_layout_title', 'Demo Layout'),
        options=list(layout_mode_map.keys()),
        index=0,
        label_visibility="collapsed",
        key="demo_layout_mode_radio"
    )
    layout_mode = layout_mode_map[layout_mode_sel]
    
    input_width_pct = 33
    if layout_mode == "split":
        input_width_pct = st.sidebar.slider(
            t.get('demo_layout_width', 'Input Column Width'),
            min_value=20, max_value=50, value=33, step=5,
            format="%d%%",
            key="demo_layout_width_slider"
        )

    if layout_mode == "split":
        # Split Columns layout (Resizable width)
        input_weight = input_width_pct / 100.0
        results_weight = 1.0 - input_weight
        
        col_input, col_results = st.columns([input_weight, results_weight], gap="large")
        
        with col_input:
            loc_params, has_consumption, monthly_cons, work_days, work_hours, base_load, grid_limit = render_location_consumption_inputs("_split")
            sol_params, has_battery, bat_params = render_solar_battery_inputs("_split", has_consumption, grid_limit)
            has_generator, gen_params, has_financials, fin_params = render_generator_financials_inputs("_split", has_consumption, grid_limit, sol_params.get("installed_kwp", 0.0) > 0.0)
            
            calc_button = st.button(t.get('demo_button_calc', 'Calculate Scenario'), type="primary", use_container_width=True, key="demo_calc_btn_split")
            
        with col_results:
            render_results_section(
                calc_button=calc_button,
                loc_params=loc_params,
                has_consumption=has_consumption,
                monthly_cons=monthly_cons,
                work_days=work_days,
                work_hours=work_hours,
                base_load=base_load,
                grid_limit=grid_limit,
                sol_params=sol_params,
                has_battery=has_battery,
                bat_params=bat_params,
                has_generator=has_generator,
                gen_params=gen_params,
                has_financials=has_financials,
                fin_params=fin_params
            )
            
    else:
        # Stacked layout (Inputs inside a collapsible expander)
        with st.expander(t.get('demo_layout_expander', '🛠️ Simulation Configuration'), expanded=True):
            col_l, col_m, col_r = st.columns(3, gap="medium")
            
            with col_l:
                loc_params, has_consumption, monthly_cons, work_days, work_hours, base_load, grid_limit = render_location_consumption_inputs("_stacked")
            with col_m:
                sol_params, has_battery, bat_params = render_solar_battery_inputs("_stacked", has_consumption, grid_limit)
            with col_r:
                has_generator, gen_params, has_financials, fin_params = render_generator_financials_inputs("_stacked", has_consumption, grid_limit, sol_params.get("installed_kwp", 0.0) > 0.0)
                st.write("<br>", unsafe_allow_html=True)
                calc_button = st.button(t.get('demo_button_calc', 'Calculate Scenario'), type="primary", use_container_width=True, key="demo_calc_btn_stacked")
                
        # Outputs rendered full width below the expander
        render_results_section(
            calc_button=calc_button,
            loc_params=loc_params,
            has_consumption=has_consumption,
            monthly_cons=monthly_cons,
            work_days=work_days,
            work_hours=work_hours,
            base_load=base_load,
            grid_limit=grid_limit,
            sol_params=sol_params,
            has_battery=has_battery,
            bat_params=bat_params,
            has_generator=has_generator,
            gen_params=gen_params,
            has_financials=has_financials,
            fin_params=fin_params
        )
