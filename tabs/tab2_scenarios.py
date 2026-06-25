# tabs/tab2_scenarios.py
import streamlit as st
import pandas as pd
import copy  

# Sub-components imports
from tabs.tab2_components.solar_ui import render_solar_ui
from tabs.tab2_components.solar_logic import generate_solar_profile
from tabs.tab2_components.battery_ui import render_battery_ui
from tabs.tab2_components.generator_ui import render_generator_ui 
from tabs.tab2_components.scenario_engine import run_isolated_scenario
from tabs.tab2_components.grid_upgrade_ui import render_grid_upgrade_ui

from logic.energy_logic import simulate_battery_logic, simulate_generator_logic
from classes.models import SubScenario, FinancialParams
from logic.storage_manager import add_sub_scenario_to_active

# Neu ausgelagerte UI-Funktion NUR für Graphen und PDF
from tabs.tab2_components.results_viewer import render_results_and_charts

def render_tab2_scenarios():
    st.header("Scenario Simulation (Hardware Integration)")
    
    if 'scenario_vault' not in st.session_state or not st.session_state['scenario_vault']:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return
        
    vault = st.session_state['scenario_vault']
    selected_name = st.selectbox("### 📂 1. Select Scenario to View or Edit", list(vault.keys()))
    current_item = vault[selected_name]

    parent_name = current_item.get('parent')
    is_variant_mode = parent_name and parent_name in vault
    base_data = vault[parent_name] if is_variant_mode else current_item
    
    # --- DER KUGELSICHERE TÜRSTEHER ---
    # Blockiert sofort, wenn das DataFrame noch leer (None) ist!
    if base_data.get('df') is None:
        st.info(f"⚠️ The data for '{selected_name}' is still empty. Please go back to '1️⃣ Baseline', configure your data, and click 'Process & Save Baseline Profile' first.")
        return
    # --------------------------------------
    
    baseline_df = base_data['df'].copy()
    grid_limit = base_data.get('grid_limit', 120.0)
    project_metadata = base_data.get('params', {}).get('project_metadata', {})
    res = base_data.get('params', {}).get('resolution', 15)
    report_name = st.session_state.get('report_name', f"Report_{selected_name}")

    # Load previously saved state
    if st.session_state.get('last_selected_scen_tab2') != selected_name:
        st.session_state['last_selected_scen_tab2'] = selected_name
        if 'loaded_params' not in st.session_state: st.session_state['loaded_params'] = {}
        
        if is_variant_mode:
            st.session_state['active_sim_results'] = current_item['df']
            st.session_state['active_sim_mode'] = current_item.get('data_source', 'Battery (BESS) Only')
            st.session_state['active_sim_params'] = current_item['params'].get('hardware_params', {})
            st.session_state['loaded_params']['hardware_params'] = st.session_state['active_sim_params']
        else:
            st.session_state['active_sim_results'] = None
            st.session_state['active_sim_mode'] = "Battery (BESS) Only"
            st.session_state['active_sim_params'] = {}
            st.session_state['loaded_params']['hardware_params'] = {}
        st.rerun()

    st.divider()
    col_input, col_chart = st.columns([1, 2.5])
    
    with col_input:
        st.write("### 2. Configure System Technology")
        active_mode = st.session_state.get('active_sim_mode', "Battery (BESS) Only")
        valid_modes = ["Solar PV Only", "Battery (BESS) Only", "Generator Only", "Grid Upgrade Only", "Combined (All)"]
        scenario_mode = st.radio("Configuration:", valid_modes, index=valid_modes.index(active_mode if active_mode in valid_modes else "Battery (BESS) Only"))
        
        hw_draft = st.session_state.get('loaded_params', {}).get('hardware_params', {}) or {}
        
        with st.form(key=f"sim_form_{scenario_mode}"):
            params = {}
            if scenario_mode == "Solar PV Only":
                with st.expander("Configure Solar PV", True): params = render_solar_ui(selected_name)
            elif scenario_mode == "Battery (BESS) Only":
                with st.expander("Configure BESS", True): params = render_battery_ui(selected_name, grid_limit, hw_draft)
            elif scenario_mode == "Generator Only":
                with st.expander("Configure Generator", True): params = render_generator_ui(selected_name)
            elif scenario_mode == "Grid Upgrade Only":
                with st.expander("Configure Grid", True): params = render_grid_upgrade_ui(selected_name)
            else: 
                with st.expander("Solar PV", False): params['solar'] = render_solar_ui(f"{selected_name}_c_sol")
                with st.expander("BESS", False): params['battery'] = render_battery_ui(f"{selected_name}_c_bat", grid_limit, hw_draft.get('battery', hw_draft))
                with st.expander("Generator", False): params['generator'] = render_generator_ui(f"{selected_name}_c_gen")

            with st.expander("🎨 Chart Colors", expanded=False):
                colors = {'raw': st.color_picker("Original", "#A9A9A9"), 'opt': st.color_picker("Optimized", "#00CC96"), 'soc': st.color_picker("SoC", "#636EFA"), 'act': st.color_picker("Action", "#FFA15A"), 'gen': st.color_picker("Generator", "#8B0000")}
            
            run_sim = st.form_submit_button("🔄 Calculate Preview", type="secondary", use_container_width=True)

        # ENGINE LOGIC
        if run_sim:
            with st.spinner("Processing physical interval math cascade..."):
                clean_base_df = baseline_df[['timestamp', 'consumption_kw']].copy()
                if scenario_mode == "Solar PV Only":
                    calculated_df = generate_solar_profile(clean_base_df, project_metadata, params)
                    calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                elif scenario_mode == "Battery (BESS) Only": calculated_df = run_isolated_scenario(clean_base_df, "Battery (Peak Shaving)", params, grid_limit, res)
                elif scenario_mode == "Generator Only": calculated_df = simulate_generator_logic(clean_base_df, grid_limit, params, res)
                elif scenario_mode == "Grid Upgrade Only":
                    calculated_df = clean_base_df.copy()
                    calculated_df['final_grid_load_kw'] = calculated_df['consumption_kw']
                else:
                    df_1 = generate_solar_profile(clean_base_df, project_metadata, params['solar'])
                    df_2 = simulate_battery_logic(df_1, grid_limit, params['battery'], res)
                    calculated_df = simulate_generator_logic(df_2, grid_limit, params['generator'], res)
                
                st.session_state['active_sim_results'] = calculated_df
                st.session_state['active_sim_mode'] = scenario_mode
                st.session_state['active_sim_params'] = params

        # DRAFT MONITOR
        is_draft = False
        active_prm = st.session_state.get('active_sim_params')
        active_mod = st.session_state.get('active_sim_mode')
        
        if active_prm and active_mod:
            if active_mod != current_item.get('data_source') or active_prm != current_item.get('params', {}).get('hardware_params', {}):
                is_draft = True

        if is_draft:
            st.warning("⚠️ **Unsaved Preview!**\nChanges are a temporary draft. Click below to securely save.")
            if st.button("💾 Update Existing" if is_variant_mode else "💾 Save as New Variant", type="primary", use_container_width=True):
                target_name = selected_name if is_variant_mode else f"{selected_name} + {active_mod.split(' ')[0]}"
                vault[target_name] = {
                    "df": st.session_state['active_sim_results'],
                    "parent": selected_name if not is_variant_mode else parent_name,
                    "data_source": active_mod,
                    "grid_limit": active_prm.get("new_grid_limit_kw", grid_limit) if active_mod == "Grid Upgrade Only" else grid_limit,
                    "params": {"is_hardware": True, "hardware_params": active_prm}
                }
                st.session_state['scenario_vault'] = vault
                st.session_state['last_selected_scen_tab2'] = target_name
                st.rerun()

    # RENDERING VISUALS 
    if st.session_state.get('active_sim_results') is not None:
        with col_chart:
            render_results_and_charts(
                st.session_state['active_sim_results'], baseline_df, grid_limit, res, 
                st.session_state['active_sim_mode'], st.session_state.get('active_sim_params', {}), 
                project_metadata, selected_name, is_draft, colors, report_name
            )
            
        # CLONE UI
        with col_input:
            st.divider()
            st.write("### 💾 Create a Copy (Optional)")
            st.info("Want to keep this setup and experiment with alternatives? Save it as a new copy below.")
            
            sub_scenario_name = st.text_input("Name this Copy:", value=f"{selected_name}_Copy")
            
            name_exists = sub_scenario_name in vault
            save_disabled = False
            vault_button_text = "🚀 Save as New Copy"
            
            if name_exists:
                st.warning(f"⚠️ A variant named '{sub_scenario_name}' already exists.")
                if not st.checkbox("Confirm: Overwrite", value=False):
                    save_disabled = True
                else:
                    vault_button_text = "⚠️ OVERWRITE"
            
            if is_draft:
                st.error("Please commit your current draft before duplicating.")
            else:
                if st.button(vault_button_text, type="primary", use_container_width=True, disabled=save_disabled):
                    vault[sub_scenario_name] = copy.deepcopy(vault[selected_name])
                    st.session_state['scenario_vault'] = vault
                    st.success(f"✅ Copy '{sub_scenario_name}' has been successfully created!")
                    st.rerun()



def render_new_subscenario_bridge(aktuelles_batterie_kwh: float, aktuelles_batterie_kw: float, simuliertes_df: pd.DataFrame):
    """
    Diese Funktion unten in Tab 2 (oder in die Sidebar) packen.
    Sie schnappt sich die Werte aus deinen bestehenden UI-Reglern.
    """
    st.divider()
    st.subheader("💾 Lösungs-Ansatz speichern")
    
    szenario_name = st.text_input("Name für diese Lösung (z.B. 'Große Batterie')", value="Option 1: Batterie")
    
    # === DER MAGISCHE SCHALTER ===
    finanzen_aktiv = st.toggle("Finanzdaten für dieses Setup berechnen? (Optional)")
    
    finanz_modul = None # Standardmäßig leer!
    
    if finanzen_aktiv:
        with st.container():
            st.info("Trage hier die geschätzten Kosten ein:")
            col1, col2 = st.columns(2)
            # Eine kleine Rechnung, um den User zu unterstützen (z.B. 400€ pro kWh)
            default_capex = float(aktuelles_batterie_kwh * 400)
            capex_input = col1.number_input("Hardware-Kaufpreis (€) [CAPEX]", value=default_capex, step=1000.0)
            opex_input = col2.number_input("Jährliche Wartung (€) [OPEX]", value=float(default_capex*0.02), step=100.0) # ca. 2%
            
            # Wir erstellen das Modul
            finanz_modul = FinancialParams(
                capex=capex_input, 
                opex_yearly=opex_input,
                lifespan_years=15
            )
            
    if st.button("Diesen Ansatz zum Vergleich hinzufügen"):
        # 1. Wir bauen das Kind zusammen
        neues_sub = SubScenario(
            name=szenario_name,
            battery_kwh=aktuelles_batterie_kwh,
            battery_kw=aktuelles_batterie_kw,
            simulated_profile=simuliertes_df, # Das fertige Ergebnis deiner Physik-Engine
            financials=finanz_modul # Hier steckt jetzt entweder None oder das Geld drin!
        )
        
        # 2. Ab an den Parent heften!
        add_sub_scenario_to_active(neues_sub)