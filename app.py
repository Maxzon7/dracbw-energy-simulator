import streamlit as st
import json
import os

#to run: python -m streamlit run MVP3/app.py

# Import the UI modules for each tab
from tabs.tab1_baseline import render_tab1_baseline
from tabs.tab2_scenarios import render_tab2_scenarios
from tabs.tab3_comparison import render_tab3_comparison
from tabs.tab4_control_center import render_tab4_control_center

def load_translations() -> dict:
    """
    Loads translation bundles from a external JSON file to decouple data from logic.
    """
    # Get the absolute path to the directory where app.py is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the absolute path to the translations file
    json_path = os.path.join(base_dir, "config", "translations.json")
    
    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)

def main():
    # Application configuration must be execution command number one
    st.set_page_config(page_title="Pro Energy Simulator", layout="wide")

    # Initialize translation data store within session state
    if 'translations' not in st.session_state:
        st.session_state['translations'] = load_translations()
    
    # --- HIER EINFÜGEN: Initialize Scenario Vault ---
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {} # Dictionary to hold our ScenarioConfig objects
        
    if 'active_scenario_name' not in st.session_state:
        st.session_state['active_scenario_name'] = None # Tracks which scenario is currently loaded
        
    if 'ui_slider_states' not in st.session_state:
        # A temporary dictionary to hold live slider movements before they are saved
        st.session_state['ui_slider_states'] = {
            'global': {},
            'monthly': {},
            'anomalies': []
        }
    # --- ENDE EINFÜGEN ---

    # --- LANGUAGE SELECTION ---
    st.sidebar.title("⚙️ Settings")
    # Extended language options mapping display string to ISO code
    languages = {
        "English 🇬🇧": "en", 
        "Deutsch 🇩🇪": "de",
        "Español 🇪🇸": "es",
        "Nederlands 🇳🇱": "nl"
    }
    sel_lang = st.sidebar.selectbox("Language / Sprache", list(languages.keys()), index=0)
    lang_code = languages[sel_lang]
    
    # Store the active language layer globally for all components
    st.session_state['t'] = st.session_state['translations'].get(lang_code, st.session_state['translations']["en"])
    t = st.session_state['t']
    
    # Header display elements
    st.title(t["title"])
    st.error(t["warning"])
    
    with st.expander(t["info_title"]):
        st.write(t["info_text"])
    
    #tab Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "Baseline", 
        "Scenarios", 
        "Comparison",
        "Control Center" # Neuer Tab!
    ])

    #route execuition
    with tab1:
        render_tab1_baseline()
    with tab2:
        render_tab2_scenarios()
    with tab3:
        render_tab3_comparison()
    with tab4:
        render_tab4_control_center()

if __name__ == "__main__":
    main()