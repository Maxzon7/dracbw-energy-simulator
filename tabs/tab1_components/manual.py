# tabs/tab1_components/manual.py
import streamlit as st

# Import our new UI module, plus the calculation engine and Trichter
from tabs.tab1_components.manual_components.parameter_inputs import render_scenario_selector, render_all_input_fields
from tabs.tab1_components.manual_components.generation_logic import run_profile_generation
from tabs.tab1_components.manual_components.anomaly_manager import render_anomaly_manager
from tabs.tab1_components.validation_ui import render_validation_dashboard

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
    # Inject loaded anomalies into session state if opening a template
    if selected_template != "[+ Create Brand New Profile]" and 'current_anomalies' in st.session_state:
        if not st.session_state['current_anomalies'] and p.get("anomalies"):
            st.session_state['current_anomalies'] = list(p.get("anomalies", []))

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
            st.success("✅ Generated annual profile successfully!")
            
    elif 'filtered_data' in st.session_state and p.get('data_source') == 'Manual':
        df = st.session_state['filtered_data']

    # 5. Route to Trichter
    if df is not None and not df.empty:
        # Merge all user inputs with the system metadata
        params_to_pass = {
            **user_inputs, # Unpacks all values from the slider dictionary automatically!
            "project_metadata": st.session_state.get('current_project_metadata', {}),
            "data_source": "Manual",
            "is_manual": True,
            "resolution": 15,
            "anomalies": list(st.session_state.get('current_anomalies', []))
        }
        
        render_validation_dashboard(df, params_to_pass, active_scenario, is_edit_mode)