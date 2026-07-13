# tabs/hub_menu.py
import streamlit as st
import pickle

def render_main_menu():
    """
    Renders the 'Hotel Lobby' (Project Hub). 
    Outsourced from app.py to keep the main file clean.
    """
    st.title("DRACBV Green Energy Solutions")
    st.markdown("### ⚡ Project Configuration Hub")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("Start a completely new energy analysis project.")
        new_project_name = st.text_input("Enter Project Name:", "My_New_Project")
        if st.button("🚀 Start Fresh Project", use_container_width=True):
            if new_project_name not in st.session_state['project_hub']:
                st.session_state['project_hub'][new_project_name] = {'scenario_vault': {}, 'active_scenario_name': None}
            st.session_state['active_project_name'] = new_project_name
            st.session_state['scenario_vault'] = st.session_state['project_hub'][new_project_name]['scenario_vault']
            st.session_state['active_scenario_name'] = st.session_state['project_hub'][new_project_name]['active_scenario_name']
            st.rerun()
            
    with col2:
        st.success("Resume an existing project from a saved configuration.")
        uploaded_file = st.file_uploader("Upload Configuration (.drac)", type=['drac'])
        if uploaded_file is not None:
            if st.button("📂 Load Project", use_container_width=True):
                try:
                    loaded_project_data = pickle.loads(uploaded_file.read())
                    project_name = uploaded_file.name.replace(".drac", "")
                    st.session_state['project_hub'][project_name] = loaded_project_data
                    st.session_state['active_project_name'] = project_name
                    st.session_state['scenario_vault'] = loaded_project_data.get('scenario_vault', {})
                    st.session_state['active_scenario_name'] = loaded_project_data.get('active_scenario_name', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load file. Error: {e}")
                
    with col3:
        st.warning("Load a predefined showcase scenario for demonstration.")
        if st.button("🧪 Try Demo Mode", use_container_width=True):
            st.session_state['is_demo_mode'] = True
            st.session_state['active_project_name'] = "Demo Mode"
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.subheader("📁 Your Active Projects (Current Session)")
    st.markdown("---")
    
    if not st.session_state['project_hub']:
        st.caption("No projects active in this session. Create or upload one above.")
    else:
        hub_cols = st.columns(3)
        for idx, (p_name, p_data) in enumerate(st.session_state['project_hub'].items()):
            with hub_cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### 🏢 {p_name}")
                    st.caption(f"Saved Scenarios: {len(p_data.get('scenario_vault', {}))}")
                    if st.button("✏️ Continue Editing", key=f"edit_{p_name}", use_container_width=True):
                        st.session_state['active_project_name'] = p_name
                        st.session_state['scenario_vault'] = p_data['scenario_vault']
                        st.session_state['active_scenario_name'] = p_data['active_scenario_name']
                        st.rerun()
                    
                    drac_bytes = pickle.dumps(p_data)
                    st.download_button("📥 Download .drac", data=drac_bytes, file_name=f"{p_name}.drac", mime="application/octet-stream", key=f"dl_{p_name}", use_container_width=True)
                    
                    if st.button("🗑️ Delete", key=f"del_{p_name}", use_container_width=True):
                        del st.session_state['project_hub'][p_name]
                        st.rerun()