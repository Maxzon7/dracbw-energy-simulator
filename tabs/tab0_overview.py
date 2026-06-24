# tabs/tab0_overview.py
import streamlit as st

# Neu: Wir importieren die Finanz-Zusammenfassung aus unseren Tab1 Komponenten
from tabs.tab1_components.financial_ui import render_financial_summary

def render_tab0_overview():
    """
    Renders the Executive Dashboard. 
    This tab acts as a read-only consolidation of the active project.
    """
    st.header("📊 Executive Project Overview")
    st.markdown("---")
    
    vault = st.session_state.get('scenario_vault', {})
    
    # Türsteher: Wenn das Projekt noch komplett leer ist
    if not vault:
        st.info("⚠️ This project is currently empty. Please head over to '1️⃣ Baseline' to configure your initial energy profile and tariffs.")
        return
        
    # Wir suchen die "Mutter-Baseline" (den Startpunkt des Projekts, der keinen 'parent' hat)
    baselines = [k for k, v in vault.items() if not v.get('parent')]
    
    if baselines:
        main_baseline = baselines[0]
        # Hol dir die Finanzen der Baseline aus dem Tresor
        base_fin = vault[main_baseline].get('params', {}).get('financial_metadata', {})
        
        # Zeichne die saubere, aufklappbare Finanz-Übersicht
        render_financial_summary(base_fin)
        
    st.markdown("---")
    st.write("### ⚡ System Status & Key Metrics")
    
    # Dummy-KPIs (Hier kommen später die echten aggregierten Daten rein)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Active Baseline", value=main_baseline if baselines else "None")
    with col2:
        st.metric(label="Total Scenarios Generated", value=str(len(vault)))
    with col3:
        if st.session_state.get('enable_financials', True):
            st.metric(label="Financial Evaluation", value="Active")
        else:
            st.metric(label="Financial Evaluation", value="Disabled")
            
    st.markdown("---")
    
    # Export-Bereich (Direkt auf dem Chef-Tab)
    st.write("### 📥 Project Export")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.button("📄 Generate Executive Management Report (PDF)", use_container_width=True)
    with col_dl2:
        st.info("💡 Note: You can download the full .drac project file from the Main Hub (Lobby).")