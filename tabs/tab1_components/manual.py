# tabs/tab1_components/manual.py
import streamlit as st

# Import our new UI module, plus the calculation engine and Trichter
from tabs.tab1_components.manual_components.parameter_inputs import render_scenario_selector, render_all_input_fields
from tabs.tab1_components.manual_components.generation_logic import run_profile_generation
from tabs.tab1_components.manual_components.anomaly_manager import render_anomaly_manager
from tabs.tab1_components.validation_ui import render_validation_dashboard

# --- Der Daten-Waschgang für JSON-Importe ---
class RecoveredAnomaly:
    """Helper class to turn loaded JSON dictionaries back into objects for the UI."""
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)
# -------------------------------------------------

def render_manual_builder(active_scenario: str, is_edit_mode: bool, base_p: dict):
    """
    Orchestrates the manual profile generation.
    Acts as a thin routing layer between UI components, calculation logic, and the validation funnel.
    """
    st.write("### 🎛️ Advanced Manual Profile Generator")
    st.info("Configure your annual load profile. You can start fresh or load an existing scenario from the dropdown below.")
    
    # 1. Handle Scenario Loading / Template Selection
    selected_template, p = render_scenario_selector(active_scenario)
    
    st.divider()
    
    # 2. Render UI Input Fields and capture the resulting user configuration
    user_inputs = render_all_input_fields(p, active_scenario, selected_template)
    
    # 3. Anomaly Management Logic
    # Fallback: Lade Template-Anomalien in den State, falls wir intern das Dropdown benutzen
    if selected_template != "[+ Create Brand New Profile]" and not st.session_state.get('current_anomalies') and p.get("anomalies"):
        st.session_state['current_anomalies'] = list(p.get("anomalies", []))

    # DER ZWANGSWASCHGANG: Mache aus allem (egal woher es kommt) saubere Objekte!
    if 'current_anomalies' in st.session_state:
        safe_anomalies = []
        for a in st.session_state['current_anomalies']:
            if isinstance(a, (int, str)): 
                continue
            if isinstance(a, dict):
                safe_anomalies.append(RecoveredAnomaly(a))
            else:
                safe_anomalies.append(a)
        st.session_state['current_anomalies'] = safe_anomalies

    render_anomaly_manager()
    st.divider()

    # 4. Trigger Generation & Validation Pipeline
    df = None
    if st.button("⚙️ Generate / Update Profile", type="secondary", use_container_width=True, key=f"main_gen_btn_{active_scenario}"):
        with st.spinner("Calculating full annual profile with anomalies..."):
            # Pass unpacked user inputs directly to the calculation engine
            df = run_profile_generation(
                user_inputs["monthly_consumption"], user_inputs["days_per_week"], user_inputs["hours_per_day"], 
                user_inputs["base_load_pct"], user_inputs["num_connections"], user_inputs["amperage"], 
                user_inputs["enable_noise"], user_inputs["noise_percentage"], user_inputs["use_custom_months"], 
                user_inputs["monthly_configs"], user_inputs["calculated_grid_kw"]
            )
            st.session_state['filtered_data'] = df
            st.session_state['manual_df_ready'] = True 
            st.success("✅ Generated annual profile successfully!")
            
    # UX-Fix: Graphen sofort laden, wenn ein Template ausgewählt wird
    elif selected_template != "[+ Create Brand New Profile]":
        if 'scenario_vault' in st.session_state and selected_template in st.session_state['scenario_vault']:
            df = st.session_state['scenario_vault'][selected_template].get("df")
            
    elif st.session_state.get('manual_df_ready', False) and 'filtered_data' in st.session_state:
        df = st.session_state['filtered_data']

    # 5. Route to Trichter
    if df is not None and not df.empty:
        
        # Bugfix 3: Anomalien absolut sicher für den .drac Export als Dictionaries verpacken!
        export_anomalies = []
        for an in st.session_state.get('current_anomalies', []):
            if hasattr(an, '__dict__'):
                export_anomalies.append(an.__dict__)
            elif isinstance(an, dict):
                export_anomalies.append(an)

        # Merge all user inputs with the system metadata
        params_to_pass = {
            **user_inputs, 
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "Manual",
            "is_manual": True,
            "resolution": 15,
            "anomalies": export_anomalies
        }
        
        render_validation_dashboard(df, params_to_pass, active_scenario, is_edit_mode)