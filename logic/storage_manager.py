# logic/storage_manager.py
# logic/storage_manager.py
import streamlit as st
from classes.models import BaseScenario, SubScenario, Tariff
import pandas as pd

def init_storage():
    """Initialisiert das neue, reine Klassen-Portfolio."""
    if "project_portfolio" not in st.session_state:
        st.session_state.project_portfolio = [] # Hier liegen NUR NOCH BaseScenario-Objekte!
    if "active_base_name" not in st.session_state:
        st.session_state.active_base_name = None

# ==========================================
# 1. FUNKTIONEN FÜR TAB 1 (BASELINE)
# ==========================================
def get_all_base_scenarios() -> list:
    """Gibt eine Liste aller Basis-Szenarien zurück."""
    init_storage()
    return st.session_state.project_portfolio

def get_base_scenario(name: str) -> BaseScenario:
    """Sucht ein Basis-Szenario anhand seines Namens."""
    init_storage()
    for scen in st.session_state.project_portfolio:
        if scen.name == name:
            return scen
    return None

def create_empty_base_scenario(name: str) -> BaseScenario:
    """Wird aufgerufen, wenn der User auf 'Create New Baseline' klickt."""
    init_storage()
    if not get_base_scenario(name):
        # Wir legen einen Platzhalter-Tarif an, bis der User das Formular abspeichert
        dummy_tariff = Tariff(name="Pending", contracted_capacity_kw=0, fixed_costs_per_year=0, price_per_kw_peak=0)
        # Erstelle das echte Objekt (df ist anfangs None, da noch nichts hochgeladen wurde)
        new_base = BaseScenario(name=name, original_profile=None, base_tariff=dummy_tariff)
        st.session_state.project_portfolio.append(new_base)
        return new_base
    return get_base_scenario(name)

def save_profile_to_base(name: str, df: pd.DataFrame, limit_kw: float):
    """Speichert das hochgeladene CSV/Profil im entsprechenden Basis-Szenario."""
    scen = get_base_scenario(name)
    if scen:
        scen.original_profile = df
        # Aktualisiere das Limit im Tarif
        scen.base_tariff.contracted_capacity_kw = limit_kw

# ==========================================
# 2. FUNKTIONEN FÜR TAB 2 (SUB-SZENARIEN)
# ==========================================
def add_sub_scenario(parent_name: str, sub_scenario: SubScenario):
    """Hängt eine fertige Lösung (Hardware/Batterie) an ein Basis-Projekt an."""
    parent = get_base_scenario(parent_name)
    if parent:
        # Prüfen, ob schon ein SubSzenario mit diesem Namen existiert (verhindert Duplikate beim Updaten)
        for i, existing_sub in enumerate(parent.sub_scenarios):
            if existing_sub.name == sub_scenario.name:
                parent.sub_scenarios[i] = sub_scenario
                return
        # Falls es neu ist, einfach anhängen
        parent.sub_scenarios.append(sub_scenario)