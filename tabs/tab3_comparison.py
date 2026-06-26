# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from logic.storage_manager import get_all_base_scenarios
from tabs.tab3_components.financial_engine import generate_15_year_cashflow, get_payback_year
from tabs.tab3_components.tarrif_calc import render_tariff_builder_ui

def render_tab3_comparison():
    st.write("## ⚖️ Advanced Comparison Suite")
    
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
        st.success(f"🔗 {len(sub_names)} associated variants found for '{selected_base_name}'!")
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

    # --- 2. THE PHYSICAL DELTA-KPI SAVINGS ENGINE ---
    if len(selected_profiles) > 1:
        st.write("### Physical Delta Analysis (Technical Savings)")
        
        base_df = selected_base_obj.original_profile
        base_limit = selected_base_obj.base_tariff.contracted_capacity_kw
        base_peak = base_df['consumption_kw'].max()
        
        base_breach = base_df[base_df['consumption_kw'] > base_limit]
        base_breach_kwh = ((base_breach['consumption_kw'] - base_limit) * 0.25).sum() if not base_breach.empty else 0.0
        
        delta_rows = []
        for name in selected_profiles:
            if name == selected_base_name:
                continue 
                
            sub_obj = next((s for s in linked_subs if s.name == name), None)
            if not sub_obj: continue
                
            sub_df = sub_obj.simulated_profile
            sub_limit = sub_obj.custom_tariff.contracted_capacity_kw if sub_obj.custom_tariff else base_limit
            
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in sub_df.columns else 'consumption_kw'
            sub_peak = sub_df[y_col].max()
            
            sub_breach = sub_df[sub_df[y_col] > sub_limit]
            sub_breach_kwh = ((sub_breach[y_col] - sub_limit) * 0.25).sum() if not sub_breach.empty else 0.0
            
            peak_savings = base_peak - sub_peak
            overload_savings_kwh = base_breach_kwh - sub_breach_kwh
            
            delta_rows.append({
                "Variant": name,
                "Max Peak Load (kW)": f"{sub_peak:.1f} kW",
                "Peak Reduction (Δ kW)": f"+ {peak_savings:.1f} kW" if peak_savings >= 0 else f"- {abs(peak_savings):.1f} kW",
                "Remaining Grid Overload": f"{sub_breach_kwh:,.0f} kWh",
                "Overload Energy Saved (Δ kWh)": f"+ {overload_savings_kwh:,.0f} kWh" if overload_savings_kwh >= 0 else f"- {abs(overload_savings_kwh):,.0f} kWh"
            })
            
        if delta_rows:
            st.dataframe(pd.DataFrame(delta_rows), use_container_width=True, hide_index=True)
            
        # --- 3. THE CFO FINANCIAL DASHBOARD ---
        st.divider()
        render_tariff_builder_ui()
        st.divider()
        
        active_subs = [s for s in linked_subs if s.name in selected_profiles]
        render_cfo_cockpit_from_classes(selected_base_obj, active_subs)

def render_cfo_cockpit_from_classes(base_scenario, selected_subs):
    st.header("📊 Executive CFO Dashboard")
    
    if not selected_subs:
        st.info("Select at least one variant above to see the financial comparison.")
        return
        
    has_financials = any(sub.financials is not None for sub in selected_subs)
    
    if not has_financials:
        st.warning("⚙️ **Technical Mode**: No financial data was entered in Tab 2. Showing performance summary only.")
        tech_data = []
        for sub in selected_subs:
            tech_data.append({
                "Scenario": sub.name, "Battery (kWh)": sub.battery_kwh, "Battery Power (kW)": sub.battery_kw,
                "Solar (kWp)": sub.solar_kwp, "Hardware Added?": "Yes" if (sub.battery_kwh > 0 or sub.solar_kwp > 0) else "No"
            })
        st.table(pd.DataFrame(tech_data))
        
    else:
        st.success("💰 **Financial Mode Active**: Calculating Cashflows & ROI based on 15-Year Lifespan.")
        col1, col2 = st.columns(2)
        
        kpi_data = []
        
        # Plotly Setup für das Finanz-Diagramm (Robuster als st.line_chart!)
        fig_cf = go.Figure()
        
        for sub in selected_subs:
            if sub.financials:
                df_cashflow = generate_15_year_cashflow(sub, base_scenario)
                payback = get_payback_year(df_cashflow)
                
                # Trace hinzufügen
                fig_cf.add_trace(go.Scatter(
                    x=df_cashflow["Jahr"],
                    y=df_cashflow["Kumulierter_Cashflow"],
                    mode='lines+markers',
                    name=sub.name,
                    line=dict(width=3)
                ))
                
                kpi_data.append({
                    "Scenario": sub.name,
                    "Hardware (CAPEX)": f"€ {sub.financials.capex:,.0f}",
                    "O&M p.a. (OPEX)": f"€ {sub.financials.opex_yearly:,.0f}",
                    "Payback (Break-Even)": f"{payback} Years" if payback > 0 else "Never (>15 Yrs)"
                })
        
        with col1:
            st.markdown("### 🏆 Management Summary")
            st.dataframe(pd.DataFrame(kpi_data), hide_index=True)
            
        with col2:
            st.markdown("### 📈 Cumulative Cashflow (15 Years)")
            fig_cf.update_layout(height=400, hovermode="x unified", xaxis_title="Years", yaxis_title="Cashflow (€)", margin=dict(l=0, r=0, t=10, b=0))
            fig_cf.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Break-Even", annotation_position="bottom right")
            st.plotly_chart(fig_cf, use_container_width=True)