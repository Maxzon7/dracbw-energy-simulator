# tabs/tab1_components/financial_ui.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_financial_inputs(p_fin: dict, active_scenario: str) -> dict:
    """
    Renders the economic baseline inputs inside an expander.
    Collects grid tariffs, inflation rates, one-time connection costs, and fuel prices.
    """
    with st.expander("💶 Economic Baseline (Tariffs & Financials)", expanded=True):
        st.write("Define the customer's current energy contracts and setup costs to establish the business-as-usual cost trajectory.")
        
        c1, c2, c3 = st.columns(3)
        energy_charge = c1.number_input("Energy Charge (€/kWh)", value=float(p_fin.get('energy_charge', 0.25)), step=0.01, format="%.3f")
        demand_charge = c2.number_input("Peak Demand Charge (€/kW/year)", value=float(p_fin.get('demand_charge', 120.0)), step=5.0, format="%.1f")
        
        baseline_grid_capex = c3.number_input(
            "Baseline Grid Upgrade CAPEX (€)", 
            value=float(p_fin.get('baseline_grid_capex', 0.0)), 
            step=1000.0, 
            format="%.1f",
            help="One-time costs for a traditional grid connection (e.g., 63,000 € for a new AC5 transformer in the baseline setup)."
        )
        
        c4, c5, c6 = st.columns(3)
        feed_in_tariff = c4.number_input("Feed-in Tariff (€/kWh)", value=float(p_fin.get('feed_in_tariff', 0.08)), step=0.01, format="%.3f")
        inflation = c5.number_input("Annual Energy Inflation (%)", value=float(p_fin.get('inflation', 3.0)), step=0.5, format="%.1f")
        
        # NEW: Input for the physical fuel burned by the backup generator
        diesel_price = c6.number_input(
            "Diesel/Fuel Price (€/L)", 
            value=float(p_fin.get('diesel_price', 1.50)), 
            step=0.05, 
            format="%.2f",
            help="Cost per liter of fuel for backup generators. Used to financially penalize systems that rely heavily on fossil fuels."
        )
        
        return {
            "energy_charge": energy_charge,
            "demand_charge": demand_charge,
            "baseline_grid_capex": baseline_grid_capex,
            "feed_in_tariff": feed_in_tariff,
            "inflation": inflation,
            "diesel_price": diesel_price
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
        base_grid_capex = fin_params.get('baseline_grid_capex', 0.0)
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
            title=f"Base Year 1 Operating Costs: {base_energy_cost + base_peak_cost:,.0f} €",
            xaxis_title="Operating Year",
            yaxis_title="Total Costs (€)",
            height=350,
            margin=dict(l=0, r=0, t=40, b=0),
            legend=dict(orientation="h", y=1.15)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        total_15y = sum(energy_costs) + sum(peak_costs) + base_grid_capex
        st.success(f"💡 **Cumulative Total Costs (15 Years including initial Grid CAPEX): {total_15y:,.0f} €**")