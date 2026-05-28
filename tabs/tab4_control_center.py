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
    st.info("Manage your active scenarios. Export complete trees (Baseline + Variants) as .drac files.")
    
    if 'scenario_vault' not in st.session_state:
        st.session_state['scenario_vault'] = {}
    vault = st.session_state['scenario_vault']
    
    # --- 1. IMPORT SECTION ---
    st.write("### 📥 Import DRAC Archive (Trees & Baselines)")
    uploaded_drac = st.file_uploader("Upload a saved .drac archive", type=["drac"])
    if uploaded_drac:
        try:
            suggested_prefix = "[Import] "
            import_prefix = st.text_input("Optional prefix to avoid name collisions:", value=suggested_prefix)
            
            if st.button("🚀 Load Tree into Active Vault", type="primary", use_container_width=True):
                new_scenarios = parse_drac_import(uploaded_drac, import_prefix)
                st.session_state['scenario_vault'].update(new_scenarios)
                st.success(f"✅ Successfully imported {len(new_scenarios)} scenario(s)!")
                st.rerun() 
        except Exception as e:
            st.error(f"Import failed. File might be corrupted. Error: {e}")

    st.divider()

    # --- 2. STRUCTURED TREE-VIEW INVENTORY ---
    st.write("### 🗃️ Active Vault Inventory")
    if not vault:
        st.warning("Your vault is currently empty. Create profiles in the baseline tab or upload a backup.")
        return

    base_scenarios = [name for name, data in vault.items() if not data.get('parent') or data.get('parent') not in vault]
    
    for base_name in base_scenarios:
        base_data = vault[base_name]
        df = base_data.get('df')
        peak = df['consumption_kw'].max() if df is not None else 0.0
        
        with st.expander(f"🏢 MAIN SCENARIO: {base_name} ({base_data.get('data_source', 'Unknown')})"):
            c_inf, c_act = st.columns([3, 1])
            c_inf.write(f"**Max. Peak Load:** {peak:.1f} kW | **Grid Limit:** {base_data.get('grid_limit', 0.0):.1f} kW")
            
            # Find all children belonging to this baseline
            sub_scenarios = [name for name, data in vault.items() if data.get('parent') == base_name]
            
            # NEW: Package the entire tree (Base + all Subs)
            tree_to_export = {base_name: base_data}
            for sub in sub_scenarios:
                tree_to_export[sub] = vault[sub]
            
            # Action Buttons
            b_export = create_drac_export(tree_to_export)
            c_act.download_button("💾 Export Entire Tree", data=b_export, file_name=f"{base_name}_Tree.drac", mime="application/zip", key=f"exp_{base_name}", use_container_width=True)
            if c_act.button("🗑️ Delete Tree", key=f"del_{base_name}", use_container_width=True):
                del st.session_state['scenario_vault'][base_name]
                # Cascade delete sub-scenarios safely
                for sub in sub_scenarios:
                    if sub in st.session_state['scenario_vault']:
                        del st.session_state['scenario_vault'][sub]
                st.rerun()
                
            if sub_scenarios:
                st.write("---")
                st.write("🌿 **Associated Variants (Sub-Scenarios):**")
                
                for sub_name in sub_scenarios:
                    sub_data = vault[sub_name]
                    sub_df = sub_data.get('df')
                    sub_peak = sub_df['consumption_kw'].max() if sub_df is not None else 0.0
                    
                    with st.container(border=True):
                        cs_name, cs_inf, cs_act1, cs_act2 = st.columns([1.5, 2, 1, 1])
                        cs_name.write(f"↳ 📊 **{sub_name}**")
                        cs_inf.write(f"Peak: {sub_peak:.1f} kW | Limit: {sub_data.get('grid_limit', 0.0):.1f} kW")
                        
                        # Sub Actions (Export single variant)
                        sub_export = create_drac_export({sub_name: sub_data})
                        cs_act1.download_button("💾 Exp", data=sub_export, file_name=f"{sub_name}.drac", mime="application/zip", key=f"exp_{sub_name}")
                        if cs_act2.button("🗑️ Del", key=f"del_{sub_name}"):
                            del st.session_state['scenario_vault'][sub_name]
                            st.rerun()