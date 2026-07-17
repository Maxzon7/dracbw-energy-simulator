import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from demo_mode.demo_components.results_utils import get_season

def render_pure_solar_results(
    results: pd.DataFrame, 
    installed_kwp: float, 
    country: str,
    res_factor: float = 1.0
):
    """Renders the dashboard for Case A: Pure Solar Yield (No Consumption)."""
    t = st.session_state.get('t', {})

    total_yield_kwh = results['solar_gen_kw'].sum() * res_factor if 'solar_gen_kw' in results.columns else 0.0
    total_yield_mwh = total_yield_kwh / 1000.0
    peak_power_kw = results['solar_gen_kw'].max() if 'solar_gen_kw' in results.columns else 0.0
    
    if installed_kwp > 0:
        capacity_factor = (total_yield_kwh / (installed_kwp * 8760.0)) * 100.0
    else:
        capacity_factor = 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric(t.get('demo_res_case_a_total', "Total Annual Yield"), f"{total_yield_mwh:,.2f} MWh", help=t.get('demo_res_case_a_total_help', "Sum of energy generated over the entire simulated year."))
    m2.metric(t.get('demo_res_case_a_peak', "Peak Power Output"), f"{peak_power_kw:,.1f} kW", help=t.get('demo_res_case_a_peak_help', "The absolute maximum power output recorded."))
    m3.metric(t.get('demo_res_case_a_cf', "Capacity Factor"), f"{capacity_factor:.1f} %", help=t.get('demo_res_case_a_cf_help', "Ratio of actual output over a year to potential output at full capacity."))
    
    tab_ts, tab_month, tab_season = st.tabs([
        t.get('demo_res_tab_ts', "Time Series"), 
        t.get('demo_res_tab_month', "Monthly Yield"), 
        t.get('demo_res_tab_season', "Seasonal Profiles")
    ])
    
    with tab_ts:
        st.write(f"**{t.get('demo_res_ts_title', 'Hourly Yield Profile')}**")
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scattergl(
            x=results['timestamp'], 
            y=results['solar_gen_kw'], 
            name=t.get('demo_res_trace_solar', "Solar Yield"), 
            line=dict(color='#FFC107', width=1), 
            fill='tozeroy',
            fillcolor='rgba(255, 193, 7, 0.1)'
        ))
        fig_ts.update_layout(
            height=400, 
            xaxis_title="Date",
            yaxis_title=t.get('demo_res_case_a_peak', "Peak Power Output") + " (kW)", 
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_ts, use_container_width=True)
        
    with tab_month:
        st.write(f"**{t.get('demo_res_month_title', 'Monthly Energy Generation')}**")
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
            name=t.get('demo_res_month_y', "Energy Yield (MWh)")
        ))
        fig_month.update_layout(
            height=400,
            xaxis_title=t.get('demo_res_month_x', "Month"),
            yaxis_title=t.get('demo_res_month_y', "Energy Yield (MWh)"),
            margin=dict(t=10, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_month, use_container_width=True)
        
    with tab_season:
        st.write(f"**{t.get('demo_res_season_title', 'Average Diurnal Yield Shapes by Season')}**")
        results_copy = results.copy()
        results_copy['month'] = results_copy['timestamp'].dt.month
        results_copy['season'] = results_copy['month'].apply(lambda m: get_season(m, country))
        results_copy['time_of_day'] = results_copy['timestamp'].dt.time
        
        seasonal_avg = results_copy.groupby(['season', 'time_of_day'])['solar_gen_kw'].mean().reset_index()
        seasonal_avg['time_str'] = seasonal_avg['time_of_day'].apply(lambda t: t.strftime('%H:%M'))
        
        season_order = ["Spring", "Summer", "Autumn", "Winter"]
        season_colors = {"Spring": "#4CAF50", "Summer": "#FFC107", "Autumn": "#FF9800", "Winter": "#2196F3"}
        
        fig_season = go.Figure()
        for season in season_order:
            season_data = seasonal_avg[seasonal_avg['season'] == season].sort_values('time_of_day')
            if not season_data.empty:
                # Season labels translated using a dynamic naming convention if they exist
                translated_season_name = t.get(f"demo_season_{season.lower()}", season)
                fig_season.add_trace(go.Scatter(
                    x=season_data['time_str'],
                    y=season_data['solar_gen_kw'],
                    name=translated_season_name,
                    mode='lines',
                    line=dict(color=season_colors.get(season, "#9E9E9E"), width=2.5)
                ))
        fig_season.update_layout(
            height=400,
            xaxis_title=t.get('demo_res_season_x', "Time of Day"),
            yaxis_title=t.get('demo_res_season_y', "Average Power Output (kW)"),
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(
                tickmode='array',
                tickvals=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:00"],
                ticktext=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:00"]
            ),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_season, use_container_width=True)
