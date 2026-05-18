# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd
import numpy as np
from tabs.tab1_components.synthetic_load import synthetic_load

def render_manual_profile_generator():
    """
    Renders the UI for generating synthetic 15-min load profiles.
    Connects the inputs to the calculation engine in synthetic_load.py.
    """
    t = st.session_state['t']
    
    st.subheader(t.get("manual_input", "Manuelles Lastprofil"))
    st.write("Generiere ein Lastprofil auf Basis grundlegender Verbrauchs- und Betriebsdaten.")
    
    # Die neuen Eingabefelder im 2-Spalten-Layout
    col1, col2 = st.columns(2)
    
    with col1:
        monthly_consumption = st.number_input(
            "Monatlicher Verbrauch (kWh)", 
            min_value=100, value=15000, step=1000,
            help="Der durchschnittliche Stromverbrauch pro Monat."
        )
        days_per_week = st.slider(
            "Arbeitstage pro Woche", 
            min_value=1, max_value=7, value=5,
            help="An wie vielen Tagen in der Woche ist der Betrieb aktiv?"
        )
        
    with col2:
        hours_per_day = st.slider(
            "Arbeitsstunden pro Tag", 
            min_value=1, max_value=24, value=8,
            help="Wie viele Stunden wird pro Arbeitstag gearbeitet?"
        )
        grid_connection_kw = st.number_input(
            "Netzanschlussleistung (kW)", 
            min_value=10, value=250, step=10,
            help="Die maximale Kapazität des Netzanschlusses in kW."
        )
        
    st.divider()
    
    # Optischer Platzhalter für das spätere Hinzufügen von Verbrauchern
    st.write("### Optionale Zusatzlasten (In Entwicklung)")
    st.info("💡 Zukünftig können hier E-Ladesäulen (EV), Wärmepumpen oder andere spezifische Stromverbraucher dem Profil hinzugefügt werden.")
    
    st.divider()
    col_raw = st.color_picker("Farbe des Lastgangs im Chart", "#A9A9A9", key="man_col")
    
    # Engine-Trigger
    if st.button(t.get("generate_profile", "Profil generieren"), type="primary", use_container_width=True):
        with st.spinner("Generiere 15-Minuten Intervalle..."):
            
            # Aufruf der neuen Berechnungslogik
            df_synthetic = synthetic_load(
                monthly_consumption=monthly_consumption,
                days_per_week=days_per_week,
                hours_per_day=hours_per_day,
                base_load_pct=15, # Festwert: 15% Grundlast nachts/am Wochenende (kannst du später auch anpassbar machen)
                year=2026 
            )
            
            # State-Management aktualisieren
            st.session_state['resolution'] = 15
            st.session_state['col_raw'] = col_raw
            st.session_state['report_name'] = "Manuelles_Profil"
            
            # WICHTIG: Das Netzlimit wird jetzt auf Basis deiner Eingabe festgelegt!
            st.session_state['grid_limit'] = float(grid_connection_kw)
            
            # Daten für den Chart speichern
            st.session_state['filtered_data'] = df_synthetic
            
            st.success("Profil erfolgreich generiert!")
            st.rerun()