# tabs/tab1_baseline.py
import streamlit as st
import pandas as pd

# --- NEUE KLASSEN-IMPORTS (Fix für den ImportError) ---
from classes.models import Tariff, BaseScenario
from logic.storage_manager import (
    get_all_base_scenarios,
    create_empty_base_scenario,
    save_profile_to_base,
    get_base_scenario
)

# UI Components imports
from tabs.tab1_components.upload import render_upload_ui
from tabs.tab1_components.synthetic_load import render_synthetic_load_ui
from tabs.tab1_components.manual import render_manual_builder
from tabs.tab1_components.project_params import render_project_params
from tabs.tab1_components.financial_ui import render_preset_selector, render_financial_inputs, render_baseline_invoice_summary
from tabs.tab1_components.chart import render_baseline_chart
from tabs.tab1_components.validation_ui import validate_and_process_data

def render_tab1_baseline():
    st.header("Baseline Data Configuration")
    
    # ==========================================
    # 1. DATEN DIREKT AUS DEM NEUEN TRESOR HOLEN
    # ==========================================
    alle_basis_projekte = get_all_base_scenarios()
    baselines = [proj.name for proj in alle_basis_projekte]
    
    col_sel, col_new = st.columns([2, 1])
    with col_sel:
        if baselines:
            active_baseline_name = st.selectbox("Select Active Baseline to Edit:", baselines)
            st.session_state.active_base_name = active_baseline_name
        else:
            st.info("No baseline profiles exist yet. Create one below.")
            active_baseline_name = "New_Baseline"
            
    with col_new:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("➕ Create New Baseline", use_container_width=True):
            new_name = f"Baseline_{len(baselines)+1}"
            
            # --- DER MAGISCHE KLASSEN-AUFRUF (Ersetzt das alte Dictionary!) ---
            create_empty_base_scenario(new_name)
            st.rerun()

    # Fallback, falls noch gar keins existiert
    if not baselines and active_baseline_name == "New_Baseline":
        create_empty_base_scenario("New_Baseline")

    # Wir holen uns das tatsächliche Objekt, um damit zu arbeiten
    active_scenario_obj = get_base_scenario(active_baseline_name)

    # Load saved metadata
    saved_params = active_scenario_obj.metadata if active_scenario_obj and active_scenario_obj.metadata else {}

    st.divider()

    # --- 1. GRID CONTRACT / TARIFF MODE CONFIGURATION ---
    st.write("### ⚙️ 1. Grid Tariff & Contract Configuration")
    
    saved_mode = saved_params.get('grid_contract_mode', "Real Contract Preset")
    contract_modes = [
        "Real Contract Preset", 
        "Generic AC Connection Tier", 
        "Generic Grid Limit (No Contract)", 
        "No Contract (Consumption Only)"
    ]
    mode_idx = contract_modes.index(saved_mode) if saved_mode in contract_modes else 0
    contract_mode = st.radio(
        "Select Grid Contract Mode:",
        contract_modes,
        index=mode_idx,
        key=f"grid_contract_mode_{active_baseline_name}"
    )

    preset_label = "Custom"
    preset_data = {}

    if contract_mode == "Real Contract Preset":
        saved_preset = saved_params.get('financial_metadata', {}).get('tariff_mode', "🛠️ Custom Tariff")
        if saved_preset in ["🛠️ Manual Custom Tariff", "🛠️ Volatile Monthly Custom Tariff"]:
            saved_preset = "🛠️ Custom Tariff"
        preset_label, preset_data = render_preset_selector(saved_preset)
    elif contract_mode == "Generic AC Connection Tier":
        from tabs.tab1_components.financial_ui import get_generic_ac_presets
        ac_presets = get_generic_ac_presets()
        ac_keys = list(ac_presets.keys())
        saved_ac_key = saved_params.get('generic_ac_key', "AC4 (3x80A - 55 kW)")
        ac_idx = ac_keys.index(saved_ac_key) if saved_ac_key in ac_keys else 3
        selected_ac_key = st.selectbox("Select Generic AC Tier:", ac_keys, index=ac_idx, key=f"ac_tier_{active_baseline_name}")
        preset_label = selected_ac_key
        preset_data = ac_presets[selected_ac_key]
    elif contract_mode == "Generic Grid Limit (No Contract)":
        preset_label = "Generic Limit"
        preset_data = {
            "fixed_annual_connection_fee": 0.0,
            "fixed_annual_transport_fee": 0.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.20,
            "energy_price_laag_per_kwh": 0.15,
            "contracted_capacity_kw": float(active_scenario_obj.base_tariff.contracted_capacity_kw) if (active_scenario_obj and active_scenario_obj.base_tariff and active_scenario_obj.base_tariff.contracted_capacity_kw > 0) else 100.0,
            "tariff_mode": "Generic Limit"
        }
    elif contract_mode == "No Contract (Consumption Only)":
        preset_label = "None (Consumption Only)"
        preset_data = {
            "fixed_annual_connection_fee": 0.0,
            "fixed_annual_transport_fee": 0.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.0,
            "energy_price_laag_per_kwh": 0.0,
            "contracted_capacity_kw": 0.0,
            "tariff_mode": "None (Consumption Only)"
        }

    if st.session_state.get('enable_financials', False) and contract_mode == "Real Contract Preset" and preset_label == "🛠️ Custom Tariff":
        from tabs.tab3_components.tarrif_calc import render_tariff_builder_ui
        render_tariff_builder_ui()
        st.write("")

    include_financials = st.session_state.get('enable_financials', False)

    if 'current_financial_metadata' not in st.session_state:
        st.session_state['current_financial_metadata'] = {}
    if preset_data:
        st.session_state['current_financial_metadata'].update(preset_data)
    st.session_state['current_financial_metadata']['tariff_mode'] = preset_label

    st.divider()

    # --- 2. DATENQUELLE ---
    st.write("### 📂 2. Data Source Configuration")
    ds_options = [
        "12-Month Consumption & Peak (Simplified)",
        "Upload CSV",
        "Generate Synthetic Load",
        "Advanced Manual Generator"
    ]
    saved_ds = saved_params.get('data_source', "12-Month Consumption & Peak (Simplified)")
    if saved_ds == "CSV":
        saved_ds = "Upload CSV"
    elif saved_ds == "Synthetic":
        saved_ds = "Generate Synthetic Load"
        
    ds_idx = ds_options.index(saved_ds) if saved_ds in ds_options else 0

    data_source = st.radio(
        "Select Data Source:", 
        options=ds_options,
        index=ds_idx,
        horizontal=True,
        key=f"data_source_{active_baseline_name}"
    )

    # Platzhalter für UI-Kompatibilität
    uploaded_file, filtered_df, upload_params = None, None, {}
    syn_params = {}
    simp_params = {}

    if data_source == "Upload CSV":
        uploaded_file, filtered_df, upload_params = render_upload_ui(active_baseline_name, saved_params)
    elif data_source == "Generate Synthetic Load":
        syn_params = render_synthetic_load_ui(active_baseline_name)
    elif data_source == "12-Month Consumption & Peak (Simplified)":
        from tabs.tab1_components.simplified_12month import render_simplified_12month_ui
        simp_params = render_simplified_12month_ui(active_baseline_name)
    else:
        render_manual_builder(active_baseline_name, is_edit_mode=False, base_p=saved_params)

    # Only show baseline_form for non-manual data sources, since manual builder handles its own saving
    if data_source != "Advanced Manual Generator":
        st.divider()

        # --- 3. PROJECT META & FINANZEN ---
        st.write("### 📊 3. Project Meta & Financial Configuration")

        with st.form("baseline_form"):
            proj_params = render_project_params(saved_params, active_baseline_name)

            st.divider()
            working_fin = saved_params.get('financial_metadata', {}).copy()
            if preset_data:
                working_fin.update(preset_data)
            working_fin['tariff_mode'] = preset_label

            fin_params = render_financial_inputs(working_fin, include_financials, contract_mode)

            st.divider()
            submit_btn = st.form_submit_button("💾 Process & Save Baseline Profile", type="primary", use_container_width=True)

        if submit_btn:
            st.session_state['current_financial_metadata'] = fin_params

        # --- 4. SAVE EXECUTION ---
        if submit_btn:
            with st.spinner("Processing energy profile & validating limits..."):
                df, is_valid, msg = validate_and_process_data(
                    data_source, uploaded_file, upload_params, syn_params, proj_params, simp_params
                )

                if data_source == "Upload CSV" and filtered_df is not None and not filtered_df.empty:
                    df = filtered_df
                    is_valid = True

                if is_valid and df is not None:
                    limit_kw = fin_params.get('contracted_capacity_kw', 120.0)

                    # Save profile class representation
                    save_profile_to_base(active_baseline_name, df, limit_kw)

                    # Update scenario tariff and metadata
                    if active_scenario_obj:
                        active_scenario_obj.base_tariff.name = preset_label if preset_label else "Custom"
                        active_scenario_obj.base_tariff.contracted_capacity_kw = limit_kw
                        active_scenario_obj.metadata = proj_params
                        active_scenario_obj.metadata['grid_contract_mode'] = contract_mode
                        active_scenario_obj.metadata['data_source'] = data_source
                        if contract_mode == "Generic AC Connection Tier":
                            active_scenario_obj.metadata['generic_ac_key'] = selected_ac_key
                        active_scenario_obj.metadata['include_financials'] = include_financials
                        active_scenario_obj.metadata['financial_metadata'] = fin_params

                    st.success(f"✅ Baseline '{active_baseline_name}' successfully saved!")
                    st.rerun()
                else:
                    st.error(f"Validation failed: {msg}")

    # --- 5. CHART RENDERING ---
    if active_scenario_obj and active_scenario_obj.original_profile is not None:
        st.divider()
        st.write(f"### 📈 Current Profile: {active_baseline_name}")
        
        # Wir rufen das Diagramm mit den Werten direkt aus unserer Klasse auf!
        render_baseline_chart(
            active_scenario_obj.original_profile, 
            active_scenario_obj.base_tariff.contracted_capacity_kw
        )

        if active_scenario_obj.metadata.get('include_financials', False):
            render_baseline_invoice_summary(
                active_scenario_obj.original_profile,
                active_scenario_obj.metadata.get('financial_metadata', {})
            )

# Die Funktion render_new_baseline_bridge wurde hier komplett GELÖSCHT,
# da wir sie nicht mehr brauchen. Tab 1 ist jetzt 100% nativ auf Klassen!