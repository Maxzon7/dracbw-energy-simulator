# tabs/tab3_components/financial_engine.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_financial_dashboard(selected_profiles: list, selected_base: str, vault: dict):
    """
    Dynamically calculates and visualizes the 15-year cashflow, ROI, and Break-Even Point 
    for all selected hardware sub-scenarios against the baseline.
    """
    st.write("### 💶 Executive Financial Dashboard (ROI Analysis)")
    st.info("Cashflow projection over 15 years including CAPEX, OPEX, grid tariffs, and energy inflation.")
    
    # 1. Extract Baseline Financial DNA
    base_data = vault[selected_base]
    base_df = base_data['df']
    base_fin = base_data.get('params', {}).get('financial_metadata', {})
    
    e_price = base_fin.get('energy_charge', 0.25)
    p_price = base_fin.get('demand_charge', 120.0)
    fit = base_fin.get('feed_in_tariff', 0.08)
    inflation = base_fin.get('inflation', 3.0) / 100.0
    
    res = base_data.get('params', {}).get('resolution', 15)
    factor = 60 / res
    
    # 2. Calculate Baseline BAU (Business As Usual) Costs
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    base_cost_yr1 = (base_kwh * e_price) + (base_peak * p_price)
    
    # Prepare Chart
    fig = go.Figure()
    fig.add_hline(y=0, line_color="white", line_width=1)
    
    results_data = []
    
    # 3. Calculate Cashflow for every Variant
    for name in selected_profiles:
        if name == selected_base:
            continue # Baseline itself has no ROI
            
        scen = vault[name]
        sub_df = scen['df']
        hw_params = scen.get('params', {}).get('hardware_params', {})
        
        # Safely extract CAPEX/OPEX depending on Isolated vs. Combined mode
        capex = hw_params.get('total_capex', 0)
        opex_pct = hw_params.get('opex_pct', 0) / 100.0
        opex = capex * opex_pct
        
        if capex == 0: # Check if it's a combined cascade
            c1 = hw_params.get('solar', {}).get('total_capex', 0)
            c2 = hw_params.get('battery', {}).get('total_capex', 0)
            o1 = c1 * (hw_params.get('solar', {}).get('opex_pct', 0) / 100.0)
            o2 = c2 * (hw_params.get('battery', {}).get('opex_pct', 0) / 100.0)
            capex = c1 + c2
            opex = o1 + o2
            
        if capex == 0:
            continue # Not a hardware scenario, skip financial math
            
        # Variant Operational Costs
        sub_kwh = sub_df['final_grid_load_kw'].clip(lower=0.0).sum() / factor
        sub_peak = sub_df['final_grid_load_kw'].max()
        sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0])).sum() / factor
        
        sub_cost_yr1 = (sub_kwh * e_price) + (sub_peak * p_price) - (sub_export * fit)
        gross_savings = base_cost_yr1 - sub_cost_yr1
        
        # 15-Year Array Math
        cashflow = [-capex] # Year 0 = Initial Investment
        for y in range(1, 16):
            inflated_savings = gross_savings * ((1 + inflation) ** (y - 1))
            inflated_opex = opex * ((1 + inflation) ** (y - 1)) 
            net_yearly = inflated_savings - inflated_opex
            cashflow.append(cashflow[-1] + net_yearly)
            
        break_even = next((y for y, v in enumerate(cashflow) if v >= 0), "> 15")
        
        # Add to Chart
        fig.add_trace(go.Scatter(
            x=list(range(0, 16)), y=cashflow, 
            mode='lines+markers', name=name,
            hovertemplate="Year %{x}<br>Cashflow: %{y:,.0f} €"
        ))
        
        # Add to Table
        results_data.append({
            "Variant Scenario": name,
            "Total CAPEX (€)": f"- {capex:,.0f} €",
            "Year 1 Net Savings": f"+ {gross_savings - opex:,.0f} €",
            "ROI (Break-Even)": f"{break_even} Years" if isinstance(break_even, int) else "No ROI",
            "15-Year Net Profit": f"{cashflow[-1]:,.0f} €"
        })
        
    # Render Output
    if results_data:
        fig.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Operating Year", yaxis_title="Cumulative Net Cashflow (€)",
            hovermode="x unified", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pd.DataFrame(results_data), use_container_width=True, hide_index=True)
    else:
        st.info("Select at least one hardware variant (with CAPEX configured) to view the financial ROI analysis.")