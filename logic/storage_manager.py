# logic/storage_manager.py
import pandas as pd
import json
import zipfile
import io
import streamlit as st
from classes.models import BaseScenario, SubScenario

def create_drac_export(scenarios_dict: dict) -> bytes:
    """
    Compresses multiple scenarios (e.g., a Baseline + all its Sub-scenarios) 
    into a unified .drac binary archive. Creates internal folders for each.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for scen_name, scen_data in scenarios_dict.items():
            # Create a safe internal folder name
            folder = scen_name.replace("/", "_").replace("\\", "_")
            
            df = scen_data.get("df")
            if df is not None:
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False, engine="pyarrow")
                zip_file.writestr(f"{folder}/data.parquet", parquet_buffer.getvalue())
                
            # Clean up the metadata
            metadata = {k: v for k, v in scen_data.items() if k != "df"}
            zip_file.writestr(f"{folder}/metadata.json", json.dumps(metadata, default=str))
            
    return zip_buffer.getvalue()

def parse_drac_import(uploaded_file, import_prefix="") -> dict:
    """
    Extracts and rebuilds a scenario vault object (potentially containing an entire tree)
    from an uploaded .drac file.
    """
    reconstructed_scenarios = {}
    
    with zipfile.ZipFile(uploaded_file, "r") as zip_file:
        paths = zip_file.namelist()
        
        # Find unique scenario folders inside the zip
        folders = set([p.split("/")[0] for p in paths if "/" in p])
        
        # Backward compatibility for old single-scenario .drac files
        if not folders and ("metadata.json" in paths or "data.parquet" in paths):
            scen_dict = {}
            if "metadata.json" in paths:
                scen_dict.update(json.loads(zip_file.read("metadata.json").decode("utf-8")))
            if "data.parquet" in paths:
                pq_bytes = zip_file.read("data.parquet")
                scen_dict["df"] = pd.read_parquet(io.BytesIO(pq_bytes), engine="pyarrow")
            
            name = import_prefix if import_prefix else "Imported_Legacy_Scenario"
            reconstructed_scenarios[name] = scen_dict
            return reconstructed_scenarios

        # New multi-scenario tree parsing
        for folder in folders:
            scen_dict = {}
            if f"{folder}/metadata.json" in paths:
                scen_dict.update(json.loads(zip_file.read(f"{folder}/metadata.json").decode("utf-8")))
            if f"{folder}/data.parquet" in paths:
                pq_bytes = zip_file.read(f"{folder}/data.parquet")
                scen_dict["df"] = pd.read_parquet(io.BytesIO(pq_bytes), engine="pyarrow")
            
            # Apply prefix to the name to avoid overwriting existing vault data
            new_name = f"{import_prefix}{folder}" if import_prefix else folder
            
            # MAGIE: If it's a sub-scenario, we must also update its parent's name to keep the tree linked!
            if scen_dict.get("parent") and import_prefix:
                scen_dict["parent"] = f"{import_prefix}{scen_dict['parent']}"
                
            reconstructed_scenarios[new_name] = scen_dict
            
    return reconstructed_scenarios


def init_class_based_storage():
    """
    Erstellt die neue 'Daten-Schublade' im Session State, falls sie noch nicht existiert.
    Stört die alten Speicher-Variablen absolut nicht.
    """
    if "project_portfolio" not in st.session_state:
        # Eine Liste, die alle Hauptprojekte (BaseScenarios) hält
        st.session_state.project_portfolio = [] 
        
    if "active_base_id" not in st.session_state:
        # Merkt sich, an welchem Standort der User gerade arbeitet
        st.session_state.active_base_id = None 

def save_base_scenario(base_scenario: BaseScenario):
    """Speichert ein neues Basis-Szenario und setzt es als 'aktiv'."""
    init_class_based_storage()
    st.session_state.project_portfolio.append(base_scenario)
    st.session_state.active_base_id = base_scenario.id

def get_active_base_scenario() -> BaseScenario:
    """Holt den Aktenordner (Parent), an dem der User gerade in Tab 2 bastelt."""
    init_class_based_storage()
    for scenario in st.session_state.project_portfolio:
        if scenario.id == st.session_state.active_base_id:
            return scenario
    return None

def add_sub_scenario_to_active(sub_scenario: SubScenario):
    """
    Nimmt einen Lösungsversuch (Child) und heftet ihn an den aktuellen Aktenordner (Parent).
    """
    active_base = get_active_base_scenario()
    if active_base:
        active_base.add_sub_scenario(sub_scenario)
        # Kurzes Feedback im UI (optional, aber gut fürs Debugging)
        st.success(f"Szenario '{sub_scenario.name}' sicher im Hintergrund gespeichert!")
    else:
        st.error("Fehler: Kein Basis-Szenario gefunden. Bitte zuerst Tab 1 ausfüllen.")