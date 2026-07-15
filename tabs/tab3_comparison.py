# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from logic.storage_manager import get_all_base_scenarios
from tabs.tab3_components.financial_engine import generate_15_year_cashflow, get_payback_year
from tabs.tab3_components.tarrif_calc import render_tariff_builder_ui

def render_tab3_comparison():
    st.write("## Advanced Comparison Suite")
    
    bases = get_all_base_scenarios()
    if not bases:
        st.warning("No saved Scenarios found. Please create a Baseline in Tab 1.")
        return
        
    base_options = [b.name for b in bases]
    st.write("### 1. Select the Base Scenario")
    selected_base_name = st.selectbox("Baseline Reference Profile:", options=base_options)
    
    selected_base_obj = next((b for b in bases if b.name == selected_base_name), None)
    
    if not selected_base_obj or selected_base_obj.original_profile is None:
        st.info("No data in this baseline yet. Please process data in Tab 1.")
        return

    linked_subs = selected_base_obj.sub_scenarios
    sub_names = [sub.name for sub in linked_subs]
    
    auto_compare = False
    if sub_names:
        st.success(f"{len(sub_names)} associated variants found for '{selected_base_name}'!")
        auto_compare = st.checkbox("Automatically overlay all associated sub-scenarios", value=True)

    all_options = [selected_base_name] + sub_names
    default_selection = [selected_base_name]
    if auto_compare:
        default_selection.extend(sub_names)
        
    selected_profiles = st.multiselect("Active Scenarios in Comparison:", options=all_options, default=default_selection)

    if not selected_profiles:
        st.warning("Please choose at least one scenario for the comparison.")
        return

    def get_df_for_name(name):
        if name == selected_base_name:
            return selected_base_obj.original_profile
        else:
            sub = next((s for s in linked_subs if s.name == name), None)
            return sub.simulated_profile if sub else None

    # --- 1. THE VISUAL GRAPH OVERLAY ---
    st.write("### Load Profile Overlay")
    fig = go.Figure()
    
    for name in selected_profiles:
        df = get_df_for_name(name)
        if df is not None and not df.empty:
            is_base = (name == selected_base_name)
            l_width = 3 if is_base else 1.5
            l_color = "#333333" if is_base else None 
            
            # Robustes Auslesen der Spalten (verhindert leere Diagramme)
            y_col = 'final_grid_load_kw'
            if y_col not in df.columns:
                y_col = 'consumption_kw'
            if y_col not in df.columns:
                y_col = df.columns[-1] # Absoluter Fallback
                
            x_col = df['timestamp'] if 'timestamp' in df.columns else df.index
            
            fig.add_trace(go.Scatter(
                x=x_col, y=df[y_col],
                mode='lines',
                line=dict(width=l_width, color=l_color),
                name=f"🏢 {name} (Base)" if is_base else f"🌿 {name}"
            ))
            
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Power (kW)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. THE TECHNICAL COMPARISON MATRIX ---
    if len(selected_profiles) >= 1:
        st.write("### Technical Comparison Matrix")
        
        comparison_rows = []
        base_df = selected_base_obj.original_profile
        base_limit = selected_base_obj.base_tariff.contracted_capacity_kw
        base_peak = base_df['consumption_kw'].max() if 'consumption_kw' in base_df.columns else base_df.iloc[:, 1].max()
        
        base_limit_str = f"{base_limit:.1f} kW" if base_limit < 99000 else "Unlimited"
        base_margin = base_limit - base_peak
        
        if base_limit >= 99000:
            base_margin_str = "Unlimited"
            base_avail_str = "Unlimited"
            base_feasibility = "✅ Yes"
        else:
            base_margin_str = f"{base_margin:.1f} kW"
            base_avail_str = f"{max(0.0, base_margin):.1f} kW"
            base_feasibility = "Yes" if base_peak <= base_limit else "No"
            
        comparison_rows.append({
            "Scenario Name": f"{selected_base_obj.name} (Base)",
            "Grid Connection": selected_base_obj.base_tariff.name,
            "Grid Capacity": base_limit_str,
            "Battery Power": "NONE",
            "New Peak": f"{base_peak:.1f} kW",
            "Safety Margin": base_margin_str,
            "Available Power": base_avail_str,
            "Technically Sufficient?": base_feasibility
        })
        
        for name in selected_profiles:
            if name == selected_base_name:
                continue
                
            sub_obj = next((s for s in linked_subs if s.name == name), None)
            if not sub_obj:
                continue
                
            sub_df = sub_obj.simulated_profile
            sub_limit = sub_obj.custom_tariff.contracted_capacity_kw if sub_obj.custom_tariff else base_limit
            
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in sub_df.columns else 'consumption_kw'
            sub_peak = sub_df[y_col].max()
            
            sub_limit_str = f"{sub_limit:.1f} kW" if sub_limit < 99000 else "Unlimited"
            sub_margin = sub_limit - sub_peak
            
            if sub_limit >= 99000:
                sub_margin_str = "Unlimited"
                sub_avail_str = "Unlimited"
                sub_feasibility = "✅ Yes"
            else:
                sub_margin_str = f"{sub_margin:.1f} kW"
                sub_avail_str = f"{max(0.0, sub_margin):.1f} kW"
                sub_feasibility = "Yes" if sub_peak <= sub_limit else "No"
                
            b_str = f"{sub_obj.battery_kwh:.1f} kWh / {sub_obj.battery_kw:.1f} kW" if sub_obj.battery_kwh > 0 else "NONE"
            t_name = sub_obj.custom_tariff.name if sub_obj.custom_tariff else selected_base_obj.base_tariff.name
            
            comparison_rows.append({
                "Scenario Name": f"{sub_obj.name}",
                "Grid Connection": t_name,
                "Grid Capacity": sub_limit_str,
                "Battery Power": b_str,
                "New Peak": f"{sub_peak:.1f} kW",
                "Safety Margin": sub_margin_str,
                "Available Power": sub_avail_str,
                "Technically Sufficient?": sub_feasibility
            })
            
        st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
            
        if st.session_state.get('enable_financials', False):
            # --- 3. THE CFO FINANCIAL DASHBOARD ---
            st.divider()
            render_tariff_builder_ui()
            st.divider()
            
            active_subs = [s for s in linked_subs if s.name in selected_profiles]
            render_cfo_cockpit_from_classes(selected_base_obj, active_subs)
        
        # --- 4. PROFESSIONAL PDF EXPORTER ---
        st.divider()
        from tabs.tab3_components.pdf_comparison_export import render_comparison_pdf_downloader
        render_comparison_pdf_downloader(selected_base_obj, selected_profiles, linked_subs)

def render_cfo_cockpit_from_classes(base_scenario, selected_subs):
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
                from tabs.tab3_components.financial_engine import calculate_irr
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
        
        variant_names = list(detailed_tables.keys())
        ui_tabs = st.tabs([f"{n}" for n in variant_names])
        for idx, t_name in enumerate(variant_names):
            with ui_tabs[idx]:
                df_cf = pd.DataFrame(detailed_tables[t_name])
                st.dataframe(
                    df_cf.style.format({col: "{:,.0f} €" for col in df_cf.columns if "€" in col or "PV" in col or "Value" in col or "NPV" in col}),
                    use_container_width=True, hide_index=True
                )