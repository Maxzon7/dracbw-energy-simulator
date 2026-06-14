# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# --- NEW: Import the outsourced Financial Engine ---
from tabs.tab3_components.financial_engine import render_financial_dashboard
from tabs.tab3_components.tarrif_calc import render_tariff_builder_ui

def render_tab3_comparison():
    """
    Renders the advanced Scenario Comparison Suite with automated Delta-KPI tracking
    for parents and child sub-scenarios. Includes the Executive CFO Dashboard.
    """
    st.write("## ⚖️ Advanced Comparison Suite")
    
    if 'scenario_vault' not in st.session_state or not st.session_state['scenario_vault']:
        st.warning("Der Tresor ist leer. Bitte erstelle und speichere Szenarien in Tab 1 oder importiere sie in Tab 4.")
        return
        
    vault = st.session_state['scenario_vault']
    
    # Filter für die Dropdown-Auswahl (nur echte Basis-Szenarien anzeigen)
    base_options = [name for name, data in vault.items() if not data.get('parent') or data.get('parent') not in vault]
    
    if not base_options:
        st.warning("Keine Basis-Szenarien im Tresor gefunden.")
        return

    st.write("### 🏢 1. Select the Base Scenario")
    selected_base = st.selectbox("Baseline Reference Profile:", options=base_options)
    
    # Autodetect Variants
    linked_subs = [name for name, data in vault.items() if data.get('parent') == selected_base]
    
    auto_compare = False
    if linked_subs:
        st.success(f"🔗 {len(linked_subs)} associated variants (Sub-Scenarios) found for '{selected_base}'!")
        auto_compare = st.checkbox("Automatically overlay all associated sub-scenarios", value=True)

    # Multiselect für Custom-Vergleiche
    all_options = list(vault.keys())
    default_selection = [selected_base]
    if auto_compare:
        default_selection.extend(linked_subs)
        
    selected_profiles = st.multiselect("Active Scenarios in Comparison:", options=all_options, default=default_selection)

    if not selected_profiles:
        st.warning("Bitte wählen Sie mindestens ein Szenario für den Vergleich aus.")
        return

    # --- 1. THE VISUAL GRAPH OVERLAY ---
    st.write("### 📈 Load Profile Overlay")
    fig = go.Figure()
    
    for name in selected_profiles:
        scen = vault[name]
        df = scen.get('df')
        if df is not None:
            is_base = (name == selected_base)
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
        st.write("### 🧮 Physical Delta Analysis (Technical Savings)")
        
        base_df = vault[selected_base]['df']
        base_limit = vault[selected_base].get('grid_limit', 50.0)
        base_peak = base_df['consumption_kw'].max()
        
        base_breach = base_df[base_df['consumption_kw'] > base_limit]
        base_breach_kwh = ((base_breach['consumption_kw'] - base_limit) * 0.25).sum() if not base_breach.empty else 0.0
        
        delta_rows = []
        for name in selected_profiles:
            if name == selected_base:
                continue 
                
            scen = vault[name]
            sub_df = scen['df']
            sub_limit = scen.get('grid_limit', 50.0)
            
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
        
        # NEU: Custom Tariff Builder UI
        render_tariff_builder_ui()
    
        render_financial_dashboard(selected_profiles, selected_base, vault)
