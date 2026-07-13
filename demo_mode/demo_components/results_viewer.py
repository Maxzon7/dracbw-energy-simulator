# demo_mode/demo_components/results_viewer.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def get_season(month: int, country: str) -> str:
    """Returns the season based on hemisphere (Argentina is Southern Hemisphere)."""
    is_south = "Argentina" in country
    if month in [12, 1, 2]:
        return "Summer ☀️" if is_south else "Winter ❄️"
    elif month in [3, 4, 5]:
        return "Autumn 🍂" if is_south else "Spring 🌸"
    elif month in [6, 7, 8]:
        return "Winter ❄️" if is_south else "Summer ☀️"
    else:
        return "Spring 🌸" if is_south else "Autumn 🍂"

def render_demo_results(
    results: pd.DataFrame, 
    installed_kwp: float, 
    country: str,
    has_consumption: bool = False,
    grid_limit: float = 0.0,
    has_battery: bool = False,
    has_generator: bool = False
):
    """
    Renders the metrics, charts, and export options for Demo Mode.
    Supports both pure Solar Yield simulations and full load-shaving Mini-Scenarios.
    """
    st.write("### 📊 Simulation Results & Analytics")
    
    # 1-hour intervals, so res = 60
    res_factor = 1.0 # 60 / 60 min = 1 hour
    
    # Check what visualizers we need
    is_solar_active = installed_kwp > 0.0 and 'solar_gen_kw' in results.columns
    
    # ==========================================
    # CASE A: PURE SOLAR YIELD (NO CONSUMPTION)
    # ==========================================
    if not has_consumption:
        total_yield_kwh = results['solar_gen_kw'].sum() * res_factor if 'solar_gen_kw' in results.columns else 0.0
        total_yield_mwh = total_yield_kwh / 1000.0
        peak_power_kw = results['solar_gen_kw'].max() if 'solar_gen_kw' in results.columns else 0.0
        
        if installed_kwp > 0:
            capacity_factor = (total_yield_kwh / (installed_kwp * 8760.0)) * 100.0
        else:
            capacity_factor = 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Annual Yield", f"{total_yield_mwh:,.2f} MWh", help="Sum of energy generated over the entire simulated year.")
        m2.metric("Peak Power Output", f"{peak_power_kw:,.1f} kW", help="The absolute maximum power output recorded.")
        m3.metric("Capacity Factor", f"{capacity_factor:.1f} %", help="Ratio of actual output over a year to potential output at full capacity.")
        
        tab_ts, tab_month, tab_season = st.tabs(["📈 Time Series", "📊 Monthly Yield", "📅 Seasonal Profiles"])
        
        with tab_ts:
            st.write("**Hourly Yield Profile**")
            fig_ts = go.Figure()
            fig_ts.add_trace(go.Scattergl(
                x=results['timestamp'], 
                y=results['solar_gen_kw'], 
                name="Solar Yield (kW)", 
                line=dict(color='#FFC107', width=1), 
                fill='tozeroy',
                fillcolor='rgba(255, 193, 7, 0.1)'
            ))
            fig_ts.update_layout(
                height=400, 
                xaxis_title="Date",
                yaxis_title="Power Output (kW)", 
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_ts, use_container_width=True)
            
        with tab_month:
            st.write("**Monthly Energy Generation**")
            results_copy = results.copy()
            results_copy['month_num'] = results_copy['timestamp'].dt.month
            results_copy['month_name'] = results_copy['timestamp'].dt.strftime('%B')
            
            monthly_df = results_copy.groupby(['month_num', 'month_name'])['solar_gen_kw'].sum().reset_index()
            monthly_df['yield_mwh'] = (monthly_df['solar_gen_kw'] * res_factor) / 1000.0
            
            fig_month = go.Figure()
            fig_month.add_trace(go.Bar(
                x=monthly_df['month_name'],
                y=monthly_df['yield_mwh'],
                marker_color='#FF9800',
                text=[f"{val:.1f}" for val in monthly_df['yield_mwh']],
                textposition='auto',
                name="Yield (MWh)"
            ))
            fig_month.update_layout(
                height=400,
                xaxis_title="Month",
                yaxis_title="Energy Yield (MWh)",
                margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_month, use_container_width=True)
            
        with tab_season:
            st.write("**Average Diurnal Yield Shapes by Season**")
            results_copy = results.copy()
            results_copy['month'] = results_copy['timestamp'].dt.month
            results_copy['season'] = results_copy['month'].apply(lambda m: get_season(m, country))
            results_copy['time_of_day'] = results_copy['timestamp'].dt.time
            
            seasonal_avg = results_copy.groupby(['season', 'time_of_day'])['solar_gen_kw'].mean().reset_index()
            seasonal_avg['time_str'] = seasonal_avg['time_of_day'].apply(lambda t: t.strftime('%H:%M'))
            
            season_order = ["Spring 🌸", "Summer ☀️", "Autumn 🍂", "Winter ❄️"]
            season_colors = {"Spring 🌸": "#4CAF50", "Summer ☀️": "#FFC107", "Autumn 🍂": "#FF9800", "Winter ❄️": "#2196F3"}
            
            fig_season = go.Figure()
            for season in season_order:
                season_data = seasonal_avg[seasonal_avg['season'] == season].sort_values('time_of_day')
                if not season_data.empty:
                    fig_season.add_trace(go.Scatter(
                        x=season_data['time_str'],
                        y=season_data['solar_gen_kw'],
                        name=season,
                        mode='lines',
                        line=dict(color=season_colors.get(season, "#9E9E9E"), width=2.5)
                    ))
            fig_season.update_layout(
                height=400,
                xaxis_title="Time of Day",
                yaxis_title="Average Power Output (kW)",
                margin=dict(t=10, b=10, l=10, r=10),
                xaxis=dict(
                    tickmode='array',
                    tickvals=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:00"],
                    ticktext=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:00"]
                ),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_season, use_container_width=True)

    # ==========================================
    # CASE B: MINI-SCENARIO (WITH CONSUMPTION)
    # ==========================================
    else:
        # Calculate Scenario Metrics
        total_cons_kwh = results['consumption_kw'].sum() * res_factor
        total_grid_kwh = results['final_grid_load_kw'].clip(lower=0.0).sum() * res_factor
        
        autarky_pct = (1.0 - (total_grid_kwh / total_cons_kwh)) * 100.0 if total_cons_kwh > 0 else 0.0
        peak_orig = results['consumption_kw'].max()
        peak_new = results['final_grid_load_kw'].max()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Original Peak Load", f"{peak_orig:,.1f} kW", help="Maximum consumption spike before optimization.")
        m2.metric("Optimized Grid Peak", f"{peak_new:,.1f} kW", help="Maximum grid demand after peak shaving / solar self-consumption.")
        m3.metric("Degree of Autarky", f"{autarky_pct:.1f} %", help="Percentage of energy covered by solar or battery output.")

        tab_load, tab_assets, tab_solar_detail = st.tabs(["📈 Load Profile", "🔋 Storage & Assets", "🌞 Solar Details"])
        
        with tab_load:
            st.write("**Hourly System Load Profile**")
            fig_load = go.Figure()
            
            # Original Demand
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['consumption_kw'], name="Original Demand", line=dict(color='#A9A9A9', width=1)))
            # Optimized Grid Demand
            fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['final_grid_load_kw'], name="Optimized Grid Demand", line=dict(color='#00CC96', width=2)))
            
            # Solar Yield
            if is_solar_active:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy', fillcolor='rgba(255,193,7,0.05)'))
                
            # Battery discharging & charging
            if has_battery and 'battery_action_kw' in results.columns:
                bat_discharge = results['battery_action_kw'].clip(lower=0.0)
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=bat_discharge, name="Battery Discharge", line=dict(color='#FFA15A', width=1), fill='tozeroy', fillcolor='rgba(255,161,90,0.05)'))
                
                bat_charge = results['battery_action_kw'].clip(upper=0.0).abs()
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=bat_charge, name="Battery Charge", line=dict(color='#AB63FA', width=1), fill='tozeroy', fillcolor='rgba(171,99,250,0.05)'))
                
            # Generator
            if has_generator and 'generator_action_kw' in results.columns:
                fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name="Generator Output", line=dict(color='#8B0000', width=1), fill='tozeroy', fillcolor='rgba(139,0,0,0.05)'))
                
            # Grid limit horizontal line
            if grid_limit > 0:
                fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text=f"Grid Limit ({grid_limit:.0f} kW)")
                
            fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_load, use_container_width=True)
            
        with tab_assets:
            if has_battery and 'battery_soc_kwh' in results.columns:
                if is_solar_active:
                    # Dual layout: Solar utilization (stacked Area) and Battery SoC
                    c_left, c_right = st.columns(2)
                    
                    with c_left:
                        st.write("**Solar Energy Utilization (kW)**")
                        solar_gen = results['solar_gen_kw']
                        cons = results['consumption_kw']
                        bat_action = results['battery_action_kw']
                        
                        solar_self_cons = np.minimum(solar_gen, cons)
                        bat_charge = np.where(bat_action < 0, np.abs(bat_action), 0.0)
                        solar_surplus = np.maximum(0.0, solar_gen - cons)
                        solar_to_bat = np.minimum(solar_surplus, bat_charge)
                        solar_excess = np.maximum(0.0, solar_gen - solar_self_cons - solar_to_bat)
                        
                        fig_sol_util = go.Figure()
                        fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_self_cons, name="Covering Demand", stackgroup='one', line=dict(width=0.5, color='#4CAF50'), fill='tonexty'))
                        fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_to_bat, name="To Battery", stackgroup='one', line=dict(width=0.5, color='#AB63FA'), fill='tonexty'))
                        fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_excess, name="Excess (Export/Curtail)", stackgroup='one', line=dict(width=0.5, color='#FF9800'), fill='tonexty'))
                        
                        fig_sol_util.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
                        st.plotly_chart(fig_sol_util, use_container_width=True)
                        
                    with c_right:
                        st.write("**Battery State of Charge (SoC) (kWh)**")
                        fig_soc = go.Figure()
                        fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color='#636EFA')))
                        fig_soc.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10))
                        st.plotly_chart(fig_soc, use_container_width=True)
                else:
                    # BESS only full-width SoC chart
                    st.write("**Battery State of Charge (SoC) (kWh)**")
                    fig_soc = go.Figure()
                    fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color='#636EFA')))
                    fig_soc.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_soc, use_container_width=True)
            else:
                st.info("🔋 No battery integrated. Check 'Integrate Battery (BESS)' on the left to simulate storage action.")
                
        with tab_solar_detail:
            if is_solar_active:
                st.write("**Solar Resource Details**")
                
                # Render GHI line and Monthly sums
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.write("Average Daily Seasonal Profiles")
                    results_copy = results.copy()
                    results_copy['month'] = results_copy['timestamp'].dt.month
                    results_copy['season'] = results_copy['month'].apply(lambda m: get_season(m, country))
                    results_copy['time_of_day'] = results_copy['timestamp'].dt.time
                    
                    seasonal_avg = results_copy.groupby(['season', 'time_of_day'])['solar_gen_kw'].mean().reset_index()
                    seasonal_avg['time_str'] = seasonal_avg['time_of_day'].apply(lambda t: t.strftime('%H:%M'))
                    
                    fig_season = go.Figure()
                    season_order = ["Spring 🌸", "Summer ☀️", "Autumn 🍂", "Winter ❄️"]
                    season_colors = {"Spring 🌸": "#4CAF50", "Summer ☀️": "#FFC107", "Autumn 🍂": "#FF9800", "Winter ❄️": "#2196F3"}
                    
                    for season in season_order:
                        season_data = seasonal_avg[seasonal_avg['season'] == season].sort_values('time_of_day')
                        if not season_data.empty:
                            fig_season.add_trace(go.Scatter(x=season_data['time_str'], y=season_data['solar_gen_kw'], name=season, mode='lines', line=dict(color=season_colors[season], width=2)))
                            
                    fig_season.update_layout(height=250, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
                    st.plotly_chart(fig_season, use_container_width=True)
                    
                with col_det2:
                    st.write("Monthly Solar Generation (MWh)")
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
                st.info("☀️ No solar PV integrated. Configure Panel counts in 'Solar PV Setup' to see weather analytics.")

    # Export CSV Section
    st.divider()
    with st.expander("📥 Export Simulated Data as CSV", expanded=False):
        st.write("Download the simulated hourly profile and solar yield results:")
        
        cols_to_export = {
            "Timestamp": results['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        }
        if has_consumption:
            cols_to_export["Consumption_kW"] = results['consumption_kw'].round(2)
            cols_to_export["Optimized_Grid_Load_kW"] = results['final_grid_load_kw'].round(2)
        if 'solar_gen_kw' in results.columns:
            cols_to_export["GHI_W_m2"] = results['ghi_w_m2'].round(1)
            cols_to_export["Solar_Yield_kW"] = results['solar_gen_kw'].round(3)
        if has_battery and 'battery_action_kw' in results.columns:
            cols_to_export["Battery_Action_kW"] = results['battery_action_kw'].round(2)
            cols_to_export["Battery_SoC_kWh"] = results['battery_soc_kwh'].round(2)
        if has_generator and 'generator_action_kw' in results.columns:
            cols_to_export["Generator_Action_kW"] = results['generator_action_kw'].round(2)
            cols_to_export["Generator_Fuel_L"] = results['generator_fuel_l'].round(2)
            
        export_df = pd.DataFrame(cols_to_export)
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="Download CSV File",
            data=csv_data,
            file_name=f"demo_simulation_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="demo_csv_download"
        )
        st.caption("The CSV file contains the timestamp index and all active simulation trace values in 1-hour resolution.")
