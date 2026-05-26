# tabs/tab4_control_center.py
import streamlit as st
from logic.storage_manager import create_drac_export, parse_drac_import

def render_tab4_control_center():
    """
    Renders the central hub for scenario management. 
    Handles importing, exporting (.drac), viewing, and deleting vault entries.
    """
    st.write("## 🗄️ Scenario Control Center")
    st.info("Manage your locally stored scenarios. Export them to your USB drive as a .drac file for client meetings, or import previous sessions.")
    
    # Ensure the vault exists
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {}

    vault = st.session_state['scenario_vault']
    
    # ==========================================
    # --- 1. IMPORT SECTION (Drag & Drop) ---
    # ==========================================
    st.write("### 📥 Import Scenario")
    uploaded_drac = st.file_uploader("Upload a .drac backup file", type=["drac"])
    
    if uploaded_drac:
        try:
            # We use the original filename (minus extension) as a suggestion
            suggested_name = uploaded_drac.name.replace(".drac", "")
            import_name = st.text_input("Name for imported scenario:", value=suggested_name)
            
            if st.button("🚀 Load into Vault", type="primary"):
                rebuilt_scenario = parse_drac_import(uploaded_drac)
                st.session_state['scenario_vault'][import_name] = rebuilt_scenario
                st.success(f"✅ Successfully imported '{import_name}'!")
                st.rerun() # Refresh page to show the new scenario below
        except Exception as e:
            st.error(f"Failed to read .drac file. It might be corrupted. Error: {e}")

    st.divider()

    # ==========================================
    # --- 2. VAULT INVENTORY (Accordion) ---
    # ==========================================
    st.write(f"### 🗃️ Active Vault Inventory ({len(vault)} Scenarios)")
    
    if not vault:
        st.warning("Your vault is currently empty. Generate a profile in Tab 1 or upload a .drac file above.")
        return

    # Iterate through all saved scenarios
    for scen_name, scen_data in vault.items():
        # Get basic metrics for the quick overview
        data_source = scen_data.get('data_source', 'Unknown')
        df = scen_data.get('df')
        
        peak_load = df['consumption_kw'].max() if df is not None else 0.0
        grid_limit = scen_data.get('grid_limit', 0.0)
        
        # Display the accordion
        with st.expander(f"📁 {scen_name} (Source: {data_source})"):
            col_info, col_actions = st.columns([3, 1])
            
            with col_info:
                st.write(f"**Max Peak Load:** {peak_load:.1f} kW")
                st.write(f"**Target Grid Limit:** {grid_limit:.1f} kW")
                if "anomalies" in scen_data and scen_data["anomalies"]:
                    st.write(f"**Active Anomalies:** {len(scen_data['anomalies'])}")
                    
            with col_actions:
                # Export Button (Generates the .drac file dynamically)
                binary_data = create_drac_export(scen_data)
                st.download_button(
                    label="💾 Export (.drac)",
                    data=binary_data,
                    file_name=f"{scen_name}.drac",
                    mime="application/zip",
                    use_container_width=True,
                    key=f"dl_{scen_name}"
                )
                
                # Delete Button (Throws it out of the vault)
                if st.button("🗑️ Delete", use_container_width=True, key=f"del_{scen_name}"):
                    del st.session_state['scenario_vault'][scen_name]
                    st.rerun()