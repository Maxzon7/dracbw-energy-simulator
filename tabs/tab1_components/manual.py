# tabs/tab1_components/manual.py
import streamlit as st
from tabs.tab1_components.synthetic_load import synthetic_load
from data_models.scenarios import BaselineScenario
import pandas as pd
def render_manual_profile_generator():
    """
    Renders the UI for generating synthetic 15-min load profiles for ONE MONTH.
    Connects the inputs to the calculation engine including dynamic noise control.
    """
    if 't' not in st.session_state:
        st.session_state['t'] = {}
        
    t = st.session_state['t']
    
    st.subheader(t.get("manual_input_title", "Manual Load Profile (1 Month)"))
    st.write(t.get("manual_input_desc", "Generate a load profile based on basic consumption and operational data."))
    
    col1, col2 = st.columns(2)
    
    with col1:
        monthly_consumption = st.number_input(
            t.get("monthly_consumption", "Monthly Consumption (kWh)"), 
            min_value=100, value=15000, step=1000,
            help=t.get("help_monthly_cons", "Average electricity consumption per month.")
        )
        days_per_week = st.slider(
            t.get("days_per_week", "Working Days per Week"), 
            min_value=1, max_value=7, value=5,
            help=t.get("help_days_week", "Number of active working days per week.")
        )
        hours_per_day = st.slider(
            t.get("hours_per_day", "Working Hours per Day"), 
            min_value=1, max_value=24, value=8,
            help=t.get("help_hours_day", "Number of working hours per active day.")
        )
        
    with col2:
        st.write("#### " + t.get("grid_connection", "Grid Connection"))
        num_connections = st.number_input(
            t.get("num_connections", "Number of Connections"), 
            min_value=1, value=1, step=1,
            help=t.get("help_num_conn", "How many grid connections does the site have?")
        )
        amperage = st.number_input(
            t.get("amperage", "Amperage per Connection (A)"), 
            min_value=16, value=250, step=10,
            help=t.get("help_amperage", "Fuse size / Amperage per connection.")
        )
        
        # Calculate grid limit in kW (Standard 3-phase 400V AC: P = I * V * sqrt(3) / 1000)
        calculated_grid_kw = num_connections * amperage * 400 * 1.732 / 1000
        st.info(f"**{t.get('calculated_grid_limit', 'Calculated Grid Limit')}**: ~{calculated_grid_kw:,.1f} kW")
        
    st.divider()
    
    # --- NEU: EINZELN ZUSCHALTBARE SCHWANKUNGEN ---
    st.write("### " + t.get("profile_behavior", "Profile Load Behavior"))
    
    enable_noise = st.toggle(
        t.get("enable_noise", "Enable realistic load fluctuations"), 
        value=False,
        help=t.get("help_enable_noise", "If disabled, the profile stays perfectly flat. If enabled, random fluctuations are simulated.")
    )
    
    noise_percentage = 0.0
    if enable_noise:
        noise_percentage = st.slider(
            t.get("noise_intensity", "Fluctuation Intensity (%)"), 
            min_value=1, max_value=30, value=5, step=1,
            help=t.get("help_noise_intensity", "Define the variance/amplitude of the fluctuations during work hours.")
        )
        
    st.divider()
    
    st.write("### " + t.get("optional_loads", "Optional Additional Loads (In Development)"))
    st.info("💡 " + t.get("optional_loads_desc", "In the future, EV chargers, heat pumps, or other specific consumers can be added here."))

    st.divider()

    # --- NEU: ADVANCED MONTHLY CUSTOMIZATION ---
    st.write("### Advanced: Custom Monthly Profiles")
    use_custom_months = st.checkbox("Enable custom logic per month", value=False)
    
    # Hier speichern wir die Konfigurationen für alle 12 Monate
    monthly_configs = {}
    
    if use_custom_months:
        st.info("Values are pre-filled with your standard configuration. Adjust specific months as needed.")
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        tabs = st.tabs(month_names)
        
        for i, tab in enumerate(tabs):
            m_idx = i + 1
            with tab:
                # Wichtig: key=... verhindert Abstürze bei gleichen Slider-Namen
                m_cons = st.number_input(f"Consumption (kWh) - {month_names[i]}", value=monthly_consumption, key=f"c_{m_idx}")
                m_days = st.slider(f"Working Days - {month_names[i]}", min_value=1, max_value=7, value=days_per_week, key=f"d_{m_idx}")
                m_hours = st.slider(f"Working Hours - {month_names[i]}", min_value=1, max_value=24, value=hours_per_day, key=f"h_{m_idx}")
                monthly_configs[m_idx] = {"consumption": m_cons, "days": m_days, "hours": m_hours}
    else:
        # Wenn Checkbox aus ist: Standardwerte 12x kopieren
        for i in range(1, 13):
            monthly_configs[i] = {"consumption": monthly_consumption, "days": days_per_week, "hours": hours_per_day}
    # --- ENDE NEU ---
    


    st.divider()
    col_raw = st.color_picker(t.get("color_picker", "Chart Line Color"), "#A9A9A9", key="man_col")
    
    if st.button("Generate Profile", type="primary", use_container_width=True):
        with st.spinner("Generating profile..."):
            
            # SCHRITT 1: Wir erstellen unser dummes, simples Objekt mit den Nutzer-Eingaben
            baseline = BaselineScenario(
                monthly_consumption = monthly_consumption,
                days_per_week = days_per_week,
                hours_per_day = hours_per_day,
                num_connections = num_connections,
                amperage = amperage,
                enable_noise = enable_noise,
                noise_percentage = noise_percentage
            )
            
            # SCHRITT 2: Wir lassen die Logik aus synthetic_load.py die echte Tabelle berechnen.
            monthly_dfs = []
            for m_idx in range(1, 13):
                config = monthly_configs[m_idx]
                df_month = synthetic_load(
                    monthly_consumption = config["consumption"],
                    days_per_week = config["days"],
                    hours_per_day = config["hours"],
                    base_load_pct = 15, 
                    year = 2026,
                    month = m_idx, # Hier wird der aktuelle Monat 1-12 übergeben!
                    noise_enabled = enable_noise,
                    noise_percentage = noise_percentage
                )
                monthly_dfs.append(df_month)
                
            # Alle 12 Monate zusammenfügen und den Index komplett neu aufbauen
            annual_df = pd.concat(monthly_dfs, ignore_index=True)
            # Zur absoluten Sicherheit nach dem Zeitstempel chronologisch sortieren
            annual_df.sort_values("timestamp", inplace=True)
            annual_df.reset_index(drop=True, inplace=True)
            
            # SCHRITT 3: Wir legen die fertige Jahres-Tabelle in unser Objekt ab
            baseline.load_profile = annual_df
            
            # SCHRITT 4: Ab in den Tresor!
            st.session_state['baseline_scenario'] = baseline
            st.session_state['filtered_data'] = annual_df
            st.session_state['grid_limit'] = float(num_connections * amperage * 400 * 1.732 / 1000)
            
            st.success("Jahresprofil erfolgreich generiert und als Baseline gespeichert!")
            st.rerun()