import uuid
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional

# ==========================================
# 1. TARIF-MODUL
# ==========================================
@dataclass
class Tariff:
    """Bauplan für einen Strom- und Netztarif (z.B. Stedin oder Custom)"""
    name: str
    contracted_capacity_kw: float  # Das vereinbarte Limit in kW
    fixed_costs_per_year: float    # Grundgebühr
    price_per_kw_peak: float       # Strafe/Kosten pro überschrittenem kW
    price_per_kwh: float = 0.0     # Optional: Arbeitspreis pro kWh
    is_custom: bool = False        # True, wenn der User ihn selbst eingetippt hat

# ==========================================
# 2. FINANZ-MODUL (Optional!)
# ==========================================
@dataclass
class FinancialParams:
    """Bauplan für die betriebswirtschaftlichen Parameter"""
    capex: float                   # Kaufpreis Hardware (Batterie/Solar) in €
    opex_yearly: float             # Laufende Wartung pro Jahr in €
    lifespan_years: int = 15       # Betrachtungszeitraum
    inflation_rate: float = 0.02   # 2% Standard-Inflation
    energy_price_growth: float = 0.04 # 4% Strompreissteigerung

# ==========================================
# 3. SUB-SZENARIO (Das Child / Die Lösung)
# ==========================================
@dataclass
class SubScenario:
    """Eine spezifische Lösung (Hardware/Tarif-Wechsel) für einen Standort"""
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())) # Generiert automatisch eine einmalige ID
    
    # Technische Eingaben
    battery_kwh: float = 0.0
    battery_kw: float = 0.0
    solar_kwp: float = 0.0
    
    # Die angehängten Module
    # 'Optional' bedeutet: Es kann ein Tarif drin sein, oder 'None' (dann gilt der vom Parent)
    custom_tariff: Optional[Tariff] = None 
    
    # Hier ist unser Sicherheitsschalter für Tab 3!
    # Wenn 'None', werden keine Finanzen berechnet.
    financials: Optional[FinancialParams] = None 
    
    # Das fertige Ergebnis der Energie-Logik
    simulated_profile: Optional[pd.DataFrame] = None 

# ==========================================
# 4. BASIS-SZENARIO (Der Parent / Das Fundament)
# ==========================================
@dataclass
class BaseScenario:
    """Der Hauptordner für einen Standort inklusive Status Quo"""
    name: str
    original_profile: pd.DataFrame # Das hochgeladene CSV/Excel Lastprofil
    base_tariff: Tariff            # Der aktuell genutzte Tarif
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Die Liste aller Lösungsversuche (Children)
    # Startet automatisch als leere Liste []
    sub_scenarios: List[SubScenario] = field(default_factory=list) 
    
    def add_sub_scenario(self, sub: SubScenario):
        """Hilfsfunktion, um schnell ein neues Child hinzuzufügen"""
        self.sub_scenarios.append(sub)