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

def render_demo_results(results: pd.DataFrame, installed_kwp: float, country: str):
    """
    Renders the metrics, charts, and export options for Demo Mode.
    """
    st.write("### 📊 Simulation Results & Analytics")
    
    # Calculate analytical metrics
    # 15-minute intervals, so sum() * 0.25 gives kWh
    total_yield_kwh = results['solar_gen_kw'].sum() * 0.25
    total_yield_mwh = total_yield_kwh / 1000.0
    peak_power_kw = results['solar_gen_kw'].max()
    
    # Capacity Factor (%) = Yield (kWh) / (Installed Capacity (kWp) * 8760 hours)
    if installed_kwp > 0:
        capacity_factor = (total_yield_kwh / (installed_kwp * 8760.0)) * 100.0
    else:
        capacity_factor = 0.0

    # Display KPI metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Annual Yield", f"{total_yield_mwh:,.2f} MWh", help="Sum of energy generated over the entire simulated year.")
    m2.metric("Peak Power Output", f"{peak_power_kw:,.1f} kW", help="The absolute maximum power output recorded.")
    m3.metric("Capacity Factor", f"{capacity_factor:.1f} %", help="Ratio of actual output over a year to potential output at full capacity.")
    
    # Tabs for different visualizations
    tab_ts, tab_month, tab_season = st.tabs(["📈 Time Series", "📊 Monthly Yield", "📅 Seasonal Profiles"])
    
    with tab_ts:
        st.write("**Quarter-Hourly Yield Profile**")
        fig_ts = go.Figure()
        
        # Plot solar yield
        fig_ts.add_trace(go.Scattergl(
            x=results['timestamp'], 
            y=results['solar_gen_kw'], 
            name="Solar Yield (kW)", 
            line=dict(color='#FFC107', width=1), 
            fill='tozeroy',
            fillcolor='rgba(255, 193, 7, 0.1)'
        ))
        
        # Plot GHI on secondary axis or background if we want, let's keep it clean
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
        
        # Aggregate monthly yields
        results_copy = results.copy()
        results_copy['month_num'] = results_copy['timestamp'].dt.month
        results_copy['month_name'] = results_copy['timestamp'].dt.strftime('%B')
        
        monthly_df = (
            results_copy.groupby(['month_num', 'month_name'])['solar_gen_kw']
            .sum()
            .reset_index()
        )
        # 15-min intervals to kWh
        monthly_df['yield_kwh'] = monthly_df['solar_gen_kw'] * 0.25
        monthly_df['yield_mwh'] = monthly_df['yield_kwh'] / 1000.0
        
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
        
        # Calculate seasonal averages for each time-of-day
        seasonal_avg = (
            results_copy.groupby(['season', 'time_of_day'])['solar_gen_kw']
            .mean()
            .reset_index()
        )
        
        # Convert time_of_day to string for x-axis
        seasonal_avg['time_str'] = seasonal_avg['time_of_day'].apply(lambda t: t.strftime('%H:%M'))
        
        # Order seasons to make sure they display in logical cycle
        season_order = ["Spring 🌸", "Summer ☀️", "Autumn 🍂", "Winter ❄️"]
        season_colors = {
            "Spring 🌸": "#4CAF50",
            "Summer ☀️": "#FFC107",
            "Autumn 🍂": "#FF9800",
            "Winter ❄️": "#2196F3"
        }
        
        fig_season = go.Figure()
        for season in season_order:
            season_data = seasonal_avg[seasonal_avg['season'] == season]
            if not season_data.empty:
                # Sort by time_of_day
                season_data = season_data.sort_values('time_of_day')
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
                tickvals=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:45"],
                ticktext=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:45"]
            ),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_season, use_container_width=True)

    # Export CSV Section
    st.divider()
    with st.expander("📥 Export Yield Data as CSV", expanded=False):
        st.write("Download the simulated quarter-hourly weather and yield data:")
        
        export_df = pd.DataFrame({
            "Timestamp": results['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
            "GHI_W_m2": results['ghi_w_m2'].round(1),
            "Solar_Yield_kW": results['solar_gen_kw'].round(3)
        })
        
        csv_data = export_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="Download CSV File",
            data=csv_data,
            file_name=f"solar_yield_{country.split(' ')[0].lower()}_{installed_kwp:.0f}kwp.csv",
            mime="text/csv",
            use_container_width=True,
            key="demo_csv_download"
        )
        st.caption("The CSV file contains Timestamp, Global Horizontal Irradiation (GHI in W/m²), and simulated solar electrical power (kW).")
