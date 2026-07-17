import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def get_bill_components(df: pd.DataFrame, f_params: dict, is_optimized: bool = True) -> dict:
    """Calculates annual billing components based on tariff rules."""
    t = st.session_state.get('t', {})
    temp_df = df.copy()
    if 'timestamp' in temp_df.columns:
        temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
        temp_df['month'] = temp_df['timestamp'].dt.month
        try:
            delta = temp_df['timestamp'].iloc[1] - temp_df['timestamp'].iloc[0]
            factor = 60 / (delta.seconds / 60)
        except:
            factor = 1.0
    else:
        temp_df['month'] = 1
        factor = 1.0
        
    load_col = 'final_grid_load_kw' if (is_optimized and 'final_grid_load_kw' in temp_df.columns) else 'consumption_kw'
    
    monthly_schedule = f_params.get('monthly_tariff_schedule', {})
    
    fixed_total = 0.0
    capacity_total = 0.0
    peak_total = 0.0
    excess_total = 0.0
    energy_total = 0.0
    taxes_total = 0.0
    adjustments_total = 0.0
    
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
        
        m_data = monthly_schedule.get(str(m), {}) or monthly_schedule.get(m, {})
        if not m_data:
            m_data = monthly_schedule.get('1', {}) or monthly_schedule.get(1, {})
            
        base_fee = float(m_data.get('base_fee', 0.0) or 0.0)
        contracted_kw = float(m_data.get('contracted_capacity_kw', 0.0) or 0.0)
        contract_price = float(m_data.get('contracted_capacity_price', 0.0) or 0.0)
        peak_penalty_price = float(m_data.get('peak_penalty_price', 0.0) or 0.0)
        excess_price = float(m_data.get('excess_penalty_price', 0.0) or 0.0)
        subsidy = float(m_data.get('subsidy_amount', 0.0) or 0.0)
        
        alta_price = float(m_data.get('alta', {}).get('price', 0.0) or 0.0)
        alta_start = int(m_data.get('alta', {}).get('start_hour', 18))
        alta_end = int(m_data.get('alta', {}).get('end_hour', 23))
        baja_price = float(m_data.get('baja', {}).get('price', 0.0) or 0.0)
        baja_start = int(m_data.get('baja', {}).get('start_hour', 23))
        baja_end = int(m_data.get('baja', {}).get('end_hour', 5))
        resto_price = float(m_data.get('resto', {}).get('price', 0.0) or 0.0)
        
        # Pico peak
        enable_tou = bool(m_data.get('enable_tou', True))
        pico_peak = m_peak
        if enable_tou and 'timestamp' in m_df.columns:
            m_df_copy = m_df.copy()
            m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
            alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
            pico_df = m_df_copy[alta_mask]
            if len(pico_df) > 0:
                pico_peak = pico_df[load_col].max()
                
        m_fixed_net = base_fee - subsidy
        m_cap_net = contracted_kw * contract_price
        m_peak_penalty = pico_peak * peak_penalty_price
        m_excess = (m_peak - contracted_kw) * excess_price if m_peak > contracted_kw else 0.0
        
        m_energy = 0.0
        if 'timestamp' in m_df.columns:
            m_df_copy = m_df.copy()
            m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
            alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
            baja_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, baja_start, baja_end))
            resto_mask = ~(alta_mask | baja_mask)
            e_alta = m_df_copy[alta_mask][load_col].sum() / factor
            e_baja = m_df_copy[baja_mask][load_col].sum() / factor
            e_resto = m_df_copy[resto_mask][load_col].sum() / factor
            m_energy = (e_alta * alta_price) + (e_baja * baja_price) + (e_resto * resto_price)
        else:
            m_energy = (m_df[load_col].sum() / factor) * resto_price
            
        net_m = m_fixed_net + m_cap_net + m_peak_penalty + m_excess + m_energy
        
        prov_taxes = m_data.get('provincial_taxes', [])
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
        
        net_with_pre_tax = net_m + pre_tax_adj
        
        # Calculate VAT and Surcharges with Compounding support
        total_tax_m = 0.0
        # Sort: non-compounded first, compounded after
        sorted_taxes = sorted(prov_taxes, key=lambda x: bool(x.get('Compound', x.get('compound', False))))
        
        for p_tax in sorted_taxes:
            rate = float(p_tax.get('Rate (%)', p_tax.get('rate', 0.0)) or 0.0)
            compound = bool(p_tax.get('Compound', p_tax.get('compound', False)))
            if compound:
                tax_val = (net_with_pre_tax + total_tax_m) * (rate / 100.0)
            else:
                tax_val = net_with_pre_tax * (rate / 100.0)
            total_tax_m += tax_val
            
        fixed_total += m_fixed_net
        capacity_total += m_cap_net
        peak_total += m_peak_penalty
        excess_total += m_excess
        energy_total += m_energy
        taxes_total += total_tax_m
        
        stabilization_credit = float(m_data.get('stabilization_credit', 0.0) or 0.0)
        adjustments_total += pre_tax_adj + post_tax_adj - stabilization_credit
        
    return {
        t.get("demo_res_bill_fixed", "Fixed connection"): fixed_total,
        t.get("demo_res_bill_capacity", "Contracted capacity"): capacity_total,
        t.get("demo_res_bill_peak", "Peak penalty (Pico)"): peak_total,
        t.get("demo_res_bill_excess", "Excess penalty"): excess_total,
        t.get("demo_res_bill_energy", "Energy cost"): energy_total,
        t.get("demo_res_bill_taxes", "Taxes (VAT + Prov)"): taxes_total,
        t.get("demo_res_bill_adjustments", "Adjustments"): adjustments_total
    }

def render_financials_tab(results: pd.DataFrame, fin_params: dict):
    """Renders the financial impact comparison tab."""
    t = st.session_state.get('t', {})
    st.write(f"### {t.get('demo_res_bill_analysis', '💰 Financial Cost Analysis (Multi-Pillar Tariff Simulation)')}")
    
    results_baseline = results.copy()
    if 'final_grid_load_kw' in results_baseline.columns:
        results_baseline = results_baseline.drop(columns=['final_grid_load_kw'])
        
    baseline_comp = get_bill_components(results_baseline, fin_params, is_optimized=False)
    opt_comp = get_bill_components(results, fin_params, is_optimized=True)
    
    baseline_total = sum(baseline_comp.values())
    opt_total = sum(opt_comp.values())
    savings = baseline_total - opt_total
    savings_pct = (savings / baseline_total * 100.0) if baseline_total > 0 else 0.0
    
    # Render metrics
    sc_col1, sc_col2, sc_col3 = st.columns(3)
    sc_col1.metric(t.get('demo_res_bill_baseline', "Baseline Annual Bill"), f"€ {baseline_total:,.2f}", help=t.get('demo_res_bill_baseline_help', "Total projected annual cost under raw baseline consumption profile."))
    sc_col2.metric(t.get('demo_res_bill_opt', "Optimized Annual Bill"), f"€ {opt_total:,.2f}", help=t.get('demo_res_bill_opt_help', "Total projected annual cost after solar self-consumption and battery peak shaving."))
    sc_col3.metric(t.get('demo_res_bill_savings', "Projected Savings"), f"€ {savings:,.2f} ({savings_pct:.1f}%)", help=t.get('demo_res_bill_savings_help', "Annual savings achieved by shaving peaks and reducing volumetric energy draw."))
    
    st.divider()
    
    # Grouped bar chart
    st.write(f"**{t.get('demo_res_bill_chart_title', 'Annual Bill Surcharges & Components Comparison')}**")
    categories = list(baseline_comp.keys())
    baseline_vals = [baseline_comp[c] for c in categories]
    opt_vals = [opt_comp[c] for c in categories]
    
    fig_comp = go.Figure(data=[
        go.Bar(name=t.get('demo_res_trace_base_bill', 'Baseline (No BESS/PV)'), x=categories, y=baseline_vals, marker_color='#A9A9A9'),
        go.Bar(name=t.get('demo_res_trace_opt_bill', 'Optimized (With BESS/PV)'), x=categories, y=opt_vals, marker_color='#00CC96')
    ])
    fig_comp.update_layout(
        barmode='group',
        height=350,
        yaxis_title="€",
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig_comp, use_container_width=True)
