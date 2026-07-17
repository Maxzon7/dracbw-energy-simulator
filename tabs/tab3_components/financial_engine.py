# tabs/tab3_components/financial_engine.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from classes.models import BaseScenario, SubScenario

def calculate_irr(cashflows: list, max_iter: int = 1000, tolerance: float = 1e-6) -> float:
    """
    Calculates the Internal Rate of Return (IRR) using the bisection method.
    Returns -1.0 if it doesn't converge or lacks a single sign change.
    """
    # Check if there is at least one positive and one negative cashflow
    has_pos = any(cf > 0 for cf in cashflows)
    has_neg = any(cf < 0 for cf in cashflows)
    if not (has_pos and has_neg):
        return -1.0
        
    def npv_f(r):
        return sum(cf / ((1.0 + r) ** t) for t, cf in enumerate(cashflows))
        
    # Search bounds for r
    low = -0.99
    high = 5.0
    
    f_low = npv_f(low)
    f_high = npv_f(high)
    
    if f_low * f_high > 0:
        # Search for a sign change
        step = 0.5
        found = False
        for _ in range(20):
            high += step
            f_high = npv_f(high)
            if f_low * f_high < 0:
                found = True
                break
        if not found:
            return -1.0
            
    # Bisection search
    for _ in range(max_iter):
        mid = (low + high) / 2.0
        f_mid = npv_f(mid)
        if abs(f_mid) < tolerance:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
            
    return (low + high) / 2.0

def render_financial_dashboard(selected_profiles: list, selected_base: str, vault: dict):
    """
    Dynamically calculates and visualizes project lifespan cashflows, ROI, LCOE, and TCO.
    Supports interactive Sensitivity Analysis and Scenario Ranking.
    """
    # Guard check: Ensure financials are enabled
    if not st.session_state.get('enable_financials', False):
        return

    st.write("### Executive Financial Dashboard (DCF & ROI Analysis)")
    
    # 1. Unpack Baseline reference
    base_data = vault[selected_base]
    base_df = base_data['df']
    base_fin = base_data.get('params', {}).get('financial_metadata', {})
    
    if not base_fin or not base_fin.get('lifespan_years'):
        st.info("Please set up the Baseline Financial data in Tab 1 first.")
        return

    # Extract global variables
    lifespan = int(base_fin.get('lifespan_years', 15))
    e_price = float(base_fin.get('energy_price_normal_per_kwh', 0.25))
    p_price = float(base_fin.get('contracted_capacity_fee_per_kw_year', 0.0)) + (float(base_fin.get('peak_capacity_fee_per_kw_month', 0.0)) * 12.0)
    base_grid_capex = float(base_fin.get('baseline_grid_capex', 0.0))
    fit = float(base_fin.get('feed_in_tariff', 0.08))
    diesel_price = float(base_fin.get('diesel_price', 1.50))
    
    inflation_rate = float(base_fin.get('inflation', 3.0)) / 100.0
    energy_price_growth = float(base_fin.get('energy_price_growth', 4.0)) / 100.0
    diesel_price_growth = float(base_fin.get('diesel_price_growth', 2.0)) / 100.0
    
    res = base_data.get('params', {}).get('resolution', 15)
    factor = 60 / res
    
    # Baseline BAU inputs
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    
    col_info, col_wacc = st.columns([2, 1])
    with col_info:
        st.info(f"Discounted Cash Flow (DCF) projection over a **{lifespan}-Year Lifespan** factoring CAPEX, OPEX, grid tariffs, fuel costs, and escalation.")
    with col_wacc:
        discount_rate = st.number_input(
            "Discount Rate / WACC (%)", 
            value=5.0, step=0.5, 
            key="wacc_input",
            help="Used to discount future cashflows to calculate the Net Present Value (NPV)."
        ) / 100.0

    # Sensitivity inputs in expander
    with st.expander("📊 Sensitivity Analysis Settings", expanded=False):
        st.write("Simulate changes in core economic factors to test scenario robustness:")
        sens_col1, sens_col2, sens_col3 = st.columns(3)
        capex_mult = sens_col1.slider("CAPEX Variation (%)", -20, 20, 0, step=5, key="sens_capex_var") / 100.0 + 1.0
        energy_inf_add = sens_col2.slider("Additional Energy Escalation (%/Yr)", -3.0, 5.0, 0.0, step=0.5, key="sens_energy_inf") / 100.0
        fuel_inf_add = sens_col3.slider("Additional Fuel Escalation (%/Yr)", -3.0, 5.0, 0.0, step=0.5, key="sens_fuel_inf") / 100.0

    # Apply Sensitivity variations
    active_energy_growth = energy_price_growth + energy_inf_add
    active_diesel_growth = diesel_price_growth + fuel_inf_add

    # Calculate Baseline BAU cashflows
    # BAU CAPEX = base_grid_capex at Year 0
    discounted_energy_sum = 0.0
    base_tco = base_grid_capex
    
    # Calculate Year 1 Baseline cost
    base_grid_bill_y1 = (base_kwh * e_price) + (base_peak * p_price)
    
    for y in range(1, lifespan + 1):
        grid_multiplier = (1.0 + active_energy_growth) ** (y - 1)
        discount_multiplier = (1.0 + discount_rate) ** y
        
        bill_y = base_grid_bill_y1 * grid_multiplier
        base_tco += bill_y / discount_multiplier
        discounted_energy_sum += base_kwh / discount_multiplier
        
    base_lcoe = base_tco / discounted_energy_sum if discounted_energy_sum > 0 else 0.0

    fig = go.Figure()
    fig.add_hline(y=0, line_color="rgba(100,100,100,0.5)", line_width=1, line_dash="dash")
    
    summary_rows = []
    detailed_tables = {}
    
    # Add Baseline TCO reference curve
    base_cf_plot = [base_grid_capex]
    base_cum_cost = base_grid_capex
    for y in range(1, lifespan + 1):
        grid_multiplier = (1.0 + active_energy_growth) ** (y - 1)
        bill_y = base_grid_bill_y1 * grid_multiplier
        base_cum_cost += bill_y
        base_cf_plot.append(-base_cum_cost)
        
    # Standardised DCF loops for each Variant Scenario
    for name in selected_profiles:
        if name == selected_base:
            continue
            
        scen = vault[name]
        sub_df = scen['df']
        hw_params = scen.get('params', {}).get('hardware_params', {})
        
        # CAPEX/OPEX structures
        capex_raw = hw_params.get('total_capex', 0)
        opex_pct = hw_params.get('opex_pct', 0) / 100.0
        degradation_pct = hw_params.get('degradation_pct', 0) / 100.0
        
        # Extract dynamic replacements
        rep_year = 99
        rep_base_cost = 0.0
        gen_rent = 0.0
        gen_maint_hr = 0.0
        
        if capex_raw > 0: # Isolated Scenario
            capex = capex_raw * capex_mult
            opex_yr1 = capex * opex_pct
            if 'replacement_year' in hw_params:
                rep_year = hw_params.get('replacement_year', 10)
                rep_pct = hw_params.get('replacement_pct', 100.0) / 100.0
                rep_base_cost = hw_params.get('total_storage_capex', 0) * rep_pct
            gen_params = hw_params.get('generator', {})
            gen_rent = float(gen_params.get('capex_per_year', 0.0))
            gen_maint_hr = float(gen_params.get('opex_per_hour', 0.0))
            
        else: # Combined Cascading configurations
            c1 = hw_params.get('solar', {}).get('total_capex', 0)
            c2 = hw_params.get('battery', {}).get('total_capex', 0)
            o1 = c1 * (hw_params.get('solar', {}).get('opex_pct', 0) / 100.0)
            o2 = c2 * (hw_params.get('battery', {}).get('opex_pct', 0) / 100.0)
            d1 = hw_params.get('solar', {}).get('degradation_pct', 0) / 100.0
            d2 = hw_params.get('battery', {}).get('degradation_pct', 0) / 100.0
            
            capex = (c1 + c2) * capex_mult
            opex_yr1 = (o1 + o2) * capex_mult
            
            if capex_raw > 0:
                degradation_pct = ((c1 * d1) + (c2 * d2)) / capex_raw
            else:
                degradation_pct = 0.0
                
            bat_params = hw_params.get('battery', {})
            rep_year = bat_params.get('replacement_year', 99)
            rep_pct = bat_params.get('replacement_pct', 100.0) / 100.0
            rep_base_cost = bat_params.get('total_storage_capex', 0) * rep_pct
            
            gen_params = hw_params.get('generator', {})
            gen_rent = float(gen_params.get('capex_per_year', 0.0))
            gen_maint_hr = float(gen_params.get('opex_per_hour', 0.0))

        if capex == 0 and gen_rent == 0:
            continue # Skip non-investments
            
        # Year 1 operational calculations
        sub_kwh = sub_df['final_grid_load_kw'].clip(lower=0.0).sum() / factor
        sub_peak = sub_df['final_grid_load_kw'].max()
        sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0.0])).sum() / factor
        
        sub_grid_bill_yr1 = (sub_kwh * e_price) + (sub_peak * p_price) - (sub_export * fit)
        grid_savings_yr1 = base_grid_bill_y1 - sub_grid_bill_yr1
        
        # Generator O&M & Fuel calculations
        annual_fuel_l = sub_df.get('generator_fuel_l', pd.Series([0.0])).sum()
        fuel_cost_yr1 = annual_fuel_l * diesel_price
        
        gen_action = sub_df.get('generator_action_kw', pd.Series([0.0]))
        run_hours = (gen_action > 0.1).sum()
        gen_maint_yr1 = run_hours * gen_maint_hr
        
        # Build cashflows tables
        cf_table = []
        net_year0 = base_grid_capex - capex
        cum_cf = net_year0
        cum_npv = net_year0
        
        cf_table.append({
            "Year": 0, 
            "CAPEX (€)": round(-capex, 2), 
            "OPEX (€)": 0.0, 
            "Generator Fuel (€)": 0.0,
            "Generator Rental (€)": 0.0,
            "Generator Maintenance (€)": 0.0,
            "Grid Savings (€)": round(base_grid_capex, 2),
            "Net Cashflow (€)": round(net_year0, 2), 
            "Cumulative Cashflow (€)": round(cum_cf, 2), 
            "Present Value (€)": round(net_year0, 2), 
            "Cumulative NPV (€)": round(cum_npv, 2)
        })
        
        sub_tco = capex
        break_even_yr = 0 if cum_cf >= 0 else "> lifespan"
        cashflow_series_list = [net_year0]
        
        for y in range(1, lifespan + 1):
            infl_multiplier = (1.0 + inflation_rate) ** (y - 1)
            deg_multiplier = (1.0 - degradation_pct) ** (y - 1)
            
            grid_multiplier = (1.0 + active_energy_growth) ** (y - 1)
            fuel_multiplier = (1.0 + active_diesel_growth) ** (y - 1)
            discount_multiplier = (1.0 + discount_rate) ** y
            
            sav_y = grid_savings_yr1 * grid_multiplier * deg_multiplier
            opx_y = opex_yr1 * infl_multiplier
            fuel_y = fuel_cost_yr1 * fuel_multiplier
            gen_rent_y = gen_rent * infl_multiplier
            gen_maint_y = gen_maint_yr1 * infl_multiplier
            
            rep_y = 0.0
            if y == rep_year:
                rep_y = rep_base_cost * infl_multiplier
                
            net_y = sav_y - opx_y - fuel_y - gen_rent_y - gen_maint_y - rep_y
            cum_cf += net_y
            cashflow_series_list.append(net_y)
            
            pv_y = net_y / discount_multiplier
            cum_npv += pv_y
            
            # TCO elements sum (discounted costs)
            annual_net_cost = sub_grid_bill_yr1 * grid_multiplier + opx_y + fuel_y + gen_rent_y + gen_maint_y + rep_y - sub_export * fit * grid_multiplier
            sub_tco += annual_net_cost / discount_multiplier
            
            cf_table.append({
                "Year": y, 
                "CAPEX (€)": round(-rep_y, 2),
                "OPEX (€)": round(-opx_y, 2), 
                "Generator Fuel (€)": round(-fuel_y, 2),
                "Generator Rental (€)": round(-gen_rent_y, 2),
                "Generator Maintenance (€)": round(-gen_maint_y, 2),
                "Grid Savings (€)": round(sav_y, 2), 
                "Net Cashflow (€)": round(net_y, 2), 
                "Cumulative Cashflow (€)": round(cum_cf, 2), 
                "Present Value (€)": round(pv_y, 2), 
                "Cumulative NPV (€)": round(cum_npv, 2)
            })
            
            if break_even_yr == "> lifespan" and cum_cf >= 0:
                break_even_yr = y
                
        # Calculate IRR
        irr_val = calculate_irr(cashflow_series_list)
        irr_str = f"{irr_val*100.0:.2f} %" if irr_val > -0.9 else "N/A"
        
        # Calculate LCOE
        lcoe_val = sub_tco / discounted_energy_sum if discounted_energy_sum > 0 else 0.0
        
        # Save financials to vault
        vault[name]['financial_metrics'] = {
            "discount_rate_used": discount_rate,
            "roi_years": break_even_yr,
            "net_present_value": cum_npv,
            "total_15y_profit": cum_cf,
            "tco": sub_tco,
            "lcoe": lcoe_val,
            "irr": irr_val,
            "cashflow_series": cf_table
        }
        
        # Plot cumulative cashflow
        plot_y = [row["Cumulative Cashflow (€)"] for row in cf_table]
        fig.add_trace(go.Scatter(
            x=list(range(lifespan + 1)), y=plot_y, mode='lines+markers', name=name,
            hovertemplate="Year %{x}<br>Cashflow: %{y:,.0f} €"
        ))
        
        # Create row object
        summary_rows.append({
            "Scenario": name,
            "NPV (Net Present Value)": cum_npv,
            "TCO (Total Cost of Ownership)": sub_tco,
            "LCOE (€/kWh)": lcoe_val,
            "IRR": irr_str,
            "Payback Period": break_even_yr,
            "Initial CAPEX": capex,
            "Year 1 Net Savings": grid_savings_yr1 - opex_yr1 - fuel_cost_yr1 - gen_rent - gen_maint_yr1,
            "Fuel Penalty (Y1)": fuel_cost_yr1 + gen_maint_yr1
        })
        
        detailed_tables[name] = cf_table
        
    # Render graphs & tables
    if summary_rows:
        # Create baseline BAU summary row
        summary_rows.append({
            "Scenario": f"{selected_base} (Baseline BAU)",
            "NPV (Net Present Value)": 0.0,
            "TCO (Total Cost of Ownership)": base_tco,
            "LCOE (€/kWh)": base_lcoe,
            "IRR": "Baseline Ref",
            "Payback Period": "Baseline Ref",
            "Initial CAPEX": base_grid_capex,
            "Year 1 Net Savings": 0.0,
            "Fuel Penalty (Y1)": 0.0
        })
        
        # Sort/Rank based on NPV (descending) or TCO (ascending)
        summary_df = pd.DataFrame(summary_rows)
        # Sort scenario rows so variants with higher NPV appear first, BAU at bottom
        summary_df["sorting_key"] = summary_df["NPV (Net Present Value)"].apply(lambda x: x if x is not None else -9999999.0)
        summary_df = summary_df.sort_values(by="sorting_key", ascending=False).drop(columns=["sorting_key"])
        
        fig.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Operating Year", yaxis_title="Cumulative Net Cashflow (€)",
            hovermode="x unified", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("#### Financial Performance Summary & Rankings")
        # Format df columns
        disp_df = summary_df.copy()
        disp_df["NPV (Net Present Value)"] = disp_df["NPV (Net Present Value)"].apply(lambda x: f"{x:,.0f} €" if x != 0.0 else "0 €")
        disp_df["TCO (Total Cost of Ownership)"] = disp_df["TCO (Total Cost of Ownership)"].apply(lambda x: f"{x:,.0f} €")
        disp_df["LCOE (€/kWh)"] = disp_df["LCOE (€/kWh)"].apply(lambda x: f"{x:.4f} €/kWh")
        disp_df["Initial CAPEX"] = disp_df["Initial CAPEX"].apply(lambda x: f"{x:,.0f} €")
        disp_df["Year 1 Net Savings"] = disp_df["Year 1 Net Savings"].apply(lambda x: f"{x:,.0f} €" if x != 0.0 else "N/A")
        disp_df["Fuel Penalty (Y1)"] = disp_df["Fuel Penalty (Y1)"].apply(lambda x: f"{x:,.0f} €" if x != 0.0 else "0 €")
        
        st.dataframe(disp_df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.write("#### Detailed Year-by-Year Cashflow Tables")
        
        variant_names = list(detailed_tables.keys())
        ui_tabs = st.tabs([f"{n}" for n in variant_names])
        
        for idx, t_name in enumerate(variant_names):
            with ui_tabs[idx]:
                df_cf = pd.DataFrame(detailed_tables[t_name])
                st.dataframe(
                    df_cf.style.format({col: "{:,.0f} €" for col in df_cf.columns if "€" in col or "PV" in col or "Value" in col or "NPV" in col}),
                    use_container_width=True, hide_index=True
                )
    else:
        st.warning("Please configure and select at least one hardware variant (with CAPEX configured) to view the financial ROI analysis.")


def calculate_annual_grid_bill_with_pillars(df, fin_params):
    """
    Calculates the exact annual grid bill using either:
      - A volatile monthly schedule if "monthly_tariff_schedule" is in fin_params.
      - The standard static 4-pillar parameters otherwise.
    """
    temp_df = df.copy()
    
    # Identify resolution and group by month
    if 'timestamp' in temp_df.columns:
        temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
        temp_df['month'] = temp_df['timestamp'].dt.month
        try:
            delta = temp_df['timestamp'].iloc[1] - temp_df['timestamp'].iloc[0]
            factor = 60 / (delta.seconds / 60)
        except:
            factor = 4.0
    else:
        res = len(temp_df) / 8760
        pts_per_month = int(730 * res)
        temp_df['month'] = (temp_df.index // pts_per_month) + 1
        temp_df['month'] = temp_df['month'].clip(upper=12)
        factor = 4.0 if len(temp_df) == 35040 else 1.0

    load_col = 'final_grid_load_kw' if 'final_grid_load_kw' in temp_df.columns else 'consumption_kw'
    
    # Check if we have a monthly tariff schedule
    monthly_schedule = fin_params.get('monthly_tariff_schedule', {})
    
    if monthly_schedule:
        total_annual_gross = 0.0
        
        def is_hour_in_range(hour, start, end):
            if start == end:
                return False
            if start < end:
                return start <= hour < end
            else:
                return (hour >= start) | (hour < end)
                
        for m in range(1, 13):
            m_mask = temp_df['month'] == m
            m_df = temp_df[m_mask]
            if len(m_df) == 0:
                continue
                
            m_peak = m_df[load_col].max()
            
            # Lookup month params
            m_data = monthly_schedule.get(str(m), {}) or monthly_schedule.get(m, {})
            if not m_data:
                m_data = monthly_schedule.get('1', {}) or monthly_schedule.get(1, {})
                
            base_fee = float(m_data.get('base_fee', 0.0) or 0.0)
            contracted_kw = float(m_data.get('contracted_capacity_kw', 0.0) or 0.0)
            contract_price = float(m_data.get('contracted_capacity_price', 0.0) or 0.0)
            peak_penalty_price = float(m_data.get('peak_penalty_price', 0.0) or 0.0)
            excess_price = float(m_data.get('excess_penalty_price', 0.0) or 0.0)
            tax_pct = float(m_data.get('tax_pct', 0.0) or 0.0)
            local_tax_pct = float(m_data.get('local_tax_pct', 0.0) or 0.0)
            subsidy = float(m_data.get('subsidy_amount', 0.0) or 0.0)
            
            alta_price = float(m_data.get('alta', {}).get('price', 0.0) or 0.0)
            alta_start = int(m_data.get('alta', {}).get('start_hour', 18))
            alta_end = int(m_data.get('alta', {}).get('end_hour', 23))
            
            baja_price = float(m_data.get('baja', {}).get('price', 0.0) or 0.0)
            baja_start = int(m_data.get('baja', {}).get('start_hour', 23))
            baja_end = int(m_data.get('baja', {}).get('end_hour', 5))
            
            resto_price = float(m_data.get('resto', {}).get('price', 0.0) or 0.0)
            
            # 1. Fixed & capacity costs
            m_fixed_cap = base_fee + (contracted_kw * contract_price)
            
            # 2. Peak penalty cost (Consumo de Potencia)
            # Calculated based on Pico-Peak if TOU is enabled, else absolute peak
            enable_tou = bool(m_data.get('enable_tou', True))
            pico_peak = m_peak
            if enable_tou and 'timestamp' in m_df.columns:
                m_df_copy = m_df.copy()
                m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                pico_df = m_df_copy[alta_mask]
                if len(pico_df) > 0:
                    pico_peak = pico_df[load_col].max()
                    
            m_peak_penalty = pico_peak * peak_penalty_price
            
            # 3. Excess penalty cost (Exceso de Potencia)
            m_excess = 0.0
            if m_peak > contracted_kw:
                m_excess = (m_peak - contracted_kw) * excess_price
                
            # 4. Energy cost segmented by time zones
            m_energy_cost = 0.0
            if 'timestamp' in m_df.columns:
                m_df_copy = m_df.copy()
                m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                
                alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                baja_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, baja_start, baja_end))
                resto_mask = ~(alta_mask | baja_mask)
                
                e_alta = m_df_copy[alta_mask][load_col].sum() / factor
                e_baja = m_df_copy[baja_mask][load_col].sum() / factor
                e_resto = m_df_copy[resto_mask][load_col].sum() / factor
                
                m_energy_cost = (e_alta * alta_price) + (e_baja * baja_price) + (e_resto * resto_price)
            else:
                total_kwh = m_df[load_col].sum() / factor
                m_energy_cost = total_kwh * resto_price
                
            net_monthly = m_fixed_cap + m_peak_penalty + m_excess + m_energy_cost - subsidy
            
            # Taxes & custom adjustments
            provincial_taxes = m_data.get('provincial_taxes', [])
            custom_adjustments = m_data.get('custom_adjustments', [])
            
            pre_tax_adj = 0.0
            post_tax_adj = 0.0
            for adj in custom_adjustments:
                amt = float(adj.get('Amount (€)', adj.get('amount', 0.0)) or 0.0)
                is_pre = bool(adj.get('Is Pre-tax', adj.get('is_pre_tax', False)))
                if is_pre:
                    pre_tax_adj += amt
                else:
                    post_tax_adj += amt
            
            net_with_pre_tax = net_monthly + pre_tax_adj
            
            # Calculate VAT and all Provincial Taxes
            tax_sum = net_with_pre_tax * (tax_pct / 100.0)
            for p_tax in provincial_taxes:
                rate = float(p_tax.get('Rate (%)', p_tax.get('rate', 0.0)) or 0.0)
                tax_sum += net_with_pre_tax * (rate / 100.0)
            
            # Calculate gross
            gross_monthly = net_with_pre_tax + tax_sum
            
            # Apply post-tax adjustments
            gross_monthly = gross_monthly + post_tax_adj
            
            # Legacy stabilization_credit fallback
            stabilization_credit = float(m_data.get('stabilization_credit', 0.0) or 0.0)
            gross_monthly = max(0.0, gross_monthly - stabilization_credit)
            
            total_annual_gross += gross_monthly
            
        return total_annual_gross
        
    else:
        if 'timestamp' in temp_df.columns:
            temp_df['is_normal'] = (temp_df['timestamp'].dt.dayofweek < 5) & (temp_df['timestamp'].dt.hour >= 7) & (temp_df['timestamp'].dt.hour < 23)
        else:
            temp_df['is_normal'] = True
            
        monthly_peaks = temp_df.groupby('month')[load_col].max()
        
        fixed_conn = float(fin_params.get('fixed_annual_connection_fee', 0.0) or 0.0)
        fixed_trans = float(fin_params.get('fixed_annual_transport_fee', 0.0) or 0.0)
        contracted_kw = float(fin_params.get('contracted_capacity_kw', 0.0) or 0.0)
        contract_price_yr = float(fin_params.get('contracted_capacity_fee_per_kw_year', 0.0) or 0.0)
        peak_price_mo = float(fin_params.get('peak_capacity_fee_per_kw_month', 0.0) or 0.0)
        
        energy_price_norm = float(fin_params.get('energy_price_normal_per_kwh', 0.0) or 0.0)
        energy_price_laag = float(fin_params.get('energy_price_laag_per_kwh', 0.0) or 0.0)
        
        annual_fixed = fixed_conn + fixed_trans + (contracted_kw * contract_price_yr)
        annual_peak = monthly_peaks.sum() * peak_price_mo
        
        annual_excess = 0.0
        contract_price_mo = contract_price_yr / 12.0
        if contracted_kw > 0 and contract_price_mo > 0:
            for m, peak in monthly_peaks.items():
                if peak > contracted_kw:
                    annual_excess += (peak - contracted_kw) * contract_price_mo
                    
        energy_normal = temp_df[temp_df['is_normal']][load_col].sum() / factor
        energy_laag = temp_df[~temp_df['is_normal']][load_col].sum() / factor if 'is_normal' in temp_df.columns else 0.0
        annual_energy = (energy_normal * energy_price_norm) + (energy_laag * energy_price_laag)
        
        net_total = annual_fixed + annual_peak + annual_excess + annual_energy
        
        vat_pct = float(fin_params.get('national_vat_pct', 0.0) or 0.0)
        local_pct = float(fin_params.get('local_tax_pct', 0.0) or 0.0)
        gross_total = net_total * (1.0 + (vat_pct + local_pct) / 100.0)
        
        return gross_total


def generate_15_year_cashflow(sub_scenario: SubScenario, base_scenario: BaseScenario, discount_rate: float = 0.05, capex_mult: float = 1.0, energy_esc_add: float = 0.0, diesel_esc_add: float = 0.0) -> pd.DataFrame:
    """
    Calculates year-by-year cashflow series comparing sub-scenario configurations against the baseline.
    Returns None if financials are not active (financials is None).
    """
    if not sub_scenario.financials:
        return None 
        
    fin = sub_scenario.financials
    lifespan = fin.lifespan_years
    inflation_rate = fin.inflation_rate
    
    # Safely unpack escalations
    energy_esc = getattr(fin, 'energy_price_growth', 0.04)
    if energy_esc > 1.0:
        energy_esc /= 100.0
    elif energy_esc == 0.0:
        energy_esc = 0.04
    energy_esc += energy_esc_add
        
    diesel_esc = getattr(fin, 'diesel_price_growth', 0.02)
    if diesel_esc > 1.0:
        diesel_esc /= 100.0
    elif diesel_esc == 0.0:
        diesel_esc = 0.02
    diesel_esc += diesel_esc_add
        
    # Extract baseline profile and simulated profiles
    base_df = base_scenario.original_profile
    sub_df = sub_scenario.simulated_profile
    
    if len(base_df) > 0:
        factor = 4.0 if len(base_df) > 15000 else 1.0
    else:
        factor = 1.0
        
    # Year 1 Baseline grid costs
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    base_tariff = base_scenario.base_tariff
    
    # Calculate grid limit CAPEX/avoided baseline
    fin_meta = base_scenario.metadata.get('financial_metadata', {})
    base_grid_capex = float(fin_meta.get('baseline_grid_capex', 0.0))
    fit = float(fin_meta.get('feed_in_tariff', 0.08))
    diesel_price = float(fin_meta.get('diesel_price', 1.50))
    
    # Calculate exact baseline grid bill using pillars
    base_grid_bill = calculate_annual_grid_bill_with_pillars(base_df, fin_meta)
    
    # Year 1 Sub-Scenario grid costs (including custom tariff overrides)
    sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0.0])).sum() / factor
    
    # Parse sub-scenario financial/grid parameters
    if sub_scenario.tech_params and 'grid' in sub_scenario.tech_params and 'data' in sub_scenario.tech_params['grid']:
        sub_fin_params = sub_scenario.tech_params['grid']['data'].copy()
        if 'contracted_capacity_kw' not in sub_fin_params:
            sub_fin_params['contracted_capacity_kw'] = sub_scenario.tech_params['grid'].get('new_grid_limit_kw', 100.0)
    else:
        sub_fin_params = fin_meta.copy()
        if sub_scenario.tech_params and 'grid' in sub_scenario.tech_params:
            sub_fin_params['contracted_capacity_kw'] = sub_scenario.tech_params['grid'].get('new_grid_limit_kw', 100.0)
            
    sub_grid_bill = calculate_annual_grid_bill_with_pillars(sub_df, sub_fin_params) - (sub_export * fit)
    
    # Backup generator costs
    annual_fuel_l = sub_df.get('generator_fuel_l', pd.Series([0.0])).sum()
    fuel_cost_yr1 = annual_fuel_l * diesel_price
    
    gen_params = sub_scenario.tech_params.get('generator', {}) if sub_scenario.tech_params else {}
    gen_rent = float(gen_params.get('capex_per_year', 0.0))
    gen_maint_hr = float(gen_params.get('opex_per_hour', 0.0))
    
    gen_action = sub_df.get('generator_action_kw', pd.Series([0.0]))
    run_hours = (gen_action > 0.1).sum()
    gen_maint_yr1 = run_hours * gen_maint_hr
    
    grid_savings_yr1 = base_grid_bill - sub_grid_bill
    
    # Lifespan cashflow simulation
    jahre = list(range(lifespan + 1))
    df = pd.DataFrame({"Year": jahre})
    
    df["CAPEX (€)"] = 0.0
    df.loc[df["Year"] == 0, "CAPEX (€)"] = -fin.capex * capex_mult
    
    # Unpack BESS details for replacement moment capex
    bess_params = sub_scenario.tech_params.get('battery', {}) if sub_scenario.tech_params else {}
    rep_year = bess_params.get('replacement_year', 10) if bess_params else 10
    rep_pct = bess_params.get('replacement_pct', 100.0) / 100.0 if bess_params else 1.0
    rep_cost_base = bess_params.get('total_storage_capex', 0.0) * rep_pct * capex_mult if bess_params else 0.0
    
    opex_liste = [0.0]
    ersparnis_liste = [0.0]
    fuel_liste = [0.0]
    miete_liste = [0.0]
    maintenance_liste = [0.0]
    capex_replacements = [0.0]
    
    for jahr in range(1, lifespan + 1):
        infl_multiplier = (1.0 + inflation_rate) ** (jahr - 1)
        grid_multiplier = (1.0 + energy_esc) ** (jahr - 1)
        fuel_multiplier = (1.0 + diesel_esc) ** (jahr - 1)
        
        # Solar PV degradation rate (compounding annual loss)
        sol_deg = float(sub_scenario.tech_params.get('solar', {}).get('degradation_pct', 0.5)) / 100.0 if (sub_scenario.tech_params and 'solar' in sub_scenario.tech_params) else 0.005
        deg_multiplier = (1.0 - sol_deg) ** (jahr - 1)
        
        opex_y = fin.opex_yearly * capex_mult * infl_multiplier
        sav_y = grid_savings_yr1 * grid_multiplier * deg_multiplier
        fuel_y = fuel_cost_yr1 * fuel_multiplier
        rent_y = gen_rent * infl_multiplier
        maint_y = gen_maint_yr1 * infl_multiplier
        
        rep_y = 0.0
        if jahr == rep_year:
            rep_y = rep_cost_base * infl_multiplier
            
        opex_liste.append(-opex_y)
        ersparnis_liste.append(sav_y)
        fuel_liste.append(-fuel_y)
        miete_liste.append(-rent_y)
        maintenance_liste.append(-maint_y)
        capex_replacements.append(-rep_y)
        
    df["OPEX (€)"] = opex_liste
    df["Grid Savings (€)"] = ersparnis_liste
    df["Generator Fuel (€)"] = fuel_liste
    df["Generator Rental (€)"] = miete_liste
    df["Generator Maintenance (€)"] = maintenance_liste
    
    grid_costs_liste = [0.0]
    for jahr in range(1, lifespan + 1):
        grid_multiplier = (1.0 + energy_esc) ** (jahr - 1)
        grid_costs_liste.append(-sub_grid_bill * grid_multiplier)
    df["Grid Costs (€)"] = grid_costs_liste
    
    df["CAPEX (€)"] = df["CAPEX (€)"] + capex_replacements
    
    df["Net Cashflow (€)"] = (
        df["CAPEX (€)"] + 
        df["OPEX (€)"] + 
        df["Grid Savings (€)"] + 
        df["Generator Fuel (€)"] +
        df["Generator Rental (€)"] +
        df["Generator Maintenance (€)"]
    )
    df["Cumulative Cashflow (€)"] = df["Net Cashflow (€)"].cumsum()
    df["Present Value (€)"] = df["Net Cashflow (€)"] / ((1.0 + discount_rate) ** df["Year"])
    df["Cumulative NPV (€)"] = df["Present Value (€)"].cumsum()
    
    return df

def get_payback_year(cashflow_df: pd.DataFrame) -> float:
    """Searches for the first year where cumulative cashflow turns positive (break-even)."""
    if cashflow_df is None:
        return None
    gewinn_jahre = cashflow_df[cashflow_df["Cumulative Cashflow (€)"] > 0]
    if gewinn_jahre.empty:
        return -1.0
    return gewinn_jahre["Year"].iloc[0]