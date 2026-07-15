# app.py
import streamlit as st
import json
import os

# Import Navigation & UI modules
from tabs.hub_menu import render_main_menu  # <-- HIER IST DIE LOBBY JETZT!
from tabs.tab0_overview import render_tab0_overview  
from tabs.tab1_baseline import render_tab1_baseline
from tabs.tab2_scenarios import render_tab2_scenarios
from tabs.tab3_comparison import render_tab3_comparison
from tabs.tab4_control_center import render_tab4_control_center

def load_translations() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "config", "translations.json")
    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)

def render_workspace(t):
    active_name = st.session_state['active_project_name']
    st.title(f"{t['title']} | 📂 Project: [{active_name}]")
    
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Project Overview", "1️⃣ Baseline", "2️⃣ Scenarios", "3️⃣ Comparison", "⚙️ Data Management"
    ])
    with tab0: render_tab0_overview()
    with tab1: render_tab1_baseline()
    with tab2: render_tab2_scenarios()
    with tab3: render_tab3_comparison()
    with tab4: render_tab4_control_center()

def init_session_states():
    """Initializes all necessary session memory to avoid cluttering the main loop."""
    if 'translations' not in st.session_state: st.session_state['translations'] = load_translations()
    if 'project_hub' not in st.session_state: st.session_state['project_hub'] = {} 
    if 'active_project_name' not in st.session_state: st.session_state['active_project_name'] = None 
    if 'scenario_vault' not in st.session_state: st.session_state['scenario_vault'] = {} 
    if 'active_scenario_name' not in st.session_state: st.session_state['active_scenario_name'] = None 
    if 'ui_slider_states' not in st.session_state: st.session_state['ui_slider_states'] = {'global': {}, 'monthly': {}, 'anomalies': []}
    if 'enable_financials' not in st.session_state: st.session_state['enable_financials'] = False

def main():
    st.set_page_config(page_title="Pro Energy Simulator", layout="wide", page_icon="⚡")
    init_session_states()

    st.sidebar.title("⚙️ Global Settings")
    languages = {"English 🇬🇧": "en", "Deutsch 🇩🇪": "de", "Español 🇪🇸": "es", "Nederlands 🇳🇱": "nl"}
    sel_lang = st.sidebar.selectbox("Language", list(languages.keys()), index=0)
    st.session_state['t'] = st.session_state['translations'].get(languages[sel_lang], st.session_state['translations']["en"])
    
    # --- ROUTING (The Switch) ---
    if st.session_state['active_project_name'] is None:
        render_main_menu() # Calls the outsourced lobby
    elif st.session_state.get('is_demo_mode', False):
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Close Demo Mode", type="primary", use_container_width=True):
            st.session_state['active_project_name'] = None
            st.session_state['is_demo_mode'] = False
            st.rerun()
        
        from demo_mode.demo_main import render_demo_mode
        render_demo_mode()
    else:
        st.sidebar.markdown("---")
        st.session_state['enable_financials'] = st.sidebar.toggle("💰 Enable Financial Evaluation", value=st.session_state['enable_financials'])
        st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
        
        # In app.py innerhalb der main() Verzweigung bei "Save & Close Project":
        if st.sidebar.button("💾 Save & Close Project", type="primary", use_container_width=True):
            # Data is already maintained inline within project_hub via storage_manager
            st.session_state['active_project_name'] = None
            st.session_state['active_base_name'] = None
            st.session_state['scenario_vault'] = {}
            st.session_state['active_scenario_name'] = None
            st.rerun()
        
        render_workspace(st.session_state['t'])

if __name__ == "__main__":
    main()