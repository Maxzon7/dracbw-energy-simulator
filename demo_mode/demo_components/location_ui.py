# demo_mode/demo_components/location_ui.py
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

def render_demo_location_ui(key_suffix: str = "") -> dict:
    """
    Renders the simplified location selection panel for the Demo Mode.
    Returns latitude, longitude, and country.
    """
    t = st.session_state.get('t', {})

    st.write(f"### {t.get('demo_loc_title', '🌐 Location Settings')}")
    st.info(t.get('demo_loc_info', "Select the location to fetch historical solar radiation data (GHI)."))

    countries = ["Netherlands 🇳🇱", "Germany 🇩🇪", "Argentina 🇦🇷", "Other"]
    
    # Initialize country and coordinates session states if not existing
    if f"demo_country{key_suffix}" not in st.session_state:
        st.session_state[f"demo_country{key_suffix}"] = "Netherlands 🇳🇱"
    if f"demo_lat_input{key_suffix}" not in st.session_state:
        st.session_state[f"demo_lat_input{key_suffix}"] = 52.3676
    if f"demo_lon_input{key_suffix}" not in st.session_state:
        st.session_state[f"demo_lon_input{key_suffix}"] = 4.9041
        
    country = st.selectbox(
        t.get('demo_loc_country', "Select Country:"), 
        options=countries, 
        key=f"demo_country_select{key_suffix}"
    )
    
    # Handle country change to reset lat/lon defaults if country changes
    if country != st.session_state[f"demo_country{key_suffix}"]:
        st.session_state[f"demo_country{key_suffix}"] = country
        geo_defaults = {
            "Netherlands 🇳🇱": {"lat": 52.3676, "lon": 4.9041},
            "Germany 🇩🇪":     {"lat": 52.5200, "lon": 13.4050},
            "Argentina 🇦🇷":  {"lat": -34.6037, "lon": -58.3816},
            "Other":          {"lat": 0.0, "lon": 0.0}
        }
        defaults = geo_defaults.get(country, geo_defaults["Other"])
        st.session_state[f"demo_lat_input{key_suffix}"] = defaults["lat"]
        st.session_state[f"demo_lon_input{key_suffix}"] = defaults["lon"]

    # Address search bar
    search_query = st.text_input(
        t.get('demo_loc_search', "🔍 Search Address or City:"), 
        placeholder=t.get('demo_loc_placeholder', "e.g., Rotterdam, Berlin, Buenos Aires"), 
        key=f"demo_search_query{key_suffix}"
    )
    
    if search_query:
        try:
            headers = {'User-Agent': 'DRACBV_Energy_Advisory_Demo_App'}
            url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
            response = requests.get(url, headers=headers).json()
            if response:
                st.session_state[f"demo_lat_input{key_suffix}"] = float(response[0]['lat'])
                st.session_state[f"demo_lon_input{key_suffix}"] = float(response[0]['lon'])
                st.success(f"{t.get('demo_loc_found', '📍 Found: ')}{response[0]['display_name']}")
            else:
                st.warning(t.get('demo_loc_not_found', "Address not found. Please try a different query."))
        except Exception as e:
            st.error(f"{t.get('demo_loc_service_err', 'Could not reach location service: ')}{e}")

    # Manual inputs
    col_lat, col_lon = st.columns(2)
    latitude = col_lat.number_input(
        t.get('demo_loc_lat', "Latitude (Breitengrad)"), 
        format="%.6f",
        key=f"demo_lat_input{key_suffix}"
    )
    longitude = col_lon.number_input(
        t.get('demo_loc_lon', "Longitude (Längengrad)"), 
        format="%.6f",
        key=f"demo_lon_input{key_suffix}"
    )

    # Interactive map toggle
    use_map = st.toggle(t.get('demo_loc_show_map', "🗺️ Show Map"), value=True, key=f"demo_map_toggle{key_suffix}")
    
    if use_map:
        try:
            m = folium.Map(location=[latitude, longitude], zoom_start=12)
            folium.Marker(
                [latitude, longitude], 
                popup=t.get('demo_loc_selected', "Selected Location"),
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            st_folium(m, height=250, use_container_width=True, key=f"demo_folium_map{key_suffix}")
        except Exception:
            st.caption(t.get('demo_loc_map_err', "Map load failed or coordinates out of range."))

    return {
        "country": country,
        "latitude": latitude,
        "longitude": longitude
    }
