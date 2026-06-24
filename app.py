import streamlit as st
import json
import os
import pickle  # WICHTIG: Erlaubt uns, komplexe DataFrames verlustfrei als .drac zu speichern

# Import the UI modules for each tab
from tabs.tab0_overview import render_tab0_overview  
from tabs.tab1_baseline import render_tab1_baseline
from tabs.tab2_scenarios import render_tab2_scenarios
from tabs.tab3_comparison import render_tab3_comparison
from tabs.tab4_control_center import render_tab4_control_center

def load_translations() -> dict:
    """Loads translation bundles from an external JSON file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, "config", "translations.json")
    with open(json_path, "r", encoding="utf-8") as file:
        return json.load(file)

def render_main_menu():
    """
    Renders the "Hotel Lobby" (Project Hub). 
    Shows active session projects and allows creating/uploading new ones.
    """
    st.title("DRACBV Green Energy Solutions")
    st.markdown("### ⚡ Project Configuration Hub")
    st.markdown("---")
    
    # --- ROW 1: Create or Load ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("Start a completely new energy analysis project.")
        new_project_name = st.text_input("Enter Project Name:", "My_New_Project")
        if st.button("🚀 Start Fresh Project", use_container_width=True):
            if new_project_name not in st.session_state['project_hub']:
                # Create a fresh, empty project blueprint
                st.session_state['project_hub'][new_project_name] = {
                    'scenario_vault': {},
                    'active_scenario_name': None
                }
            # Activate Project
            st.session_state['active_project_name'] = new_project_name
            # Load vault into working memory
            st.session_state['scenario_vault'] = st.session_state['project_hub'][new_project_name]['scenario_vault']
            st.session_state['active_scenario_name'] = st.session_state['project_hub'][new_project_name]['active_scenario_name']
            st.rerun()
            
    with col2:
        st.success("Resume an existing project from a saved configuration.")
        uploaded_file = st.file_uploader("Upload Configuration (.drac)", type=['drac'])
        if uploaded_file is not None:
            if st.button("📂 Load Project", use_container_width=True):
                try:
                    # Unpack the binary drac file
                    loaded_project_data = pickle.loads(uploaded_file.read())
                    project_name = uploaded_file.name.replace(".drac", "")
                    
                    # Store in Hub and activate
                    st.session_state['project_hub'][project_name] = loaded_project_data
                    st.session_state['active_project_name'] = project_name
                    
                    # Push to working memory
                    st.session_state['scenario_vault'] = loaded_project_data.get('scenario_vault', {})
                    st.session_state['active_scenario_name'] = loaded_project_data.get('active_scenario_name', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load .drac file. It might be corrupted. Error: {e}")
                
    with col3:
        st.warning("Load a predefined showcase scenario for demonstration.")
        if st.button("🧪 Try Demo Mode", use_container_width=True):
            st.session_state['project_hub']["Demo_Facility"] = {
                'scenario_vault': {}, # Here we could inject dummy data later
                'active_scenario_name': None
            }
            st.session_state['active_project_name'] = "Demo_Facility"
            st.session_state['scenario_vault'] = {}
            st.session_state['active_scenario_name'] = None
            st.rerun()

    # --- ROW 2: Active Session Projects (The List) ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("📁 Your Active Projects (Current Session)")
    st.markdown("---")
    
    if not st.session_state['project_hub']:
        st.caption("No projects active in this session. Create or upload one above.")
    else:
        # Create a grid layout for project cards
        hub_cols = st.columns(3)
        for idx, (p_name, p_data) in enumerate(st.session_state['project_hub'].items()):
            col = hub_cols[idx % 3]
            with col:
                with st.container(border=True):
                    st.markdown(f"#### 🏢 {p_name}")
                    scen_count = len(p_data.get('scenario_vault', {}))
                    st.caption(f"Saved Scenarios inside: {scen_count}")
                    
                    # Button 1: Jump back in
                    if st.button("✏️ Continue Editing", key=f"edit_{p_name}", use_container_width=True):
                        st.session_state['active_project_name'] = p_name
                        st.session_state['scenario_vault'] = p_data['scenario_vault']
                        st.session_state['active_scenario_name'] = p_data['active_scenario_name']
                        st.rerun()
                        
                    # Button 2: Download the whole project as .drac
                    # We serialize the project data dictionary
                    drac_bytes = pickle.dumps(p_data)
                    st.download_button(
                        label="📥 Download .drac", 
                        data=drac_bytes, 
                        file_name=f"{p_name}.drac", 
                        mime="application/octet-stream",
                        key=f"dl_{p_name}",
                        use_container_width=True
                    )
                    
                    # Button 3: Trash
                    if st.button("🗑️ Delete from Session", key=f"del_{p_name}", use_container_width=True):
                        del st.session_state['project_hub'][p_name]
                        st.rerun()


def render_workspace(t):
    """
    Renders the main project tabs (the actual working area) 
    only when a project is currently active.
    """
    active_name = st.session_state['active_project_name']
    st.title(f"{t['title']} | 📂 Project: [{active_name}]")
    st.error(t["warning"])
    
    with st.expander(t["info_title"]):
        st.write(t["info_text"])
    
    # Tab Navigation
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Project Overview", 
        "1️⃣ Baseline", 
        "2️⃣ Scenarios", 
        "3️⃣ Comparison",
        "⚙️ Data Management" # Renamed from Control Center
    ])

    with tab0:
        render_tab0_overview()
    with tab1:
        render_tab1_baseline()
    with tab2:
        render_tab2_scenarios()
    with tab3:
        render_tab3_comparison()
    with tab4:
        render_tab4_control_center()


def main():
    st.set_page_config(page_title="Pro Energy Simulator", layout="wide", page_icon="⚡")

    # Initialize translations
    if 'translations' not in st.session_state:
        st.session_state['translations'] = load_translations()
    
    # --- HUB STATE MANAGEMENT ---
    if 'project_hub' not in st.session_state:
        st.session_state['project_hub'] = {} 
        
    if 'active_project_name' not in st.session_state:
        st.session_state['active_project_name'] = None 

    # --- WORKSPACE STATE MANAGEMENT (For the active project) ---
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {} 
        
    if 'active_scenario_name' not in st.session_state:
        st.session_state['active_scenario_name'] = None 
        
    if 'ui_slider_states' not in st.session_state:
        st.session_state['ui_slider_states'] = {
            'global': {}, 'monthly': {}, 'anomalies': []
        }
        
    if 'enable_financials' not in st.session_state:
        st.session_state['enable_financials'] = True
    # ---------------------------------------

    st.sidebar.title("⚙️ Global Settings")
    
    languages = {
        "English 🇬🇧": "en", 
        "Deutsch 🇩🇪": "de",
        "Español 🇪🇸": "es",
        "Nederlands 🇳🇱": "nl"
    }
    sel_lang = st.sidebar.selectbox("Language / Sprache", list(languages.keys()), index=0)
    lang_code = languages[sel_lang]
    
    st.session_state['t'] = st.session_state['translations'].get(lang_code, st.session_state['translations']["en"])
    t = st.session_state['t']
    
    # --- DYNAMIC ROUTING ---
    if st.session_state['active_project_name'] is None:
        render_main_menu()
    else:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Project Controls")
        
        st.session_state['enable_financials'] = st.sidebar.toggle(
            "💰 Enable Financial Evaluation", 
            value=st.session_state['enable_financials']
        )
        
        st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
        
        # --- THE PANIC BUTTON (Save & Return to Hub) ---
        if st.sidebar.button("💾 Save & Close Project", type="primary", use_container_width=True):
            # Sync the current working memory back into the Hub before leaving
            p_name = st.session_state['active_project_name']
            st.session_state['project_hub'][p_name]['scenario_vault'] = st.session_state['scenario_vault']
            st.session_state['project_hub'][p_name]['active_scenario_name'] = st.session_state['active_scenario_name']
            
            # Clear active workspace
            st.session_state['active_project_name'] = None
            st.session_state['scenario_vault'] = {}
            st.session_state['active_scenario_name'] = None
            st.rerun() 
            
        render_workspace(t)

if __name__ == "__main__":
    main()