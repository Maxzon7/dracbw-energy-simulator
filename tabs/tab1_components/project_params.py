

# tabs/tab1_components/project_params.py
import streamlit as st

def render_project_params(loaded_metadata: dict, active_scenario: str) -> dict:
    """
    Renders the UI for global project parameters and grid constraints.
    Uses dynamic keys based on the active_scenario to ensure proper state switching.
    """
    with st.expander("📝 Enter General Project Data", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Project Name / Company", 
                value=loaded_metadata.get('project_name', ""), 
                key=f"proj_name_{active_scenario}"
            )
            
            # Country dropdown with safe indexing
            countries = ["Netherlands 🇳🇱", "Germany 🇩🇪", "Argentina 🇦🇷", "Other"]
            default_country = loaded_metadata.get('country', "Netherlands 🇳🇱")
            country_idx = countries.index(default_country) if default_country in countries else 0
            country = st.selectbox("Country", options=countries, index=country_idx, key=f"country_{active_scenario}")
            
            # Sectors dropdown
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

    # Return the dictionary to be stored in the session state overarching package
    return {
        "project_name": project_name,
        "country": country,
        "sector": sector,
        "grid_operator": grid_operator,
        "voltage_level": voltage_level,
        "strict_zero_export": strict_zero_export
    }