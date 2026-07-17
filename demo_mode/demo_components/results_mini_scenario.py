import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from demo_mode.demo_components.results_utils import get_season
from demo_mode.demo_components.results_financials import render_financials_tab

def render_mini_scenario_results(
    results: pd.DataFrame, 
    installed_kwp: float, 
    country: str,
    grid_limit: float = 0.0,
    has_battery: bool = False,
    has_generator: bool = False,
    has_financials: bool = False,
    fin_params: dict = None,
    res_factor: float = 1.0
):
    """Renders the dashboard for Case B: Mini-Scenario (With Consumption)."""
    t = st.session_state.get('t', {})
    is_solar_active = installed_kwp > 0.0 and 'solar_gen_kw' in results.columns
    
    # Calculate Scenario Metrics
    total_cons_kwh = results['consumption_kw'].sum() * res_factor
    total_grid_kwh = results['final_grid_load_kw'].clip(lower=0.0).sum() * res_factor
    
    autarky_pct = (1.0 - (total_grid_kwh / total_cons_kwh)) * 100.0 if total_cons_kwh > 0 else 0.0
    peak_orig = results['consumption_kw'].max()
    peak_new = results['final_grid_load_kw'].max()
    
    m1, m2, m3 = st.columns(3)
    m1.metric(t.get('demo_res_case_b_orig_peak', "Original Peak Load"), f"{peak_orig:,.1f} kW", help=t.get('demo_res_case_b_orig_peak_help', "Maximum consumption spike before optimization."))
    m2.metric(t.get('demo_res_case_b_opt_peak', "Optimized Grid Peak"), f"{peak_new:,.1f} kW", help=t.get('demo_res_case_b_opt_peak_help', "Maximum grid demand after peak shaving / solar self-consumption."))
    m3.metric(t.get('demo_res_case_b_autarky', "Degree of Autarky"), f"{autarky_pct:.1f} %", help=t.get('demo_res_case_b_autarky_help', "Percentage of energy covered by solar or battery output."))

    if has_financials and fin_params:
        tab_load, tab_assets, tab_solar_detail, tab_fin = st.tabs([
            t.get('demo_res_tab_load', "Load Profile"),
            t.get('demo_res_tab_assets', "Storage & Assets"),
            t.get('demo_res_tab_solar', "Solar Details"),
            t.get('demo_res_tab_fin', "💰 Financial Impact (EDEMSA)")
        ])
    else:
        tab_load, tab_assets, tab_solar_detail = st.tabs([
            t.get('demo_res_tab_load', "Load Profile"),
            t.get('demo_res_tab_assets', "Storage & Assets"),
            t.get('demo_res_tab_solar', "Solar Details")
        ])
    
    with tab_load:
        st.write(f"**{t.get('demo_res_load_title', 'Hourly System Load Profile')}**")
        fig_load = go.Figure()
        
        # Original Demand
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['consumption_kw'], name=t.get('demo_res_trace_orig', "Original Demand"), line=dict(color='#A9A9A9', width=1)))
        # Optimized Grid Demand
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['final_grid_load_kw'], name=t.get('demo_res_trace_opt', "Optimized Grid Demand"), line=dict(color='#00CC96', width=2)))
        
        # Solar Yield
        if is_solar_active:
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name=t.get('demo_res_trace_solar', "Solar Yield"), line=dict(color='#FFC107', width=1), fill='tozeroy', fillcolor='rgba(255,193,7,0.05)'))
            
        # Battery discharging & charging
        if has_battery and 'battery_action_kw' in results.columns:
            bat_discharge = results['battery_action_kw'].clip(lower=0.0)
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=bat_discharge, name=t.get('demo_res_trace_dischg', "Battery Discharge"), line=dict(color='#FFA15A', width=1), fill='tozeroy', fillcolor='rgba(255,161,90,0.05)'))
            
            bat_charge = results['battery_action_kw'].clip(upper=0.0).abs()
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=bat_charge, name=t.get('demo_res_trace_chg', "Battery Charge"), line=dict(color='#AB63FA', width=1), fill='tozeroy', fillcolor='rgba(171,99,250,0.05)'))
            
        # Generator
        if has_generator and 'generator_action_kw' in results.columns:
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name=t.get('demo_res_trace_gen', "Generator Output"), line=dict(color='#8B0000', width=1), fill='tozeroy', fillcolor='rgba(139,0,0,0.05)'))
            
        # Grid limit horizontal line
        if grid_limit > 0:
            grid_lim_label = t.get('grid_limit', "Grid Limit")
            fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text=f"{grid_lim_label} ({grid_limit:.0f} kW)")
            
        fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_load, use_container_width=True)
        
    with tab_assets:
        if has_battery and 'battery_soc_kwh' in results.columns:
            bat_params = st.session_state.get("demo_bat_params", {})
            b_type = bat_params.get("battery_type", "LFP (Lithium Iron Phosphate)")
            min_soc = bat_params.get("min_soc_pct", 10.0)
            max_soc = bat_params.get("max_soc_pct", 90.0)
            b_cap_nominal = bat_params.get("b_cap", 200.0)
            cycle_life = bat_params.get("cycle_life", 6000)
            
            # Dynamic calculations
            throughput_kwh = results['battery_action_kw'].clip(lower=0.0).sum() * res_factor
            usable_capacity_kwh = b_cap_nominal * (max_soc - min_soc) / 100.0
            cycles_run = throughput_kwh / usable_capacity_kwh if usable_capacity_kwh > 0 else 0.0
            
            # Degradation calculation
            cycle_deg = (cycles_run / cycle_life) * 100.0 if cycle_life > 0 else 0.0
            calendar_deg = 1.5
            total_deg = max(cycle_deg, calendar_deg)
            
            st.markdown(f"#### {t.get('demo_res_bat_perf_title', 'Storage Performance: ')}{b_type}")
            st.caption(f"{t.get('demo_res_bat_config', 'Configuration: ')}**{bat_params.get('num_batteries', 10)} modules** of **{bat_params.get('cap_per_module', 20.0):.1f} kWh** | SoC range: **{min_soc:.0f}% - {max_soc:.0f}%**")
            
            col_met1, col_met2, col_met3 = st.columns(3)
            col_met1.metric(t.get('demo_res_metric_cycles', "Simulated Cycles"), f"{cycles_run:.1f} Cycles")
            col_met2.metric(t.get('demo_res_metric_deg', "Est. Capacity Degradation"), f"-{total_deg:.2f}% / yr", help=t.get('demo_res_metric_deg_help', "Calculated based on simulated cycle throughput and calendar aging."))
            
            # Temperature capacity retention
            if 'temp_c' in results.columns:
                temp_cap_coeff = bat_params.get('temp_cap_coeff', 0.5) / 100.0
                temp_dev = np.maximum(0.0, 15.0 - results['temp_c']) + np.maximum(0.0, results['temp_c'] - 35.0)
                retention = np.maximum(0.2, 1.0 - temp_dev * temp_cap_coeff)
                min_retention = retention.min() * 100.0
                col_met3.metric(t.get('demo_res_metric_ret', "Min Temp Cap Retention"), f"{min_retention:.1f}%", help=t.get('demo_res_metric_ret_help', "Reduced storage capacity due to cold/hot intervals."))
            else:
                col_met3.metric(t.get('demo_res_metric_ret', "Min Temp Cap Retention"), "100.0% (N/A)")
            st.divider()

            if is_solar_active:
                # Dual layout: Solar utilization (stacked Area) and Battery SoC
                c_left, c_right = st.columns(2)
                
                with c_left:
                    st.write(f"**{t.get('demo_res_solar_util_title', 'Solar Energy Utilization (kW)')}**")
                    solar_gen = results['solar_gen_kw']
                    cons = results['consumption_kw']
                    bat_action = results['battery_action_kw']
                    
                    solar_self_cons = np.minimum(solar_gen, cons)
                    bat_charge = np.where(bat_action < 0, np.abs(bat_action), 0.0)
                    solar_surplus = np.maximum(0.0, solar_gen - cons)
                    solar_to_bat = np.minimum(solar_surplus, bat_charge)
                    solar_excess = np.maximum(0.0, solar_gen - solar_self_cons - solar_to_bat)
                    
                    fig_sol_util = go.Figure()
                    fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_self_cons, name=t.get('demo_res_cover_demand', "Covering Demand"), stackgroup='one', line=dict(width=0.5, color='#4CAF50'), fill='tonexty'))
                    fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_to_bat, name=t.get('demo_res_to_battery', "To Battery"), stackgroup='one', line=dict(width=0.5, color='#AB63FA'), fill='tonexty'))
                    fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_excess, name=t.get('demo_res_excess', "Excess (Export/Curtail)"), stackgroup='one', line=dict(width=0.5, color='#FF9800'), fill='tonexty'))
                    
                    fig_sol_util.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
                    st.plotly_chart(fig_sol_util, use_container_width=True)
                    
                with c_right:
                    st.write(f"**{t.get('demo_res_bat_soc_title', 'Battery State of Charge (SoC) (kWh)')}**")
                    fig_soc = go.Figure()
                    fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color='#636EFA')))
                    fig_soc.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_soc, use_container_width=True)
            else:
                # BESS only full-width SoC chart
                st.write(f"**{t.get('demo_res_bat_soc_title', 'Battery State of Charge (SoC) (kWh)')}**")
                fig_soc = go.Figure()
                fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color='#636EFA')))
                fig_soc.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_soc, use_container_width=True)
        else:
            st.info(t.get('demo_res_solar_info', "No battery integrated. Check 'Integrate Battery (BESS)' on the left to simulate storage action."))
            
    with tab_solar_detail:
        if is_solar_active:
            sol_params = st.session_state.get("demo_sol_params", {})
            panel_type = sol_params.get("panel_type", "Monocrystalline Silicon")
            ghi_source = sol_params.get("ghi_source", "Open-Meteo API")
            yield_factor = sol_params.get("yield_factor", 1.0)
            
            loss_sum = sol_params.get("loss_inverter", 3.0) + sol_params.get("loss_cabling", 1.5) + sol_params.get("loss_soiling", 1.0) + sol_params.get("loss_other", 2.0)
            
            st.markdown(f"#### {t.get('demo_res_sol_details_title', 'Solar Plant Details: ')}{panel_type}")
            st.caption(f"{t.get('demo_res_sol_config', 'Radiation Source: ')}**{ghi_source}** | Yield Factor: **{yield_factor:.2f}** | Total Technical Losses: **{loss_sum:.1f}%**")
            
            col_sol_met1, col_sol_met2, col_sol_met3 = st.columns(3)
            
            # Equivalent full load hours
            total_yield_kwh = results['solar_gen_kw'].sum() * res_factor
            eq_hours = total_yield_kwh / installed_kwp if installed_kwp > 0 else 0.0
            col_sol_met1.metric(t.get('demo_res_sol_full_load', "Equivalent Full-Load Hours"), f"{eq_hours:.1f} hrs/yr")
            
            # Thermal loss avg/max
            if 'temp_c' in results.columns:
                temp_coeff = sol_params.get('temp_coeff', 0.25) / 100.0
                temp_loss = np.maximum(0.0, (results['temp_c'] - 25.0) * temp_coeff)
                avg_temp_loss = temp_loss.mean() * 100.0
                max_temp_loss = temp_loss.max() * 100.0
                col_sol_met2.metric(t.get('demo_res_sol_therm_loss', "Avg / Max Thermal Loss"), f"{avg_temp_loss:.1f}% / {max_temp_loss:.1f}%")
            else:
                col_sol_met2.metric(t.get('demo_res_sol_therm_loss', "Avg / Max Thermal Loss"), "0.0% (N/A)")
                
            # Irradiation
            if 'ghi_w_m2' in results.columns:
                avg_ghi = results['ghi_w_m2'].mean()
                col_sol_met3.metric(t.get('demo_res_sol_avg_ghi', "Average GHI"), f"{avg_ghi:.1f} W/m²")
            else:
                col_sol_met3.metric(t.get('demo_res_sol_avg_ghi', "Average GHI"), "N/A")
            st.divider()
            
            # Render GHI line and Monthly sums
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.write(t.get('demo_res_sol_profiles_title', "Average Daily Seasonal Profiles"))
                results_copy = results.copy()
                results_copy['month'] = results_copy['timestamp'].dt.month
                results_copy['season'] = results_copy['month'].apply(lambda m: get_season(m, country))
                results_copy['time_of_day'] = results_copy['timestamp'].dt.time
                
                seasonal_avg = results_copy.groupby(['season', 'time_of_day'])['solar_gen_kw'].mean().reset_index()
                seasonal_avg['time_str'] = seasonal_avg['time_of_day'].apply(lambda t: t.strftime('%H:%M'))
                
                fig_season = go.Figure()
                season_order = ["Spring", "Summer", "Autumn", "Winter"]
                season_colors = {"Spring": "#4CAF50", "Summer": "#FFC107", "Autumn": "#FF9800", "Winter": "#2196F3"}
                
                for season in season_order:
                    season_data = seasonal_avg[seasonal_avg['season'] == season].sort_values('time_of_day')
                    if not season_data.empty:
                        translated_season_name = t.get(f"demo_season_{season.lower()}", season)
                        fig_season.add_trace(go.Scatter(x=season_data['time_str'], y=season_data['solar_gen_kw'], name=translated_season_name, mode='lines', line=dict(color=season_colors[season], width=2)))
                        
                fig_season.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_season, use_container_width=True)
                
            with col_det2:
                st.write(t.get('demo_res_sol_monthly_mwh', "Monthly Solar Generation (MWh)"))
                results_copy = results.copy()
                results_copy['month_num'] = results_copy['timestamp'].dt.month
                results_copy['month_name'] = results_copy['timestamp'].dt.strftime('%B')
                monthly_df = results_copy.groupby(['month_num', 'month_name'])['solar_gen_kw'].sum().reset_index()
                monthly_df['yield_mwh'] = (monthly_df['solar_gen_kw'] * res_factor) / 1000.0
                
                fig_month = go.Figure()
                fig_month.add_trace(go.Bar(x=monthly_df['month_name'], y=monthly_df['yield_mwh'], marker_color='#FF9800'))
                fig_month.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_month, use_container_width=True)
        else:
            st.info(t.get('demo_res_solar_info_pv', "No solar PV integrated. Configure Panel counts in 'Solar PV Setup' to see weather analytics."))

    if has_financials and fin_params:
        with tab_fin:
            render_financials_tab(results, fin_params)
