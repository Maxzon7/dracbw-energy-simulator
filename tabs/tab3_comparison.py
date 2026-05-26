# tabs/tab3_comparison.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_tab3_comparison():
    """
    Renders the advanced Scenario Comparison Suite with automated Delta-KPI tracking
    for parents and child sub-scenarios.
    """
    st.write("## ⚖️ Advanced Comparison Suite")
    
    if 'scenario_vault' not in st.session_state or not st.session_state['scenario_vault']:
        st.warning("Der Tresor ist leer. Bitte erstelle und speichere Szenarien in Tab 1 oder importiere sie in Tab 4.")
        return
        
    vault = st.session_state['scenario_vault']
    
    # Filter for root baselines to simplify initial selection
    base_options = [name for name, data in vault.items() if not data.get('parent') or data.get('parent') not in vault]
    
    st.write("### 🏢 1. Wählen Sie das Basis-Szenario")
    selected_base = st.selectbox("Haupt-Referenzprofil:", options=base_options)
    
    # Autodetect variants
    linked_subs = [name for name, data in vault.items() if data.get('parent') == selected_base]
    
    auto_compare = False
    if linked_subs:
        st.success(f"🔗 {len(linked_subs)} zugehörige Varianten (Sub-Szenarien) für '{selected_base}' gefunden!")
        auto_compare = st.checkbox("Alle zugehörigen Sub-Szenarien automatisch mit einblenden", value=True)

    # Multiselect for fully custom comparisons
    all_options = list(vault.keys())
    default_selection = [selected_base]
    if auto_compare:
        default_selection.extend(linked_subs)
        
    selected_profiles = st.multiselect("Szenarien im aktiven Vergleich:", options=all_options, default=default_selection)

    if not selected_profiles:
        st.warning("Bitte wählen Sie mindestens ein Szenario für den Vergleich aus.")
        return

    # --- 1. THE VISUAL GRAPH OVERLAY ---
    st.write("### 📈 Lastprofil-Überlagerung")
    fig = go.Figure()
    
    for name in selected_profiles:
        scen = vault[name]
        df = scen.get('df')
        if df is not None:
            # Visual styling hierarchy: Base is thick and dark, subs are colorful
            is_base = (name == selected_base)
            l_width = 3 if is_base else 1.5
            l_color = "#333333" if is_base else None # Auto-color for subs
            
            fig.add_trace(go.Scatter(
                x=df['timestamp'], y=df['consumption_kw'],
                mode='lines',
                line=dict(width=l_width, color=l_color),
                name=f"🏠 {name} (Base)" if is_base else f"🌿 {name}"
            ))
            
    fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), yaxis_title="Leistung (kW)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. THE DELTA-KPI SAVINGS ENGINE ---
    if len(selected_profiles) > 1:
        st.write("### 🧮 Wirtschaftliche Delta-Analyse (Einsparungen)")
        st.info(f"Alle folgenden Einsparungen beziehen sich auf das gewählte Basis-Referenzprofil: **{selected_base}**")
        
        # Calculate Base values as reference benchmarks
        base_df = vault[selected_base]['df']
        base_limit = vault[selected_base].get('grid_limit', 50.0)
        base_peak = base_df['consumption_kw'].max()
        
        base_breach = base_df[base_df['consumption_kw'] > base_limit]
        base_breach_kwh = ((base_breach['consumption_kw'] - base_limit) * 0.25).sum() # 15-min factor
        
        delta_rows = []
        for name in selected_profiles:
            if name == selected_base:
                continue # Skip base itself for delta row
                
            scen = vault[name]
            sub_df = scen['df']
            sub_limit = scen.get('grid_limit', 50.0)
            sub_peak = sub_df['consumption_kw'].max()
            
            sub_breach = sub_df[sub_df['consumption_kw'] > sub_limit]
            sub_breach_kwh = ((sub_breach['consumption_kw'] - sub_limit) * 0.25).sum()
            
            # Mathematical Deltas (Positive numbers = Savings!)
            peak_savings = base_peak - sub_peak
            overload_savings_kwh = base_breach_kwh - sub_breach_kwh
            
            delta_rows.append({
                "Variante": name,
                "Max Peak Load (kW)": f"{sub_peak:.1f} kW",
                "Spitzenlast-Reduktion (Δ kW)": f"+ {peak_savings:.1f} kW" if peak_savings >= 0 else f"- {abs(peak_savings):.1f} kW",
                "Netzüberlastung (kWh)": f"{sub_breach_kwh:,.0f} kWh",
                "Eingesparte Überlast-Energie (Δ kWh)": f"+ {overload_savings_kwh:,.0f} kWh" if overload_savings_kwh >= 0 else f"- {abs(overload_savings_kwh):,.0f} kWh"
            })
            
        if delta_rows:
            st.dataframe(pd.DataFrame(delta_rows), use_container_width=True, hide_index=True)