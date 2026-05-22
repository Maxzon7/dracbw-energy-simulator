# tabs/tab1_components/validation_ui.py
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def render_validation_dashboard(df: pd.DataFrame, params: dict, active_scenario: str, is_edit_mode: bool):
    """
    UNIFIED VALIDATION ENGINE (Der "Trichter")
    Nimmt fertige, normierte Lastgang-Daten (egal ob manuell oder CSV) entgegen 
    und rendert eine identische UX-Oberfläche für Validierung, Charting und Speicherung.
    """
    # Parameter sicher entpacken
    grid_limit = params.get('grid_limit', 50.0)
    res = params.get('resolution', 15)
    col_raw = params.get('col_raw', '#A9A9A9')
    data_source = params.get('data_source', 'Unknown')
    
    st.divider()
    st.write("### ⚡ 3. Baseline Load Profile Validation")
    
    # 1. Mathematische KPI-Berechnung
    intervals_per_hour = 60 / res
    total_energy_kwh = df['consumption_kw'].sum() / intervals_per_hour
    peak_load = df['consumption_kw'].max()
    avg_load = df['consumption_kw'].mean()
    
    # 2. Das identische 4-Spalten-Layout (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Resolution", f"{res} min")
    col2.metric("Peak Load", f"{peak_load:.1f} kW")
    col3.metric("Total Load", f"{total_energy_kwh:,.0f} kWh")
    col4.metric("Avg Base Load", f"{avg_load:.1f} kW")
    
    # 3. Gemeinsamer Anomalie-Scanner (Z-Score Logik)
    # Sucht nach Ausreißern, die mehr als 3 Standardabweichungen vom Durchschnitt abweichen
    std_dev = df['consumption_kw'].std()
    z_scores = (df['consumption_kw'] - avg_load) / std_dev if std_dev > 0 else 0
    anomalies = df[z_scores > 3.0] 
    
    if not anomalies.empty:
        st.warning(f"⚠️ {len(anomalies)} ungewöhnliche Lastspitzen (Anomalien) im Profil erkannt. Bitte im Chart prüfen!")
    else:
        st.success("✅ Profil validiert. Keine extremen Anomalien erkannt.")
        
    # 4. Das gemeinsame interaktive Diagramm
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['consumption_kw'], 
        mode='lines', line=dict(color=col_raw, width=1), 
        name=f'Kundenlast ({data_source})'
    ))
    
    # Gefundene Anomalien als rote Kreuzchen im Chart markieren
    if not anomalies.empty:
        fig.add_trace(go.Scatter(
            x=anomalies['timestamp'], y=anomalies['consumption_kw'],
            mode='markers', marker=dict(color='red', size=8, symbol='x'),
            name='Anomalien'
        ))
        
    fig.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
    fig.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), yaxis_title="Leistung (kW)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # 5. Der gemeinsame Speicher-Tresor
    st.divider()
    st.write(f"### 💾 {data_source}-Szenario speichern")
    
    default_scen_name = st.session_state.get('active_scenario_name', f"Szenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"Neues_{data_source}_Profil"
        
    scenario_name = st.text_input("Szenario-Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    if st.button(f"🚀 Profil sicher speichern & weiter", type="primary", use_container_width=True, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        
        if 'scenario_registry' not in st.session_state:
            st.session_state['scenario_registry'] = {}
            
        st.session_state['scenario_registry'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": anomalies.index.tolist() if not anomalies.empty else [],
            "data_source": data_source,
            "params": params
        }
        
        # Falls es ein CSV-Upload war, setzen wir den Popup-Merker zurück
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"✅ Szenario '{scenario_name}' erfolgreich im Tresor gesichert! Du kannst nun Tab 2 öffnen.")
        st.rerun()