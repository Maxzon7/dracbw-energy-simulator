# demo_mode/demo_components/location_ui.py
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

def render_demo_location_ui() -> dict:
    """
    Renders the simplified location selection panel for the Demo Mode.
    Returns latitude, longitude, and country.
    """
    st.write("### 🌐 Location Settings")
    st.info("Select the location to fetch historical solar radiation data (GHI).")

    countries = ["Netherlands 🇳🇱", "Germany 🇩🇪", "Argentina 🇦🇷", "Other"]
    
    # Initialize country session state if not existing
    if "demo_country" not in st.session_state:
        st.session_state["demo_country"] = "Netherlands 🇳🇱"
        
    country = st.selectbox(
        "Select Country:", 
        options=countries, 
        key="demo_country_select"
    )
    
    # Handle country change to reset lat/lon defaults if country changes
    if country != st.session_state["demo_country"]:
        st.session_state["demo_country"] = country
        geo_defaults = {
            "Netherlands 🇳🇱": {"lat": 52.3676, "lon": 4.9041},
            "Germany 🇩🇪":     {"lat": 52.5200, "lon": 13.4050},
            "Argentina 🇦🇷":  {"lat": -34.6037, "lon": -58.3816},
            "Other":          {"lat": 0.0, "lon": 0.0}
        }
        defaults = geo_defaults.get(country, geo_defaults["Other"])
        st.session_state["demo_lat"] = defaults["lat"]
        st.session_state["demo_lon"] = defaults["lon"]

    # Smart defaults fallback
    if "demo_lat" not in st.session_state:
        st.session_state["demo_lat"] = 52.3676
    if "demo_lon" not in st.session_state:
        st.session_state["demo_lon"] = 4.9041

    # Address search bar
    search_query = st.text_input(
        "🔍 Search Address or City:", 
        placeholder="e.g., Rotterdam, Berlin, Buenos Aires", 
        key="demo_search_query"
    )
    
    if search_query:
        try:
            headers = {'User-Agent': 'DRACBV_Energy_Advisory_Demo_App'}
            url = f"https://nominatim.openstreetmap.org/search?q={search_query}&format=json&limit=1"
            response = requests.get(url, headers=headers).json()
            if response:
                st.session_state["demo_lat"] = float(response[0]['lat'])
                st.session_state["demo_lon"] = float(response[0]['lon'])
                st.success(f"📍 Found: {response[0]['display_name']}")
            else:
                st.warning("Address not found. Please try a different query.")
        except Exception as e:
            st.error(f"Could not reach location service: {e}")

    # Manual inputs
    col_lat, col_lon = st.columns(2)
    latitude = col_lat.number_input(
        "Latitude (Breitengrad)", 
        value=st.session_state["demo_lat"], 
        format="%.6f",
        key="demo_lat_input"
    )
    longitude = col_lon.number_input(
        "Longitude (Längengrad)", 
        value=st.session_state["demo_lon"], 
        format="%.6f",
        key="demo_lon_input"
    )
    
    # Keep session states synced with numeric inputs
    st.session_state["demo_lat"] = latitude
    st.session_state["demo_lon"] = longitude

    # Interactive map toggle
    use_map = st.toggle("🗺️ Show Map", value=True, key="demo_map_toggle")
    
    if use_map:
        try:
            m = folium.Map(location=[st.session_state["demo_lat"], st.session_state["demo_lon"]], zoom_start=12)
            folium.Marker(
                [st.session_state["demo_lat"], st.session_state["demo_lon"]], 
                popup="Selected Location",
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)
            st_folium(m, height=250, use_container_width=True, key="demo_folium_map")
        except Exception:
            st.caption("Map load failed or coordinates out of range.")

    return {
        "country": country,
        "latitude": latitude,
        "longitude": longitude
    }
