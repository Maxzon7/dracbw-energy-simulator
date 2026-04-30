# config/translations.py

"""
This file contains all language dictionaries and text content for the application.
By keeping the text separate, the main application file remains clean and maintainable.
"""

# Dictionary to map display names to internal language codes
LANGUAGES = {
    "English 🇬🇧": "en",
    "Deutsch 🇩🇪": "de",
    "Nederlands 🇳🇱": "nl"
}

# Nested dictionary containing all UI text elements per language
CONTENT = {
    "en": {
        "title": "Smart Energy and Peak Shaving Simulator",
        "warning": "Warning: This software is in beta stage and prone to errors. Results are for orientation only and must never be the sole basis for investment decisions. Please verify the units of your input data (e.g., kW vs. W).",
        "info_title": "Technical Documentation",
        "info_text": "This tool analyzes consumption patterns to optimize grid load. Raw data is converted to kilowatts (kW). The simulation calculates minimum storage requirements considering continuous charging and discharging cycles.",
        "header_data": "1. Data Input",
        "header_grid": "2. Grid and Resolution",
        "header_battery": "3. Battery Specifications",
        "header_colors": "4. Chart Colors",
        "grid_limit": "Grid Limit (kW)",
        "resolution": "Data Resolution (Minutes)",
        "enable_bat": "Enable Battery Simulation",
        "bat_cap": "Battery Capacity (kWh)",
        "bat_pwr": "Max. Charging Power (kW)",
        "analysis_period": "Analysis Period",
        "metrics_title": "Hardware Requirements and Peak Analysis",
        "metric_peak": "Maximum Original Peak",
        "metric_min_pwr": "Min. Battery Power Required",
        "metric_min_cap": "Min. Capacity Required",
        "chart_load": "System Load Profile",
        "chart_act": "Battery Action (kW)",
        "chart_soc": "State of Charge (SoC in kWh)",
        "no_bat_warn": "Battery simulation disabled. Showing raw data only.",
        "pdf_button": "Generate PDF Report",
        "pdf_download": "Download Technical PDF"
    },
    "de": {
        "title": "Smart Energy und Peak Shaving Simulator",
        "warning": "Warnung: Diese Software befindet sich im Beta-Stadium und ist fehleranfaellig. Die Ergebnisse dienen nur zur Orientierung und duerfen niemals die alleinige Grundlage fuer Investitionsentscheidungen sein. Pruefen Sie insbesondere die Einheiten Ihrer Eingabedaten (z.B. kW vs. W).",
        "info_title": "Technische Dokumentation",
        "info_text": "Dieses Tool analysiert Verbrauchsmuster zur Optimierung der Netzlast. Rohdaten werden in Kilowatt (kW) umgerechnet. Die Simulation berechnet den minimalen Speicherbedarf unter Beruecksichtigung kontinuierlicher Lade- und Entladezyklen.",
        "header_data": "1. Dateneingabe",
        "header_grid": "2. Netz und Aufloesung",
        "header_battery": "3. Batterie-Spezifikationen",
        "header_colors": "4. Diagramm-Farben",
        "grid_limit": "Netz-Limit (kW)",
        "resolution": "Daten-Aufloesung (Minuten)",
        "enable_bat": "Batterie-Simulation aktivieren",
        "bat_cap": "Batterie-Kapazitaet (kWh)",
        "bat_pwr": "Max. Ladeleistung (kW)",
        "analysis_period": "Analysezeitraum",
        "metrics_title": "Hardware-Anforderungen und Peak-Analyse",
        "metric_peak": "Maximaler Lastspitze (Original)",
        "metric_min_pwr": "Min. benoetigte Batterieleistung",
        "metric_min_cap": "Min. benoetigte Kapazitaet",
        "chart_load": "Systemlast-Profil",
        "chart_act": "Batterie-Aktion (kW)",
        "chart_soc": "Ladestand (SoC in kWh)",
        "pdf_button": "PDF Bericht generieren",
        "pdf_download": "Technisches PDF herunterladen",
        "no_bat_warn": "Batterie-Simulation deaktiviert. Zeige nur Rohdaten."
    },
    "nl": {
        "title": "Smart Energy en Peak Shaving Simulator",
        "warning": "Waarschuwing: Deze software bevindt zich in een betafase en is foutgevoelig. De resultaten zijn uitsluitend bedoeld ter orientatie en mogen nooit de enige basis vormen voor investeringsbeslissingen. Controleer met name de eenheden van uw invoergegevens (bijv. kW vs. W).",
        "info_title": "Technische Documentatie",
        "info_text": "Deze tool analyseert verbruikspatronen om de netbelasting te optimaliseren. Ruwe gegevens worden omgezet naar kilowatt (kW). De simulatie berekent de minimale opslagbehoefte rekening houdend met continue laad- en ontlaadcycli.",
        "header_data": "1. Gegevensinvoer",
        "header_grid": "2. Net en Resolutie",
        "header_battery": "3. Batterijspecificaties",
        "header_colors": "4. Grafiekkleuren",
        "grid_limit": "Netlimiet (kW)",
        "resolution": "Resolutie gegevens (minuten)",
        "enable_bat": "Batterijsimulatie inschakelen",
        "bat_cap": "Batterijcapaciteit (kWh)",
        "bat_pwr": "Max. laadvermogen (kW)",
        "analysis_period": "Analyseperiode",
        "metrics_title": "Hardwarevereisten en Piekanalyse",
        "metric_peak": "Maximale Oorspronkelijke Piek",
        "metric_min_pwr": "Min. Batterijvermogen Vereist",
        "metric_min_cap": "Min. Capaciteit Vereist",
        "chart_load": "Systeembelastingprofiel",
        "chart_act": "Batterij-actie (kW)",
        "chart_soc": "Laadstatus (SoC in kWh)",
        "pdf_button": "Genereer PDF Rapport",
        "pdf_download": "Download Technisch PDF",
        "no_bat_warn": "Batterijsimulatie uitgeschakeld. Alleen ruwe gegevens worden getoond."
    }
}