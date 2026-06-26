# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- NEW CLASS-BASED IMPORTS ---
from logic.storage_manager import get_all_base_scenarios
from tabs.tab3_components.financial_engine import generate_15_year_cashflow, get_payback_year
from tabs.tab3_components.tarrif_calc import render_tariff_builder_ui

def render_tab3_comparison():
    """
    Renders the advanced Scenario Comparison Suite with automated Delta-KPI tracking
    for parents (BaseScenario) and child solutions (SubScenarios). 
    """
    st.write("## ⚖️ Advanced Comparison Suite")
    
    # 1. Fetch data from our new Class Vault
    bases = get_all_base_scenarios()
    
    if not bases:
        st.warning("No saved Scenarios found. Please create a Baseline in Tab 1.")
        return
        
    base_options = [b.name for b in bases]

    st.write("### 1. Select the Base Scenario")
    selected_base_name = st.selectbox("Baseline Reference Profile:", options=base_options)
    
    # Extract the actual class object
    selected_base_obj = next((b for b in bases if b.name == selected_base_name), None)
    
    if not selected_base_obj or selected_base_obj.original_profile is None:
        st.info("No data in this baseline yet. Please process data in Tab 1.")
        return

    # Autodetect Variants (Children)
    linked_subs = selected_base_obj.sub_scenarios
    sub_names = [sub.name for sub in linked_subs]
    
    auto_compare = False
    if sub_names:
        st.success(f"🔗 {len(sub_names)} associated variants (Sub-Scenarios) found for '{selected_base_name}'!")
        auto_compare = st.checkbox("Automatically overlay all associated sub-scenarios", value=True)

    # Multiselect for Custom Comparisons
    all_options = [selected_base_name] + sub_names
    default_selection = [selected_base_name]
    if auto_compare:
        default_selection.extend(sub_names)
        
    selected_profiles = st.multiselect("Active Scenarios in Comparison:", options=all_options, default=default_selection)

    if not selected_profiles:
        st.warning("Please choose at least one scenario for the comparison.")
        return

    # Helper function to grab the correct DataFrame from our objects
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
        if df is not None:
            is_base = (name == selected_base_name)
            l_width = 3 if is_base else 1.5
            l_color = "#333333" if is_base else None 
            
            # Switch to final grid load if available (Sub-scenarios)
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in df.columns else 'consumption_kw'
            
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df[y_col],
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
            # Check if variant has a custom tariff, otherwise use base limit
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
        
        # Call the new integrated Class-based CFO Cockpit
        active_subs = [s for s in linked_subs if s.name in selected_profiles]
        render_cfo_cockpit_from_classes(selected_base_obj, active_subs)

def render_cfo_cockpit_from_classes(base_scenario, selected_subs):
    """
    Renders the Financial Data dynamically based on the presence of FinancialParams in the objects.
    """
    st.header("📊 Executive CFO Dashboard")
    
    if not selected_subs:
        st.info("Select at least one variant above to see the financial comparison.")
        return
        
    has_financials = any(sub.financials is not None for sub in selected_subs)
    
    if not has_financials:
        # --- TECHNICAL ONLY MODE ---
        st.warning("⚙️ **Technical Mode**: No financial data was entered in Tab 2. Showing performance summary only.")
        
        tech_data = []
        for sub in selected_subs:
            tech_data.append({
                "Scenario": sub.name,
                "Battery (kWh)": sub.battery_kwh,
                "Battery Power (kW)": sub.battery_kw,
                "Solar (kWp)": sub.solar_kwp,
                "Hardware Added?": "Yes" if (sub.battery_kwh > 0 or sub.solar_kwp > 0) else "No"
            })
        st.table(pd.DataFrame(tech_data))
        
    else:
        # --- FINANCIAL CFO MODE ---
        st.success("💰 **Financial Mode Active**: Calculating Cashflows & ROI based on 15-Year Lifespan.")
        
        col1, col2 = st.columns(2)
        
        cashflow_diagrams_data = pd.DataFrame()
        kpi_data = []
        
        for sub in selected_subs:
            if sub.financials:
                df_cashflow = generate_15_year_cashflow(sub, base_scenario)
                payback = get_payback_year(df_cashflow)
                
                if cashflow_diagrams_data.empty:
                    cashflow_diagrams_data["Year"] = df_cashflow["Jahr"] # Internal mapping
                cashflow_diagrams_data[sub.name] = df_cashflow["Kumulierter_Cashflow"]
                
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
            cashflow_diagrams_data.set_index("Year", inplace=True) 
            st.line_chart(cashflow_diagrams_data)