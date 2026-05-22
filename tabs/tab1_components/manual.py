
# tabs/tab1_components/manual.py
import streamlit as st
import pandas as pd

# Deine ausgelagerte Logik importieren
from tabs.tab1_components.manual_components.generation_logic import generate_synthetic_profile
# Unseren neuen "Trichter" importieren
from tabs.tab1_components.validation_ui import render_validation_dashboard

def render_manual_builder(active_scenario: str, is_edit_mode: bool, p: dict):
    """
    Sammelt die Parameter für ein manuelles Profil, generiert die Daten 
    und leitet sie an das gemeinsame Validation Dashboard (den Trichter) weiter.
    """
    t = st.session_state.get('t', {})
    
    st.write("### 🎛️ Manual Profile Generator")
    st.info("Set the parameters below to generate a synthetic industrial load profile.")
    
    # 1. Parameter Eingabefelder
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Time Configuration")
        days = st.number_input(
            "Duration (Days)", min_value=1, max_value=365, 
            value=int(p.get('days', 30)), step=1, key=f"days_{active_scenario}"
        )
        res_options = [1, 5, 15, 60]
        saved_res = p.get('resolution', 15)
        res_index = res_options.index(saved_res) if saved_res in res_options else 2
        res = st.selectbox(
            "Resolution (min)", res_options, 
            index=res_index, key=f"res_manual_{active_scenario}"
        )

    with col2:
        st.subheader("Load Characteristics")
        base_load = st.number_input(
            "Base Load (kW)", min_value=0.0, max_value=1000.0, 
            value=float(p.get('base_load', 20.0)), step=5.0, key=f"base_load_{active_scenario}"
        )
        peak_load = st.number_input(
            "Peak Load (kW)", min_value=10.0, max_value=5000.0, 
            value=float(p.get('peak_load', 150.0)), step=10.0, key=f"peak_load_{active_scenario}"
        )

    st.divider()
    
    col_g1, col_g2 = st.columns(2)
    grid_limit = col_g1.number_input(
        "Grid Limit (kW)", min_value=10.0, max_value=5000.0, 
        value=float(p.get('grid_limit', 100.0)), step=10.0, key=f"grid_limit_manual_{active_scenario}"
    )
    col_raw = col_g2.color_picker(
        "Raw Load Color", p.get('col_raw', "#A9A9A9"), key=f"col_raw_manual_{active_scenario}"
    )
    
    report_name = st.text_input(
        "Report Title", value=p.get('report_name', "Manual_Energy_Report"), 
        key=f"report_title_manual_{active_scenario}"
    )

    # 2. Generator-Engine starten
    df = None
    if st.button("⚙️ Generate / Update Profile", type="secondary", use_container_width=True, key=f"gen_btn_{active_scenario}"):
        with st.spinner("Calculating physical load intervals..."):
            df = generate_synthetic_profile(days, res, base_load, peak_load)
            st.session_state['filtered_data'] = df
            st.success(f"✅ Generated {len(df)} intervals successfully!")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'Manual':
        df = st.session_state['filtered_data']
        st.success(f"📦 Currently using active data from loaded scenario: '{st.session_state.get('active_scenario_name')}'")

    # ==========================================
    # 3. DIE MAGIE: ÜBERGABE AN DEN TRICHTER
    # ==========================================
    if df is not None and not df.empty:
        # Wir schnüren ein Paket mit allen aktuellen Schieberegler-Werten
        params_to_pass = {
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "Manual",
            "report_name": report_name,
            "grid_limit": grid_limit,
            "resolution": res,
            "col_raw": col_raw,
            # Diese Werte sichern wir, falls der Berater das Profil später nochmal laden will
            "days": days,
            "base_load": base_load,
            "peak_load": peak_load
        }
        
        # Ab hier rufen wir die exakt gleiche Oberfläche auf wie im CSV-Upload!
        render_validation_dashboard(df, params_to_pass, active_scenario, is_edit_mode)