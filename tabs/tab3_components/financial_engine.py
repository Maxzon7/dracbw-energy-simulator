# tabs/tab3_components/financial_engine.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def render_financial_dashboard(selected_profiles: list, selected_base: str, vault: dict):
    """
    Dynamically calculates and visualizes the 15-year cashflow, ROI, and Net Present Value (NPV)
    for all selected hardware sub-scenarios against the baseline.
    Generates detailed year-by-year cashflow series and auto-saves them back into the vault.
    """
    st.write("### 💶 Executive Financial Dashboard (DCF & ROI Analysis)")
    
    col_info, col_wacc = st.columns([2, 1])
    with col_info:
        st.info("Discounted Cash Flow (DCF) projection over 15 years including CAPEX, OPEX, grid tariffs, fuel costs, and compounding energy inflation.")
    with col_wacc:
        discount_rate = st.number_input(
            "Discount Rate / WACC (%)", 
            value=5.0, step=0.5, 
            help="Used to discount future cashflows to calculate the Net Present Value (NPV)."
        ) / 100.0
    
    # 1. Extract Baseline Financial DNA
    base_data = vault[selected_base]
    base_df = base_data['df']
    base_fin = base_data.get('params', {}).get('financial_metadata', {})
    
    e_price = base_fin.get('energy_charge', 0.25)
    p_price = base_fin.get('demand_charge', 120.0)
    base_grid_capex = base_fin.get('baseline_grid_capex', 0.0) 
    fit = base_fin.get('feed_in_tariff', 0.08)
    inflation = base_fin.get('inflation', 3.0) / 100.0
    diesel_price = base_fin.get('diesel_price', 1.50) # NEW: Unpack fuel price
    
    res = base_data.get('params', {}).get('resolution', 15)
    factor = 60 / res
    
    # 2. Calculate Baseline BAU (Business As Usual) Costs
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    base_grid_bill_yr1 = (base_kwh * e_price) + (base_peak * p_price)
    
    fig = go.Figure()
    fig.add_hline(y=0, line_color="white", line_width=1)
    
    summary_data = []
    detailed_tables = {}
    
    # 3. Calculate Advanced Cashflow Series for every Variant
    for name in selected_profiles:
        if name == selected_base:
            continue # Baseline itself has no comparative ROI
            
        scen = vault[name]
        sub_df = scen['df']
        hw_params = scen.get('params', {}).get('hardware_params', {})
        
        # Safely extract CAPEX/OPEX depending on Isolated vs. Combined mode
        capex = hw_params.get('total_capex', 0)
        opex_pct = hw_params.get('opex_pct', 0) / 100.0
        opex_yr1 = capex * opex_pct
        
        if capex == 0: # Check if it's a combined cascade
            c1 = hw_params.get('solar', {}).get('total_capex', 0)
            c2 = hw_params.get('battery', {}).get('total_capex', 0)
            o1 = c1 * (hw_params.get('solar', {}).get('opex_pct', 0) / 100.0)
            o2 = c2 * (hw_params.get('battery', {}).get('opex_pct', 0) / 100.0)
            capex = c1 + c2
            opex_yr1 = o1 + o2
            
        if capex == 0:
            continue # Skip non-hardware scenarios
            
        # Variant Operational Costs (Grid interaction only)
        sub_kwh = sub_df['final_grid_load_kw'].clip(lower=0.0).sum() / factor
        sub_peak = sub_df['final_grid_load_kw'].max()
        sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0])).sum() / factor
        
        sub_grid_bill_yr1 = (sub_kwh * e_price) + (sub_peak * p_price) - (sub_export * fit)
        grid_savings_yr1 = base_grid_bill_yr1 - sub_grid_bill_yr1
        
        # --- NEW: GENERATOR FUEL COSTS ---
        # Get total fuel burned from the simulation and multiply by current diesel price
        annual_fuel_l = sub_df.get('generator_fuel_l', pd.Series([0])).sum()
        fuel_cost_yr1 = annual_fuel_l * diesel_price
        
        # --- 15-YEAR CASHFLOW CASCADING MATHEMATICS ---
        cf_table = []
        
        # Net Year 0 cashflow accounts for avoided grid upgrade costs minus new hardware investments
        net_year0 = base_grid_capex - capex
        cum_cf = net_year0
        cum_npv = net_year0
        
        # Year 0: Initial Investment / Avoided Baseline Cost
        cf_table.append({
            "Year": 0, 
            "CAPEX (€)": round(-capex, 2), 
            "OPEX (€)": 0, 
            "Fuel Cost (€)": 0,
            "Grid Savings (€)": round(base_grid_capex, 2),
            "Net Cashflow (€)": round(net_year0, 2), 
            "Cumulative Cashflow (€)": round(cum_cf, 2), 
            "Present Value (PV)": round(net_year0, 2), 
            "Cumulative NPV (€)": round(cum_npv, 2)
        })
        
        # If avoided costs completely cover the new investment, project breaks even on Day 1
        break_even_yr = 0 if cum_cf >= 0 else "> 15"
        
        # Years 1 to 15: Operations & Compounding
        for y in range(1, 16):
            infl_multiplier = (1 + inflation) ** (y - 1)
            
            # Inflate grid savings, maintenance, and fuel prices over time
            sav_y = grid_savings_yr1 * infl_multiplier
            opx_y = opex_yr1 * infl_multiplier
            fuel_y = fuel_cost_yr1 * infl_multiplier
            
            net_y = sav_y - opx_y - fuel_y
            cum_cf += net_y
            
            # Discounting for Net Present Value (NPV)
            pv_y = net_y / ((1 + discount_rate) ** y)
            cum_npv += pv_y
            
            cf_table.append({
                "Year": y, "CAPEX (€)": 0, "OPEX (€)": round(-opx_y, 2), "Fuel Cost (€)": round(-fuel_y, 2),
                "Grid Savings (€)": round(sav_y, 2), "Net Cashflow (€)": round(net_y, 2), 
                "Cumulative Cashflow (€)": round(cum_cf, 2), "Present Value (PV)": round(pv_y, 2), 
                "Cumulative NPV (€)": round(cum_npv, 2)
            })
            
            # Check for Break-Even Point
            if break_even_yr == "> 15" and cum_cf >= 0:
                break_even_yr = y
                
        # --- SAVE FINANCIALS DIRECTLY INTO THE ACTIVE VAULT ---
        vault[name]['financial_metrics'] = {
            "discount_rate_used": discount_rate,
            "roi_years": break_even_yr,
            "net_present_value": cum_npv,
            "total_15y_profit": cum_cf,
            "cashflow_series": cf_table
        }
        
        # Add Line to Waterfall Chart
        plot_y = [row["Cumulative Cashflow (€)"] for row in cf_table]
        fig.add_trace(go.Scatter(
            x=list(range(16)), y=plot_y, mode='lines+markers', name=name,
            hovertemplate="Year %{x}<br>Cashflow: %{y:,.0f} €"
        ))
        
        # Add to Summary Dashboard
        summary_data.append({
            "Variant Scenario": name,
            "Total CAPEX": f"- {capex:,.0f} €",
            "Year 1 Net Savings": f"+ {grid_savings_yr1 - opex_yr1 - fuel_cost_yr1:,.0f} €",
            "Fuel Penalty (Y1)": f"- {fuel_cost_yr1:,.0f} €" if fuel_cost_yr1 > 0 else "0 €",
            "Break-Even (ROI)": f"{break_even_yr} Years" if isinstance(break_even_yr, str) or break_even_yr > 0 else "Instant (Day 1)",
            "15Y Cum. Cashflow": f"{cum_cf:,.0f} €",
            "15Y Net Present Value (NPV)": f"{cum_npv:,.0f} €"
        })
        
        detailed_tables[name] = cf_table
        
    # --- RENDER OUTPUTS ---
    if summary_data:
        fig.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Operating Year", yaxis_title="Cumulative Net Cashflow (€)",
            hovermode="x unified", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("#### 🏆 Financial Performance Summary")
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.divider()
        st.write("#### 📊 Detailed 15-Year Cashflow Series")
        st.info("Analyze the exact yearly progression of grid savings, maintenance costs, fuel burn penalties, and discounted values.")
        
        variant_names = list(detailed_tables.keys())
        ui_tabs = st.tabs([f"🌿 {n}" for n in variant_names])
        
        for idx, t_name in enumerate(variant_names):
            with ui_tabs[idx]:
                df_cf = pd.DataFrame(detailed_tables[t_name])
                st.dataframe(
                    df_cf.style.format({col: "{:,.0f} €" for col in df_cf.columns if "€" in col or "PV" in col}),
                    use_container_width=True, hide_index=True
                )
    else:
        st.warning("Please select at least one hardware variant (with CAPEX configured) to view the financial ROI analysis.")