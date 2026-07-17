import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from tabs.tab3_components.financial_engine import generate_15_year_cashflow, get_payback_year, calculate_irr
from tabs.tab3_components.comparison_cashflows import generate_baseline_cashflow_df

def render_cfo_cockpit_from_classes(base_scenario, selected_subs):
    """Renders the executive CFO Dashboard with line chart and cashflow tables."""
    st.header("Executive CFO Dashboard")
    
    if not selected_subs:
        st.info("Select at least one variant above to see the financial comparison.")
        return
        
    has_financials = any(sub.financials is not None for sub in selected_subs)
    
    if not has_financials:
        st.warning("**Technical Mode**: No financial data was entered in Tab 2. Showing performance summary only.")
        tech_data = []
        for sub in selected_subs:
            tech_data.append({
                "Scenario": sub.name, "Battery (kWh)": sub.battery_kwh, "Battery Power (kW)": sub.battery_kw,
                "Solar (kWp)": sub.solar_kwp, "Hardware Added?": "Yes" if (sub.battery_kwh > 0 or sub.solar_kwp > 0) else "No"
            })
        st.table(pd.DataFrame(tech_data))
        return
        
    # Extract baseline financials
    fin_meta = base_scenario.metadata.get('financial_metadata', {})
    lifespan = int(fin_meta.get('lifespan_years', 15))
    
    col_info, col_wacc = st.columns([2, 1])
    with col_info:
        st.info(f"Discounted Cash Flow (DCF) projection over a **{lifespan}-Year Lifespan** factoring CAPEX, OPEX, grid tariffs, fuel costs, and escalation.")
    with col_wacc:
        discount_rate = st.number_input(
            "Discount Rate / WACC (%)", 
            value=5.0, step=0.5, 
            key="cf_wacc_input",
            help="Used to discount future cashflows to calculate the Net Present Value (NPV)."
        ) / 100.0

    # Sensitivity inputs in expander
    with st.expander("📊 Sensitivity Analysis Settings", expanded=False):
        st.write("Simulate changes in core economic factors to test scenario robustness:")
        sens_col1, sens_col2, sens_col3 = st.columns(3)
        capex_mult = sens_col1.slider("CAPEX Variation (%)", -20, 20, 0, step=5, key="cf_sens_capex_var") / 100.0 + 1.0
        energy_inf_add = sens_col2.slider("Additional Energy Escalation (%/Yr)", -3.0, 5.0, 0.0, step=0.5, key="cf_sens_energy_inf") / 100.0
        fuel_inf_add = sens_col3.slider("Additional Fuel Escalation (%/Yr)", -3.0, 5.0, 0.0, step=0.5, key="cf_sens_fuel_inf") / 100.0

    fig_cf = go.Figure()
    fig_cf.add_hline(y=0, line_color="rgba(100,100,100,0.5)", line_width=1, line_dash="dash")
    
    kpi_data = []
    detailed_tables = {}
    
    # Calculate baseline BAU reference TCO and LCOE
    base_df = base_scenario.original_profile
    if len(base_df) > 0:
        factor = 4.0 if len(base_df) > 15000 else 1.0
    else:
        factor = 1.0
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    base_tariff = base_scenario.base_tariff
    
    e_price = base_tariff.price_per_kwh
    p_price = base_tariff.price_per_kw_peak
    fixed_annual = base_tariff.fixed_costs_per_year
    base_grid_capex = float(fin_meta.get('baseline_grid_capex', 0.0))
    fit = float(fin_meta.get('feed_in_tariff', 0.08))
    
    base_grid_bill_yr1 = fixed_annual + (base_kwh * e_price) + (base_peak * p_price)
    
    energy_esc = float(fin_meta.get('energy_price_growth', 4.0)) / 100.0 + energy_inf_add
    
    discounted_energy_sum = 0.0
    base_tco = base_grid_capex
    for y in range(1, lifespan + 1):
        grid_multiplier = (1.0 + energy_esc) ** (y - 1)
        discount_multiplier = (1.0 + discount_rate) ** y
        bill_y = base_grid_bill_yr1 * grid_multiplier
        base_tco += bill_y / discount_multiplier
        discounted_energy_sum += base_kwh / discount_multiplier
        
    base_lcoe = base_tco / discounted_energy_sum if discounted_energy_sum > 0 else 0.0

    # Process each sub scenario
    for sub in selected_subs:
        if sub.financials:
            # Generate cashflows incorporating sensitivity factors
            df_cashflow = generate_15_year_cashflow(
                sub, base_scenario, discount_rate,
                capex_mult=capex_mult,
                energy_esc_add=energy_inf_add,
                diesel_esc_add=fuel_inf_add
            )
            
            if df_cashflow is not None:
                payback = get_payback_year(df_cashflow)
                
                # Plot line
                fig_cf.add_trace(go.Scatter(
                    x=df_cashflow["Year"],
                    y=df_cashflow["Cumulative Cashflow (€)"],
                    mode='lines+markers',
                    name=sub.name,
                    line=dict(width=3)
                ))
                
                # NPV
                npv_val = df_cashflow["Cumulative NPV (€)"].iloc[-1]
                
                # TCO and LCOE for variant
                sub_tco = sub.financials.capex * capex_mult
                sub_tariff = sub.custom_tariff if sub.custom_tariff else base_scenario.base_tariff
                sub_df = sub.simulated_profile
                sub_kwh = sub_df['final_grid_load_kw'].clip(lower=0.0).sum() / factor
                sub_peak = sub_df['final_grid_load_kw'].max()
                sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0.0])).sum() / factor
                
                sub_grid_bill_yr1 = (
                    sub_tariff.fixed_costs_per_year +
                    (sub_kwh * sub_tariff.price_per_kwh) +
                    (sub_peak * sub_tariff.price_per_kw_peak) -
                    (sub_export * fit)
                )
                
                # Generator cost elements
                gen_params = sub.tech_params.get('generator', {}) if sub.tech_params else {}
                gen_rent = float(gen_params.get('capex_per_year', 0.0))
                gen_maint_hr = float(gen_params.get('opex_per_hour', 0.0))
                gen_action = sub_df.get('generator_action_kw', pd.Series([0.0]))
                run_hours = (gen_action > 0.1).sum()
                gen_maint_yr1 = run_hours * gen_maint_hr
                
                diesel_price = float(fin_meta.get('diesel_price', 1.50))
                annual_fuel_l = sub_df.get('generator_fuel_l', pd.Series([0.0])).sum()
                fuel_cost_yr1 = annual_fuel_l * diesel_price
                
                # Combined variables
                opex_yr1 = sub.financials.opex_yearly * capex_mult
                inflation_rate = sub.financials.inflation_rate
                
                sol_deg = float(sub.tech_params.get('solar', {}).get('degradation_pct', 0.5)) / 100.0 if (sub.tech_params and 'solar' in sub.tech_params) else 0.005
                
                bess_params = sub.tech_params.get('battery', {}) if sub.tech_params else {}
                rep_year = bess_params.get('replacement_year', 10) if bess_params else 10
                rep_pct = bess_params.get('replacement_pct', 100.0) / 100.0 if bess_params else 1.0
                rep_cost_base = bess_params.get('total_storage_capex', 0.0) * rep_pct if bess_params else 0.0
                
                diesel_esc = float(fin_meta.get('diesel_price_growth', 2.0)) / 100.0 + fuel_inf_add
                
                for jahr in range(1, lifespan + 1):
                    infl_multiplier = (1.0 + inflation_rate) ** (jahr - 1)
                    grid_multiplier = (1.0 + energy_esc) ** (jahr - 1)
                    fuel_multiplier = (1.0 + diesel_esc) ** (jahr - 1)
                    discount_multiplier = (1.0 + discount_rate) ** jahr
                    
                    opx_y = opex_yr1 * infl_multiplier
                    fuel_y = fuel_cost_yr1 * fuel_multiplier
                    rent_y = gen_rent * infl_multiplier
                    maint_y = gen_maint_yr1 * infl_multiplier
                    
                    rep_y = 0.0
                    if jahr == rep_year:
                        rep_y = rep_cost_base * infl_multiplier
                        
                    annual_net_cost = sub_grid_bill_yr1 * grid_multiplier + opx_y + fuel_y + rent_y + maint_y + rep_y
                    sub_tco += annual_net_cost / discount_multiplier
                    
                lcoe_val = sub_tco / discounted_energy_sum if discounted_energy_sum > 0 else 0.0
                
                # IRR from net cashflows series list
                cashflows = [row["Net Cashflow (€)"] for row in df_cashflow.to_dict('records')]
                irr_val = calculate_irr(cashflows)
                irr_str = f"{irr_val*100.0:.2f} %" if irr_val > -0.9 else "N/A"
                
                kpi_data.append({
                    "Scenario": sub.name,
                    "NPV (Net Present Value)": npv_val,
                    "TCO (Total Cost of Ownership)": sub_tco,
                    "LCOE": lcoe_val,
                    "IRR": irr_str,
                    "Payback Period": f"{payback} Years" if payback > 0 else "Never (> lifespan Yrs)"
                })
                
                detailed_tables[sub.name] = df_cashflow

    if kpi_data:
        # Generate and add Baseline detailed cashflow table
        df_base_cf = generate_baseline_cashflow_df(
            base_scenario, discount_rate,
            capex_mult=capex_mult,
            energy_esc_add=energy_inf_add
        )
        detailed_tables["Baseline BAU"] = df_base_cf

        # Append baseline BAU reference
        kpi_data.append({
            "Scenario": f"{base_scenario.name} (Baseline BAU)",
            "NPV (Net Present Value)" : 0.0,
            "TCO (Total Cost of Ownership)": base_tco,
            "LCOE": base_lcoe,
            "IRR": "Baseline Ref",
            "Payback Period": "Baseline Ref"
        })
        
        # Scenario Ranking by NPV
        kpi_df = pd.DataFrame(kpi_data)
        kpi_df["sorting_key"] = kpi_df["NPV (Net Present Value)"].apply(lambda x: x if x is not None else -9999999.0)
        kpi_df = kpi_df.sort_values(by="sorting_key", ascending=False).drop(columns=["sorting_key"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Management Summary & Rankings")
            disp_df = kpi_df.copy()
            disp_df["NPV (Net Present Value)"] = disp_df["NPV (Net Present Value)"].apply(lambda x: f"{x:,.0f} €" if x != 0.0 else "0 €")
            disp_df["TCO (Total Cost of Ownership)"] = disp_df["TCO (Total Cost of Ownership)"].apply(lambda x: f"{x:,.0f} €")
            disp_df["LCOE"] = disp_df["LCOE"].apply(lambda x: f"{x:.4f} €/kWh")
            st.dataframe(disp_df, use_container_width=True, hide_index=True)
            
        with col2:
            st.markdown(f"### Cumulative Cashflow ({lifespan} Years)")
            fig_cf.update_layout(height=400, hovermode="x unified", xaxis_title="Years", yaxis_title="Cashflow (€)", margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_cf, use_container_width=True)
            
        st.divider()
        st.markdown("### Detailed Year-by-Year Cashflows")
        
        if not detailed_tables:
            st.info("No scenarios with financial data are available for comparison.")
        else:
            view_mode = st.radio(
                "Comparison Mode:",
                ["Single Scenario Details", "Compare Metric across Scenarios"],
                horizontal=True,
                key="tab3_cashflow_view_mode"
            )
            
            variant_names = list(detailed_tables.keys())
            
            if "Single Scenario Details" in view_mode:
                selected_var = st.selectbox(
                    "Select Scenario to view detailed cashflow table:",
                    variant_names,
                    key="tab3_selected_var_detail"
                )
                if selected_var in detailed_tables:
                    df_cf = pd.DataFrame(detailed_tables[selected_var])
                    st.dataframe(
                        df_cf.style.format({col: "{:,.0f} €" for col in df_cf.columns if "€" in col or "PV" in col or "Value" in col or "NPV" in col}),
                        use_container_width=True, hide_index=True
                    )
            else:
                first_df = pd.DataFrame(next(iter(detailed_tables.values())))
                cols_to_compare = [col for col in first_df.columns if col != "Year"]
                
                selected_col = st.selectbox(
                    "Select Financial Metric to compare across all scenarios:",
                    cols_to_compare,
                    key="tab3_selected_col_comparison"
                )
                
                comparison_data = {"Year": first_df["Year"]}
                for t_name in variant_names:
                    df_cf = pd.DataFrame(detailed_tables[t_name])
                    if selected_col in df_cf.columns:
                        comparison_data[t_name] = df_cf[selected_col]
                        
                comp_df = pd.DataFrame(comparison_data)
                st.dataframe(
                    comp_df.style.format({col: "{:,.0f} €" for col in comp_df.columns if col != "Year"}),
                    use_container_width=True, hide_index=True
                )
