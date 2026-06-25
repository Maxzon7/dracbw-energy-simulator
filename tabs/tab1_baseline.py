# tabs/tab1_baseline.py
import streamlit as st
import pandas as pd

from classes.models import BaseScenario, Tariff
from logic.storage_manager import save_base_scenario

# UI Components imports
from tabs.tab1_components.upload import render_upload_ui
from tabs.tab1_components.synthetic_load import render_synthetic_load_ui
from tabs.tab1_components.project_params import render_project_params
from tabs.tab1_components.financial_ui import render_preset_selector, render_financial_inputs
from tabs.tab1_components.chart import render_baseline_chart

# Validation & Save imports
from tabs.tab1_components.validation_ui import validate_and_process_data
from tabs.tab1_components.validation_components.save_handler import save_profile_to_vault

def render_tab1_baseline():
    st.header("Baseline Data Configuration")
    
    vault = st.session_state.get('scenario_vault', {})
    baselines = [k for k, v in vault.items() if not v.get('parent')]
    
    # --- BASELINE SELECTION OR CREATION ---
    col_sel, col_new = st.columns([2, 1])
    with col_sel:
        if baselines:
            active_baseline = st.selectbox("Select Active Baseline to Edit:", baselines)
        else:
            st.info("No baseline profiles exist yet. Create one below.")
            active_baseline = "New_Baseline"
            
    with col_new:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("➕ Create New Baseline", use_container_width=True):
            new_name = f"Baseline_{len(baselines)+1}"
            vault[new_name] = {'df': None, 'params': {}}
            st.session_state['scenario_vault'] = vault
            st.rerun()

    if not baselines and active_baseline == "New_Baseline":
        vault["New_Baseline"] = {'df': None, 'params': {}}
        st.session_state['scenario_vault'] = vault

    st.divider()

    # --- 1. DAS REAKTIVE AUTOFILL-DROPDOWN (Out of Form) ---
    st.write("### ⚙️ 1. Grid Tariff Autofill")
    preset_label, preset_data = render_preset_selector()
    
    st.divider()
    
    # --- 2. DATENQUELLE (Out of Form) ---
    st.write("### 📂 2. Data Source Configuration")
    data_source = st.radio("Select Data Source:", ["Upload CSV", "Generate Synthetic Load"], horizontal=True)
    
    saved_params = vault[active_baseline].get('params', {})
    uploaded_file, filtered_df, upload_params = None, None, {}
    syn_params = {}
    
    if data_source == "Upload CSV":
        uploaded_file, filtered_df, upload_params = render_upload_ui(active_baseline, saved_params)
    else:
        syn_params = render_synthetic_load_ui(active_baseline)

    st.divider()

    # --- 3. DIE SCHALLDICHTE KABINE (Das st.form nur für Parameter & Finanzen) ---
    st.write("### 📊 3. Project Meta & Financial Configuration")
    
    with st.form("baseline_form"):
        
        # HIER IST DER FIX: Reihenfolge der Argumente umgedreht! (Wörterbuch zuerst, String danach)
        proj_params = render_project_params(saved_params, active_baseline)
        
        st.divider()
        saved_fin = saved_params.get('financial_metadata', {})
        working_fin = saved_fin.copy()
        if preset_data:
            working_fin.update(preset_data)
            working_fin['tariff_mode'] = preset_label
            
        fin_params = render_financial_inputs(working_fin)
        
        st.divider()
        submit_btn = st.form_submit_button("💾 Process & Save Baseline Profile", type="primary", use_container_width=True)
        
    # --- 4. SAVE EXECUTION (After Form Submit) ---
    if submit_btn:
        with st.spinner("Processing energy profile & validating limits..."):
            df, is_valid, msg = validate_and_process_data(
                data_source, uploaded_file, upload_params, syn_params, proj_params
            )
            
            if data_source == "Upload CSV" and filtered_df is not None and not filtered_df.empty:
                df = filtered_df
                is_valid = True
            
            if is_valid and df is not None:
                final_params = {
                    "data_source": data_source,
                    "resolution": upload_params.get('resolution', 15) if data_source == "Upload CSV" else 15,
                    "project_metadata": proj_params,
                    "financial_metadata": fin_params
                }
                
                success = save_profile_to_vault(
                    vault, active_baseline, df, final_params, proj_params.get('grid_limit_kw', 120.0)
                )
                
                if success:
                    st.session_state['scenario_vault'] = vault
                    st.success(f"✅ Baseline '{active_baseline}' successfully saved with active tariffs!")
                    st.rerun() 
            else:
                st.error(f"Validation failed: {msg}")

    # --- 5. CHART RENDERING ---
    if vault[active_baseline].get('df') is not None:
        st.divider()
        st.write(f"### 📈 Current Profile: {active_baseline}")
        render_baseline_chart(
            vault[active_baseline]['df'], 
            vault[active_baseline].get('grid_limit', proj_params.get('grid_limit_kw', 120.0))
        )

        render_new_baseline_bridge(vault[active_baseline]['df'])



def render_new_baseline_bridge(hochgeladenes_df: pd.DataFrame):
    """
    Diese Funktion einfach ganz unten in Tab 1 aufrufen. 
    Sie baut das Fundament für unser neues Klassensystem, stört aber den alten Code nicht.
    """
    st.divider()
    st.subheader("🏗️ Schritt 2: Projekt-Fundament für Finanz-Analyse sichern")
    
    with st.form("basis_szenario_form"):
        col1, col2 = st.columns(2)
        with col1:
            projekt_name = st.text_input("Name des Standorts/Projekts", value="Werk Hamburg 2026")
        
        with col2:
            # Hier simulieren wir die Tarifauswahl. Später kann das aus deiner JSON kommen.
            tarif_wahl = st.selectbox(
                "Aktueller Netztarif", 
                ["Stedin Grootverbruik", "Enexis GTO", "Eigener Tarif"]
            )
            
        submitted = st.form_submit_button("Projekt & Tarif bestätigen")
        
        if submitted:
            # 1. Wir bauen den Tarif zusammen (Dummy-Werte für den Anfang)
            if tarif_wahl == "Stedin Grootverbruik":
                gewählter_tarif = Tariff(name="Stedin 2026", contracted_capacity_kw=500, fixed_costs_per_year=2000, price_per_kw_peak=45.0)
            else:
                gewählter_tarif = Tariff(name="Standard", contracted_capacity_kw=0, fixed_costs_per_year=0, price_per_kw_peak=30.0)
            
            # 2. Wir packen alles in unseren neuen Klassen-Ordner
            neues_basis_projekt = BaseScenario(
                name=projekt_name,
                original_profile=hochgeladenes_df, # Das DataFrame aus deinem bisherigen Code!
                base_tariff=gewählter_tarif
            )
            
            # 3. Ab in den Tresor!
            save_base_scenario(neues_basis_projekt)
            st.success(f"✅ Projekt '{projekt_name}' mit Tarif '{gewählter_tarif.name}' wurde erfolgreich im Hintergrund angelegt!")