# tabs/tab1_components/project_params.py
import streamlit as st
import datetime

def render_project_parameters():
    """
    Renders general project metadata inside an expander.
    Stores all selections in st.session_state['project_metadata'] 
    so it can be attached to any data source (Manual or CSV).
    """
    # Lade bereits gespeicherte Parameter aus einem geladenen Szenario (Klon-Prinzip)
    p = st.session_state.get('loaded_params', {})
    
    with st.expander("🌐 General Project Parameters & Location", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. Sektor-Auswahl
            sectors = ["Industrial", "Hotel / Hospitality", "Logistics / Warehouse", "Agriculture", "Construction Site", "Office Building"]
            saved_sector = p.get('project_metadata', {}).get('sector', "Industrial")
            sector = st.selectbox("Company Sector", sectors, index=sectors.index(saved_sector) if saved_sector in sectors else 0)
            
            # 2. Länder-Auswahl (Vorerst Argentinien und Niederlande)
            countries = ["Netherlands", "Argentina"]
            saved_country = p.get('project_metadata', {}).get('country', "Netherlands")
            country = st.selectbox("Country", countries, index=countries.index(saved_country) if saved_country in countries else 0)
            
            # 3. Dynamische Regionen-Auswahl basierend auf dem gewählten Land
            regions_map = {
                "Netherlands": ["Zeeland", "Noord-Holland", "Zuid-Holland", "Utrecht", "Gelderland", "Brabant"],
                "Argentina": ["Buenos Aires", "Córdoba", "Santa Fe", "Mendoza", "Patagonia", "Salta"]
            }
            available_regions = regions_map.get(country, [])
            saved_region = p.get('project_metadata', {}).get('region', available_regions[0])
            region = st.selectbox("Region / Province", available_regions, index=available_regions.index(saved_region) if saved_region in available_regions else 0)

        with col2:
            # 4. Startdatum der Simulation
            saved_date = p.get('project_metadata', {}).get('start_date', datetime.date(2026, 1, 1))
            start_date = st.date_input("Scenario Start Date", value=saved_date)
            
            # 5. Betrachtungszeitraum (Jahre)
            saved_duration = p.get('project_metadata', {}).get('project_duration', 15)
            project_duration = st.slider("Project Horizon (Years)", min_value=1, max_value=30, value=int(saved_duration))
            
            # 6. Vertragliche Netzkapazität
            saved_contracted = p.get('project_metadata', {}).get('contracted_capacity_kw', 50.0)
            contracted_capacity_kw = st.number_input("Contracted Capacity (kW)", min_value=0.0, value=float(saved_contracted), step=5.0)

        # Alle eingegebenen Daten live in ein Paket schnüren und im Session State ablegen
        st.session_state['project_metadata'] = {
            "sector": sector,
            "country": country,
            "region": region,
            "start_date": start_date,
            "project_duration": project_duration,
            "contracted_capacity_kw": contracted_capacity_kw
        }