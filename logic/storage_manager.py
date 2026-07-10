# logic/storage_manager.py
import streamlit as st
from classes.models import BaseScenario, SubScenario, Tariff
import pandas as pd

def init_storage():
    """Initializes the class-based portfolio inside the active project session."""
    active_project = st.session_state.get('active_project_name')
    if not active_project:
        return

    # Ensure the active project structure exists within the project hub
    if active_project in st.session_state.get('project_hub', {}):
        if 'project_portfolio' not in st.session_state['project_hub'][active_project]:
            st.session_state['project_hub'][active_project]['project_portfolio'] = []

def get_all_base_scenarios() -> list:
    """Returns all base scenarios linked to the currently active project."""
    init_storage()
    active_project = st.session_state.get('active_project_name')
    if active_project and active_project in st.session_state.get('project_hub', {}):
        return st.session_state['project_hub'][active_project]['project_portfolio']
    return []

def get_base_scenario(name: str) -> BaseScenario:
    """Searches for a specific base scenario by name within the active project."""
    portfolio = get_all_base_scenarios()
    for scen in portfolio:
        if scen.name == name:
            return scen
    return None

def create_empty_base_scenario(name: str) -> BaseScenario:
    """Creates and registers a new empty base scenario for the active project."""
    init_storage()
    active_project = st.session_state.get('active_project_name')
    
    if not get_base_scenario(name) and active_project:
        dummy_tariff = Tariff(name="Pending", contracted_capacity_kw=0, fixed_costs_per_year=0, price_per_kw_peak=0)
        new_base = BaseScenario(name=name, original_profile=None, base_tariff=dummy_tariff)
        st.session_state['project_hub'][active_project]['project_portfolio'].append(new_base)
        return new_base
    return get_base_scenario(name)

def save_profile_to_base(name: str, df: pd.DataFrame, limit_kw: float):
    """Saves the processed data profile directly into the specified base scenario."""
    scen = get_base_scenario(name)
    if scen:
        scen.original_profile = df
        scen.base_tariff.contracted_capacity_kw = limit_kw

def add_sub_scenario(base_name: str, sub_scenario: SubScenario):
    """Attaches a newly simulated variant (child) to a specific base scenario (parent)."""
    base_obj = get_base_scenario(base_name)
    if base_obj:
        base_obj.add_sub_scenario(sub_scenario)