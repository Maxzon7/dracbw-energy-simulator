# tabs/tab1_components/financial_ui.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_financial_inputs(p_fin: dict, active_scenario: str) -> dict:
    """
    Renders the economic baseline inputs inside an expander.
    Collects grid tariffs and inflation rates.
    """
    with st.expander("💶 Economic Baseline (Tariffs & Financials)", expanded=True):
        st.write("Define the customer's current energy contracts to establish the business-as-usual cost trajectory.")
        
        c1, c2 = st.columns(2)
        energy_charge = c1.number_input("Energy Charge (€/kWh)", value=float(p_fin.get('energy_charge', 0.25)), step=0.01, format="%.3f")
        demand_charge = c2.number_input("Peak Demand Charge (€/kW/year)", value=float(p_fin.get('demand_charge', 120.0)), step=5.0, format="%.1f")
        
        c3, c4 = st.columns(2)
        feed_in_tariff = c3.number_input("Feed-in Tariff (€/kWh)", value=float(p_fin.get('feed_in_tariff', 0.08)), step=0.01, format="%.3f")
        inflation = c4.number_input("Annual Energy Inflation (%)", value=float(p_fin.get('inflation', 3.0)), step=0.5, format="%.1f")
        
        return {
            "energy_charge": energy_charge,
            "demand_charge": demand_charge,
            "feed_in_tariff": feed_in_tariff,
            "inflation": inflation
        }

def render_financial_projection(df: pd.DataFrame, fin_params: dict):
    """
    Calculates and renders a 15-year baseline cost projection chart.
    """
    if df is None or df.empty:
        return
        
    with st.expander("📈 15-Year Baseline Cost Projection (Business-as-Usual)", expanded=True):
        st.info("Projected electricity costs over the next 15 years assuming no hardware interventions are made.")
        
        # Calculate baseline metrics
        resolution = 15 # Assuming 15 min data
        annual_energy_kwh = df['consumption_kw'].sum() / (60 / resolution)
        annual_peak_kw = df['consumption_kw'].max()
        
        e_price = fin_params.get('energy_charge', 0.25)
        p_price = fin_params.get('demand_charge', 120.0)
        inflation = fin_params.get('inflation', 3.0) / 100.0
        
        base_energy_cost = annual_energy_kwh * e_price
        base_peak_cost = annual_peak_kw * p_price
        
        years = list(range(1, 16))
        energy_costs = []
        peak_costs = []
        
        # Compound Inflation Math
        for y in years:
            multiplier = (1 + inflation) ** (y - 1)
            energy_costs.append(base_energy_cost * multiplier)
            peak_costs.append(base_peak_cost * multiplier)
            
        # Draw Stacked Bar Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=energy_costs, name="Energy Cost (€)", marker_color="#3498db"))
        fig.add_trace(go.Bar(x=years, y=peak_costs, name="Peak Demand Cost (€)", marker_color="#e74c3c"))
        
        fig.update_layout(
            barmode='stack',
            title=f"Base Year 1 Costs: {base_energy_cost + base_peak_cost:,.0f} €",
            xaxis_title="Operating Year",
            yaxis_title="Total Costs (€)",
            height=350,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", y=1.15)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        total_15y = sum(energy_costs) + sum(peak_costs)
        st.success(f"💡 **Cumulative Total Costs (15 Years): {total_15y:,.0f} €**")