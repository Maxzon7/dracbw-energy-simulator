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
from tabs.tab2_components.results_viewer import render_results_and_charts

from logic.energy_logic import simulate_battery_logic, simulate_generator_logic

# --- UNSERE NEUEN KLASSEN-TOOLS ---
from classes.models import SubScenario, FinancialParams
from logic.storage_manager import get_all_base_scenarios, get_base_scenario, add_sub_scenario

def render_tab2_scenarios():
    st.header("Scenario Simulation (Hardware Integration)")

    # 1. Tresor prüfen (Gibt es schon Klassen?)
    bases = get_all_base_scenarios()
    if not bases:
        st.warning("⚠️ Please generate and save a Baseline in Tab 1 first.")
        return

    # Dropdown für das Projekt
    base_names = [b.name for b in bases]
    selected_base_name = st.selectbox("### 📂 1. Select Project (Baseline)", base_names)
    active_base = get_base_scenario(selected_base_name)

    # Kugelsicherer Türsteher
    if active_base.original_profile is None:
        st.info(f"⚠️ Das Projekt '{selected_base_name}' hat noch keine Daten. Bitte in Tab 1 'Process & Save' klicken.")
        return

    # Daten direkt aus der Klasse ziehen
    baseline_df = active_base.original_profile.copy()
    grid_limit = active_base.base_tariff.contracted_capacity_kw
    project_metadata = {}
    res = 15

    st.divider()
    col_input, col_chart = st.columns([1, 2.5])

    with col_input:
        st.write("### 2. Configure System Technology")
        active_mode = st.session_state.get('active_sim_mode', "Battery (BESS) Only")
        valid_modes = ["Solar PV Only", "Battery (BESS) Only", "Generator Only", "Grid Upgrade Only", "Combined (All)"]
        scenario_mode = st.radio("Configuration:", valid_modes, index=valid_modes.index(active_mode if active_mode in valid_modes else "Battery (BESS) Only"))

        hw_draft = st.session_state.get('active_sim_params', {})

        with st.form(key=f"sim_form_{scenario_mode}"):
            params = {}
            if scenario_mode == "Solar PV Only":
                with st.expander("Configure Solar PV", True): params = render_solar_ui(selected_base_name)
            elif scenario_mode == "Battery (BESS) Only":
                with st.expander("Configure BESS", True): params = render_battery_ui(selected_base_name, grid_limit, hw_draft)
            elif scenario_mode == "Generator Only":
                with st.expander("Configure Generator", True): params = render_generator_ui(selected_base_name)
            elif scenario_mode == "Grid Upgrade Only":
                with st.expander("Configure Grid", True): params = render_grid_upgrade_ui(selected_base_name)
            else:
                with st.expander("Solar PV", False): params['solar'] = render_solar_ui(f"{selected_base_name}_c_sol")
                with st.expander("BESS", False): params['battery'] = render_battery_ui(f"{selected_base_name}_c_bat", grid_limit, hw_draft.get('battery', hw_draft))
                with st.expander("Generator", False): params['generator'] = render_generator_ui(f"{selected_base_name}_c_gen")

            with st.expander("🎨 Chart Colors", expanded=False):
                colors = {'raw': st.color_picker("Original", "#A9A9A9"), 'opt': st.color_picker("Optimized", "#00CC96"), 'soc': st.color_picker("SoC", "#636EFA"), 'act': st.color_picker("Action", "#FFA15A"), 'gen': st.color_picker("Generator", "#8B0000")}
                st.session_state['chart_colors'] = colors # Farben zwischenspeichern

            run_sim = st.form_submit_button("🔄 Calculate Preview", type="secondary", use_container_width=True)

        # ENGINE LOGIC (Bleibt unberührt!)
        if run_sim:
            with st.spinner("Processing physical interval math cascade..."):
                clean_base_df = baseline_df[['timestamp', 'consumption_kw']].copy()
                if scenario_mode == "Solar PV Only":
                    calculated_df = generate_solar_profile(clean_base_df, project_metadata, params)
                    calculated_df['final_grid_load_kw'] = calculated_df['net_load_kw']
                elif scenario_mode == "Battery (BESS) Only":
                    calculated_df = run_isolated_scenario(clean_base_df, "Battery (Peak Shaving)", params, grid_limit, res)
                elif scenario_mode == "Generator Only":
                    calculated_df = simulate_generator_logic(clean_base_df, grid_limit, params, res)
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


        # --- NEUE SPEICHER-LOGIK (Ersetzt die alte Draft & Clone UI!) ---
        if st.session_state.get('active_sim_results') is not None:
            st.divider()
            st.write("### 💾 Variante an Projekt anhängen")
            st.info("Bist du mit dem Chart rechts zufrieden? Speichere diese Konfiguration als Variante für das CFO-Cockpit.")

            szenario_name = st.text_input("Name für diese Lösung:", value=f"Option: {scenario_mode}")

            finanzen_aktiv = st.toggle("Finanzdaten berechnen? (Optional)")
            finanz_modul = None

            if finanzen_aktiv:
                with st.container():
                    col1, col2 = st.columns(2)
                    p = st.session_state['active_sim_params']
                    default_capex = 0.0

                    # Dynamische Kosten-Schätzung für ein besseres UX
                    if scenario_mode == "Battery (BESS) Only":
                        default_capex = float(p.get('capacity_kwh', 0) * 400)
                    elif scenario_mode == "Solar PV Only":
                        default_capex = float(p.get('system_size_kwp', 0) * 800)
                    elif scenario_mode == "Combined (All)":
                        default_capex = float(p.get('battery', {}).get('capacity_kwh', 0) * 400) + float(p.get('solar', {}).get('system_size_kwp', 0) * 800)

                    capex_input = col1.number_input("Hardware-Kaufpreis (€) [CAPEX]", value=default_capex, step=1000.0)
                    opex_input = col2.number_input("Jährliche Wartung (€) [OPEX]", value=float(default_capex*0.02), step=100.0)

                    finanz_modul = FinancialParams(capex=capex_input, opex_yearly=opex_input, lifespan_years=15)

            if st.button("🚀 Variante Speichern", type="primary", use_container_width=True):
                b_kwh, b_kw, s_kwp = 0.0, 0.0, 0.0
                p = st.session_state['active_sim_params']