import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.energy_logic import load_and_clean_csv, process_consumption_data, simulate_battery_logic, get_exact_minimum_requirements

def main():
    st.set_page_config(page_title="Pro Energy Simulator", layout="wide")

    # --- TRANSLATION SYSTEM ---
    # English is now the first option (index 0)
    languages = {
        "English 🇬🇧": "en",
        "Deutsch 🇩🇪": "de",
        "Nederlands 🇳🇱": "nl"
    }
    
    sel_lang = st.sidebar.selectbox("Language Selection", list(languages.keys()), index=0)
    lang = languages[sel_lang]

    content = {
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
            "no_bat_warn": "Battery simulation disabled. Showing raw data only."
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
            "no_bat_warn": "Batterijsimulatie uitgeschakeld. Alleen ruwe gegevens worden getoond."
        }
    }
    
    # Secure fallback to English
    t = content.get(lang, content["en"])

    st.title(t["title"])
    st.error(t["warning"])
    
    with st.expander(t["info_title"]):
        st.write(t["info_text"])

    # --- SIDEBAR CONTROLS ---
    st.sidebar.header(t["header_data"])
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
    
    st.sidebar.header(t["header_grid"])
    grid_limit = st.sidebar.number_input(t["grid_limit"], value=50.0, step=5.0)
    res = st.sidebar.selectbox(t["resolution"], [1, 5, 15, 60], index=2)
    
    st.sidebar.header(t["header_battery"])
    show_battery = st.sidebar.toggle(t["enable_bat"], value=True)
    b_cap = st.sidebar.slider(t["bat_cap"], 0, 500, 100, disabled=not show_battery)
    b_pwr = st.sidebar.slider(t["bat_pwr"], 0, 200, 50, disabled=not show_battery)
    
    st.sidebar.header(t["header_colors"])
    col_raw = st.sidebar.color_picker("Raw Load Color", "#A9A9A9")
    col_opt = st.sidebar.color_picker("Optimized Load Color", "#00CC96")
    col_soc = st.sidebar.color_picker("SoC Color", "#636EFA")
    col_act = st.sidebar.color_picker("Battery Action Color", "#FFA15A")

    if uploaded_file:
        try:
            # 1. Use our new smart loader to handle the CSV mess
            raw_df = load_and_clean_csv(uploaded_file)
            
            # 2. Process the cleaned dataframe
            data = process_consumption_data(raw_df, res)
            
            min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
            selected_dates = st.sidebar.date_input(t["analysis_period"], [min_date, max_date])
            
            if len(selected_dates) == 2:
                filtered = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                (data['timestamp'].dt.date <= selected_dates[1])]
                
                min_reqs = get_exact_minimum_requirements(filtered, grid_limit, res)
                
                st.subheader(t["metrics_title"])
                m1, m2, m3 = st.columns(3)
                
                m1.metric(t["metric_peak"], f"{filtered['consumption_kw'].max():.1f} kW")
                m2.metric(t["metric_min_pwr"], f"{min_reqs['min_power_kw']:.1f} kW")
                m3.metric(t["metric_min_cap"], f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")

                if show_battery:
                    results = simulate_battery_logic(filtered, grid_limit, b_cap, b_pwr, res)
                    
                    st.subheader(t["chart_load"])
                    fig_load = go.Figure()
                    fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                             name="Raw", line=dict(color=col_raw, width=1)))
                    fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                             name="Optimized", line=dict(color=col_opt, width=2)))
                    fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red")
                    fig_load.update_layout(height=350, yaxis_title="kW", margin=dict(t=10, b=10))
                    st.plotly_chart(fig_load, use_container_width=True)

                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.subheader(t["chart_act"])
                        fig_act = go.Figure()
                        fig_act.add_trace(go.Bar(x=results['timestamp'], y=results['battery_action_kw'], marker_color=col_act))
                        fig_act.update_layout(height=250, yaxis_title="kW", margin=dict(t=10, b=10))
                        st.plotly_chart(fig_act, use_container_width=True)
                        
                    with c_right:
                        st.subheader(t["chart_soc"])
                        fig_soc = go.Figure()
                        fig_soc.add_trace(go.Scatter(x=results['timestamp'], y=results['battery_soc_kwh'], 
                                                     fill='tozeroy', line=dict(color=col_soc)))
                        fig_soc.update_layout(height=250, yaxis_title="kWh", margin=dict(t=10, b=10))
                        st.plotly_chart(fig_soc, use_container_width=True)
                else:
                    st.warning(t["no_bat_warn"])
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=filtered['timestamp'], y=filtered['consumption_kw'], line=dict(color=col_raw)))
                    fig.add_hline(y=grid_limit, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)
                    
        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()