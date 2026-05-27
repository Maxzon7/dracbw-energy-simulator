# tabs/tab4_control_center.py
import streamlit as st
import pandas as pd
from logic.storage_manager import create_drac_export, parse_drac_import

def render_tab4_control_center():
    """
    Renders the central hub for scenario management. 
    Displays a structured tree-view grouping sub-scenarios under their parent baselines.
    """
    st.write("## 🗄️ Scenario Control Center")
    st.info("Manage your active scenarios. Export them as .drac files for client meetings or upload backups.")
    
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {}
    vault = st.session_state['scenario_vault']
    
    # --- 1. IMPORT SECTION ---
    st.write("### 📥 Import DRAC Backup")
    uploaded_drac = st.file_uploader("Upload a saved .drac scenario file", type=["drac"])
    if uploaded_drac:
        try:
            suggested_name = uploaded_drac.name.replace(".drac", "")
            import_name = st.text_input("Scenario name for import:", value=suggested_name)
            if st.button("🚀 Load into Active Vault", type="primary", use_container_width=True):
                st.session_state['scenario_vault'][import_name] = parse_drac_import(uploaded_drac)
                st.success(f"✅ '{import_name}' successfully imported!")
                st.rerun() 
        except Exception as e:
            st.error(f"Import failed. File might be corrupted. Error: {e}")

    st.divider()

    # --- 2. STRUCTURED TREE-VIEW INVENTORY ---
    st.write("### 🗃️ Active Vault Inventory")
    if not vault:
        st.warning("Your vault is currently empty. Create profiles in the baseline tab or upload a backup.")
        return

    # Sort into Baselines (or Orphans) and Sub-Scenarios safely
    base_scenarios = [name for name, data in vault.items() if not data.get('parent') or data.get('parent') not in vault]
    
    for base_name in base_scenarios:
        base_data = vault[base_name]
        df = base_data.get('df')
        peak = df['consumption_kw'].max() if df is not None else 0.0
        
        # Main Accordion for the Baseline
        with st.expander(f"🏢 MAIN SCENARIO: {base_name} ({base_data.get('data_source', 'Unknown')})"):
            c_inf, c_act = st.columns([3, 1])
            c_inf.write(f"**Max. Peak Load:** {peak:.1f} kW | **Grid Limit:** {base_data.get('grid_limit', 0.0):.1f} kW")
            
            # Action Buttons
            b_export = create_drac_export(base_data)
            c_act.download_button("💾 Export", data=b_export, file_name=f"{base_name}.drac", mime="application/zip", key=f"exp_{base_name}", use_container_width=True)
            if c_act.button("🗑️ Delete", key=f"del_{base_name}", use_container_width=True):
                del st.session_state['scenario_vault'][base_name]
                st.rerun()
                
            # Find all children belonging to this baseline
            sub_scenarios = [name for name, data in vault.items() if data.get('parent') == base_name]
            
            if sub_scenarios:
                st.write("---")
                st.write("🌿 **Associated Variants (Sub-Scenarios):**")
                
                for sub_name in sub_scenarios:
                    sub_data = vault[sub_name]
                    sub_df = sub_data.get('df')
                    sub_peak = sub_df['consumption_kw'].max() if sub_df is not None else 0.0
                    
                    # Inner container for visual nesting
                    with st.container(border=True):
                        cs_name, cs_inf, cs_act1, cs_act2 = st.columns([1.5, 2, 1, 1])
                        cs_name.write(f"↳ 📊 **{sub_name}**")
                        cs_inf.write(f"Peak: {sub_peak:.1f} kW | Limit: {sub_data.get('grid_limit', 0.0):.1f} kW")
                        
                        # Sub Actions
                        sub_export = create_drac_export(sub_data)
                        cs_act1.download_button("💾 Exp", data=sub_export, file_name=f"{sub_name}.drac", mime="application/zip", key=f"exp_{sub_name}")
                        if cs_act2.button("🗑️ Del", key=f"del_{sub_name}"):
                            del st.session_state['scenario_vault'][sub_name]
                            st.rerun()