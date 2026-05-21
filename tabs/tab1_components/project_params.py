# tabs/tab1_components/project_params.py
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

def render_project_params(loaded_metadata: dict, active_scenario: str) -> dict:
    """
    Renders the UI for global project parameters, including dynamic geographical coordinates
    for live weather API fetching via an interactive map and strict grid constraints.
    """
    with st.expander("📝 Enter General Project Data", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Project Name / Company", 
                value=loaded_metadata.get('project_name', ""), 
                key=f"proj_name_{active_scenario}"
            )
            
            countries = ["Netherlands 🇳🇱", "Germany 🇩🇪", "Argentina 🇦🇷", "Other"]
            default_country = loaded_metadata.get('country', "Netherlands 🇳🇱")
            country_idx = countries.index(default_country) if default_country in countries else 0
            country = st.selectbox("Country", options=countries, index=country_idx, key=f"country_{active_scenario}")
            
            sectors = ["Industry", "Agriculture", "Logistics", "Utility", "Hotel / Leisure", "Other"]
            default_sector = loaded_metadata.get('sector', "Industry")
            sector_idx = sectors.index(default_sector) if default_sector in sectors else 0
            sector = st.selectbox("Sector", options=sectors, index=sector_idx, key=f"sector_{active_scenario}")

        with col2:
            st.write("**Grid Operator & Contract Details**")
            grid_operator = st.text_input(
                "Grid Operator Name", 
                value=loaded_metadata.get('grid_operator', ""), 
                key=f"grid_op_{active_scenario}"
            )
            
            voltage_levels = ["Low Voltage (LV)", "Medium Voltage (MV)", "High Voltage (HV)"]
            default_voltage = loaded_metadata.get('voltage_level', "Medium Voltage (MV)")
            voltage_idx = voltage_levels.index(default_voltage) if default_voltage in voltage_levels else 1
            voltage_level = st.selectbox("Voltage Level", options=voltage_levels, index=voltage_idx, key=f"voltage_{active_scenario}")
            
            strict_zero_export = st.checkbox(
                "Strict Zero Export (No Grid Feed-in allowed)", 
                value=loaded_metadata.get('strict_zero_export', False), 
                key=f"zero_exp_{active_scenario}"
            )
            
        st.divider()
        st.write("🌐 **Geographical Location (Live Solar Data)**")
        
        # 1. Smart Default Values
        geo_defaults = {
            "Netherlands 🇳🇱": {"lat": 52.3676, "lon": 4.9041},   # Amsterdam
            "Germany 🇩🇪":     {"lat": 52.5200, "lon": 13.4050},  # Berlin
            "Argentina 🇦🇷":  {"lat": -34.6037, "lon": -58.3816}, # Buenos Aires
            "Other":          {"lat": 0.0, "lon": 0.0}
        }
        fallback = geo_defaults.get(country, geo_defaults["Other"])

        # 2. Session State Bindings (Ensures map and inputs stay in sync)
        lat_key = f"lat_val_{active_scenario}"
        lon_key = f"lon_val_{active_scenario}"
        
        if lat_key not in st.session_state:
            st.session_state[lat_key] = float(loaded_metadata.get('latitude', fallback['lat']))
        if lon_key not in st.session_state:
            st.session_state[lon_key] = float(loaded_metadata.get('longitude', fallback['lon']))

        # 3. Geocoding Search Bar (Type address -> Get coordinates)
        search_query = st.text_input(
            "🔍 Search Address or City (Press Enter):", 
            placeholder="e.g., Rotterdam, Industrieweg 1", 
            key=f"search_{active_scenario}"
        )
        
        if search_query:
            try:
                headers = {'User-Agent': 'DRACBV_Energy_Advisory_App'}
                url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
                response = requests.get(url, headers=headers).json()
                if response:
                    st.session_state[lat_key] = float(response[0]['lat'])
                    st.session_state[lon_key] = float(response[0]['lon'])
                    st.success(f"Found: {response[0]['display_name']}")
                else:
                    st.warning("Address not found. Please try a different query.")
            except Exception:
                st.error("Could not reach location service.")

        # 4. Manual Inputs (Linked to state)
        col_lat, col_lon = st.columns(2)
        
        def update_coords():
            st.session_state[lat_key] = st.session_state[f"lat_input_{active_scenario}"]
            st.session_state[lon_key] = st.session_state[f"lon_input_{active_scenario}"]

        latitude = col_lat.number_input(
            "Latitude (Breitengrad)", value=st.session_state[lat_key], format="%.6f",
            key=f"lat_input_{active_scenario}", on_change=update_coords
        )
        longitude = col_lon.number_input(
            "Longitude (Längengrad)", value=st.session_state[lon_key], format="%.6f",
            key=f"lon_input_{active_scenario}", on_change=update_coords
        )
        
        # 5. Interactive Map Rendering
        use_map = st.toggle("🗺️ Open Interactive Map", value=True, key=f"map_toggle_{active_scenario}")
        
        if use_map:
            # Build the map centered on current coordinates
            m = folium.Map(location=[st.session_state[lat_key], st.session_state[lon_key]], zoom_start=12)
            folium.Marker(
                [st.session_state[lat_key], st.session_state[lon_key]], 
                popup=project_name if project_name else "Selected Location",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            
            # Render map and listen for clicks
            map_data = st_folium(m, height=350, use_container_width=True, key=f"folium_{active_scenario}")
            
            # If user clicks the map, update coordinates and reload UI
            if map_data and map_data.get("last_clicked"):
                st.session_state[lat_key] = map_data["last_clicked"]["lat"]
                st.session_state[lon_key] = map_data["last_clicked"]["lng"]
                st.rerun()

    # Return payload for the registry
    return {
        "project_name": project_name,
        "country": country,
        "sector": sector,
        "grid_operator": grid_operator,
        "voltage_level": voltage_level,
        "strict_zero_export": strict_zero_export,
        "latitude": st.session_state[lat_key],
        "longitude": st.session_state[lon_key]
    }