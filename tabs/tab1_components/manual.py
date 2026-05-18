# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd
import numpy as np
# Wichtig: Exakte Schreibweise deines Dateinamens nutzen (ohne "h" bei syntetic)
from tabs.tab1_components.syntetic_load import synthetic_load

def render_manual_profile_generator():
    """
    Renders the UI for generating synthetic 15-min load profiles for a full year.
    Connects the inputs to the calculation engine in syntetic_load.py.
    Saves the dataframe to session_state['filtered_data'].
    """
    t = st.session_state['t']
    
    st.subheader(t.get("manual_input", "Synthetic Profile Generator"))
    st.write("Generiere ein Jahres-Lastprofil auf Basis von Branchen-Rahmendaten.")
    
    # Aufbau des 2-Spalten-Layouts gemäß deiner Vorlage
    col1, col2 = st.columns(2)
    
    with col1:
        sector = st.selectbox(
            t.get("sector", "Sector"), 
            ["Manufacturing", "Hospital", "Commercial", "Data Center", "Agriculture"]
        )
        scale = st.selectbox(
            t.get("scale", "Scale"), 
            ["Small", "Medium", "Large", "Enterprise"]
        )
        operation_hours = st.selectbox(
            t.get("operation_hours", "Operation Hours"), 
            ["24/7", "8h (Day shift)", "16h (Two shifts)", "Custom"]
        )
        annual_consumption = st.number_input(
            t.get("annual_consumption", "Annual Consumption (kWh)"), 
            min_value=1000, value=500000, step=10000
        )
        
    with col2:
        base_load_pct = st.slider(
            t.get("base_load_pct", "Base Load (%)"), 
            min_value=0, max_value=100, value=20
        )
        peak_multiplier = st.number_input(
            t.get("peak_multiplier", "Peak Load Multiplier"), 
            min_value=1.0, value=1.5, step=0.1
        )
        peak_hours = st.multiselect(
            t.get("peak_hours", "Peak Load Hours"), 
            ["00:00 - 04:00", "04:00 - 08:00", "08:00 - 12:00", 
             "12:00 - 16:00", "16:00 - 20:00", "20:00 - 24:00"],
            default=["08:00 - 12:00", "12:00 - 16:00"]
        )
        weekend_operation = st.toggle(
            t.get("weekend_operation", "Weekend Operation"), 
            value=False
        )
        
    st.divider()
    col_raw = st.color_picker("Raw Load Color", "#A9A9A9", key="man_col")
    
    # 3. Profile Generation Engine-Trigger
    if st.button(t.get("generate_profile", "Generate Profile"), type="primary", use_container_width=True):
        with st.spinner("Generating 15-min interval data..."):
            
            # Aufruf deiner Berechnungslogik aus syntetic_load.py
            df_synthetic = synthetic_load(
                annual_consumption=annual_consumption,
                base_load_pct=base_load_pct,
                peak_multiplier=peak_multiplier,
                operation_hours=operation_hours,
                weekend_operation=weekend_operation,
                peak_hours=peak_hours,
                year=2026  # Synchronisiert mit deiner restlichen App-Timeline von 2026
            )
            
            # State-Management: Beibehaltung deiner App-Konventionen
            st.session_state['resolution'] = 15
            st.session_state['col_raw'] = col_raw
            st.session_state['report_name'] = "Manual_Synthetic_Profile"
            
            # Setzt das Netzkapazitätslimit dynamisch auf 110% der maximal generierten Spitze
            st.session_state['grid_limit'] = float(df_synthetic['consumption_kw'].max() * 1.1)
            
            # WICHTIG: Speichern im exakt selben State-Key, den auch deine chart.py ausliest
            st.session_state['filtered_data'] = df_synthetic
            
            st.success(t.get("profile_generated_success", "Profile successfully generated!"))
            st.rerun()