# tabs/tab1_components/project_params.py
import streamlit as st
import datetime

def render_project_parameters():
    """
    Renders general project metadata and grid operator specifications inside an expander.
    Stores all selections in st.session_state['project_metadata'] 
    so it can be attached to any data source (Manual or CSV).
    """
    # Lade bereits gespeicherte Parameter aus einem geladenen Szenario (Klon-Prinzip)
    p = st.session_state.get('loaded_params', {})
    meta = p.get('project_metadata', {})
    
    with st.expander("🌐 General Project Parameters & Grid Specifications", expanded=False):
        st.markdown("### 🏢 Project & Location Details")
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. Sektor-Auswahl
            sectors = ["Industrial", "Hotel / Hospitality", "Logistics / Warehouse", "Agriculture", "Construction Site", "Office Building"]
            saved_sector = meta.get('sector', "Industrial")
            sector = st.selectbox("Company Sector", sectors, index=sectors.index(saved_sector) if saved_sector in sectors else 0)
            
            # 2. Länder-Auswahl
            countries = ["Netherlands", "Argentina"]
            saved_country = meta.get('country', "Netherlands")
            country = st.selectbox("Country", countries, index=countries.index(saved_country) if saved_country in countries else 0)
            
            # 3. Dynamische Regionen-Auswahl
            regions_map = {
                "Netherlands": ["Zeeland", "Noord-Holland", "Zuid-Holland", "Utrecht", "Gelderland", "Brabant"],
                "Argentina": ["Buenos Aires", "Córdoba", "Santa Fe", "Mendoza", "Patagonia", "Salta"]
            }
            available_regions = regions_map.get(country, [])
            saved_region = meta.get('region', available_regions[0])
            region = st.selectbox("Region / Province", available_regions, index=available_regions.index(saved_region) if saved_region in available_regions else 0)

        with col2:
            # 4. Startdatum der Simulation
            saved_date = meta.get('start_date', datetime.date(2026, 1, 1))
            start_date = st.date_input("Scenario Start Date", value=saved_date)
            
            # 5. Betrachtungszeitraum (Jahre)
            saved_duration = meta.get('project_duration', 15)
            project_duration = st.slider("Project Horizon (Years)", min_value=1, max_value=30, value=int(saved_duration))
            
            # 6. Vertragliche Netzkapazität
            saved_contracted = meta.get('contracted_capacity_kw', 50.0)
            contracted_capacity_kw = st.number_input("Contracted Capacity (kW)", min_value=0.0, value=float(saved_contracted), step=5.0)

        st.markdown("---")
        st.markdown("### 🔌 Grid Operator Specifications")
        col3, col4 = st.columns(2)
        
        with col3:
            # 7. Name des Netzbetreibers
            saved_operator = meta.get('grid_operator', "")
            grid_operator = st.text_input("Grid Operator Name", value=saved_operator, placeholder="e.g. Liander, Enexis, Edesur...")
            
            # 8. Spannungsebene
            voltage_levels = ["Low Voltage (400V)", "Medium Voltage (10kV - 20kV)"]
            saved_voltage = meta.get('voltage_level', "Low Voltage (400V)")
            voltage_level = st.selectbox("Voltage Level", voltage_levels, index=voltage_levels.index(saved_voltage) if saved_voltage in voltage_levels else 0)
            
        with col4:
            # 9. Einspeise-Richtlinie (Feed-in Policy / Zero Export)
            feed_in_policies = ["Allow Grid Feed-in", "Strict Zero Export Policy"]
            saved_policy = meta.get('feed_in_policy', "Allow Grid Feed-in")
            feed_in_policy = st.radio("Feed-in / Export Policy", feed_in_policies, index=feed_in_policies.index(saved_policy) if saved_policy in feed_in_policies else 0)

        # Alle eingegebenen Daten live in das gemeinsame Paket schnüren und im Session State ablegen
        st.session_state['project_metadata'] = {
            "sector": sector,
            "country": country,
            "region": region,
            "start_date": start_date,
            "project_duration": project_duration,
            "contracted_capacity_kw": contracted_capacity_kw,
            "grid_operator": grid_operator,
            "voltage_level": voltage_level,
            "feed_in_policy": feed_in_policy
        }