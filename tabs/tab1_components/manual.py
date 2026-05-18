# tabs/tab1_components/manual.py
import streamlit as st
from tabs.tab1_components.synthetic_load import synthetic_load

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
    col_raw = st.color_picker(t.get("color_picker", "Chart Line Color"), "#A9A9A9", key="man_col")
    
    if st.button(t.get("generate_profile", "Generate Profile"), type="primary", use_container_width=True):
        with st.spinner(t.get("generating_spinner", "Generating 15-minute interval data...")):
            
            # Aufruf der Berechnungslogik mit den dynamischen Noise-Parametern
            df_synthetic = synthetic_load(
                monthly_consumption=monthly_consumption,
                days_per_week=days_per_week,
                hours_per_day=hours_per_day,
                base_load_pct=15, 
                year=2026,
                month=1,
                noise_enabled=enable_noise,
                noise_percentage=noise_percentage
            )
            
            # State-Management aktualisieren
            st.session_state['resolution'] = 15
            st.session_state['col_raw'] = col_raw
            st.session_state['report_name'] = "Manual_Monthly_Profile"
            st.session_state['grid_limit'] = float(calculated_grid_kw)
            st.session_state['filtered_data'] = df_synthetic
            
            st.success(t.get("success_profile", "Profile successfully generated!"))
            
            # Statistiken & Grenzwertprüfung im UI anzeigen
            max_load = df_synthetic['consumption_kw'].max()
            grid_limit = calculated_grid_kw
            exceedance = max(0, max_load - grid_limit)
            
            st.write("### " + t.get("profile_stats", "Profile Statistics"))
            stat_col1, stat_col2, stat_col3 = st.columns(3)
            stat_col1.metric(t.get("max_load", "Peak Load (kW)"), f"{max_load:,.1f}")
            stat_col2.metric(t.get("grid_limit_metric", "Grid Limit (kW)"), f"{grid_limit:,.1f}")
            
            if exceedance > 0:
                stat_col3.metric(t.get("exceedance", "Exceedance (kW)"), f"{exceedance:,.1f}", delta="- Over Limit", delta_color="inverse")
                st.error(t.get("warning_exceedance", f"Warning: The generated peak load exceeds the grid connection by {exceedance:,.1f} kW! Please adjust parameters."))
            else:
                stat_col3.metric(t.get("exceedance", "Exceedance (kW)"), "0.0", delta="Within Limits", delta_color="normal")
            
            st.rerun()