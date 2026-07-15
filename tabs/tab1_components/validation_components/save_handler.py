# tabs/tab1_components/validation_components/save_handler.py
import streamlit as st
import pandas as pd
from tabs.tab1_components.financial_ui import render_financial_projection

def render_save_handler(df: pd.DataFrame, params: dict, active_scenario: str, statistical_anomalies: pd.DataFrame):
    """
    Renders the UI for saving the validated scenario to the global scenario vault.
    Supports establishing hierarchical parent-child relationships for sub-scenarios.
    """
    data_source = params.get('data_source', 'Unknown')
    grid_limit = params.get('grid_limit', 50.0)
    
    st.divider()
    st.write(f"### 💾 Save {data_source} Scenario")
    
    if st.session_state.get('enable_financials', False):
        fin_meta = st.session_state.get('current_financial_metadata', {})
        render_financial_projection(df, fin_meta)
        st.write("---")
    
    # 1. Base Naming Suggestion
    default_scen_name = st.session_state.get('active_scenario_name', f"Scenario_{data_source}")
    if default_scen_name == "[+ Create New Scenario]":
        default_scen_name = f"New_{data_source}_Profile"
        
    scenario_name = st.text_input("Scenario Name:", value=default_scen_name, key=f"save_name_{active_scenario}")
    
    # --- NEU: Intelligenter Duplikats-Wächter ---
    vault = st.session_state.get('scenario_vault', {})
    existing_scenarios = list(vault.keys())
    name_exists = scenario_name in existing_scenarios
    save_disabled = False
    
    if name_exists:
        st.warning(f"⚠️ A scenario named '{scenario_name}' already exists. Please rename it to save as a copy, or check the box below to overwrite.")
        overwrite = st.checkbox("Overwrite existing scenario", value=False, key=f"ow_{active_scenario}")
        if not overwrite:
            save_disabled = True
    
    # 2. Hierarchical Stammbaum Architecture 
    col_type, col_parent = st.columns(2)
    with col_type:
        save_type = st.radio("Scenario Type:", options=["Base Scenario", "Sub-Scenario"], horizontal=True, key=f"save_type_{active_scenario}")
        
    parent_scen = None
    with col_parent:
        if save_type == "Sub-Scenario":
            if existing_scenarios:
                suggested_parent = st.session_state.get('last_loaded_registry_name')
                default_idx = existing_scenarios.index(suggested_parent) if suggested_parent in existing_scenarios else 0
                parent_scen = st.selectbox("Belongs to Base Scenario:", options=existing_scenarios, index=default_idx, key=f"parent_select_{active_scenario}")
            else:
                st.warning("No base scenarios in the vault. Saving as Base Scenario.")
                save_type = "Base Scenario"

    # 3. Execution Pipeline (mit disabled=save_disabled)
    if st.button(f"🚀 Securely Save Profile & Continue", type="primary", use_container_width=True, disabled=save_disabled, key=f"save_btn_uni_{active_scenario}"):
        st.session_state['filtered_data'] = df
        st.session_state['active_scenario_name'] = scenario_name
        st.session_state['manual_df_ready'] = False 
        
        params['financial_metadata'] = fin_meta
        
        if 'scenario_vault' not in st.session_state:
            st.session_state['scenario_vault'] = {}
            
        st.session_state['scenario_vault'][scenario_name] = {
            "df": df,
            "grid_limit": grid_limit,
            "anomalies": statistical_anomalies.index.tolist() if not statistical_anomalies.empty else [],
            "data_source": data_source,
            "parent": parent_scen, 
            "params": params
        }
        
        # --- TRANSACTIONAL DATA BRIDGE ---
        from classes.models import BaseScenario, SubScenario, Tariff, FinancialParams
        from logic.storage_manager import get_base_scenario, create_empty_base_scenario, save_profile_to_base, add_sub_scenario
        
        active_project = st.session_state.get('active_project_name')
        
        if active_project:
            if save_type == "Base Scenario":
                # Ensure the base scenario exists in storage
                base_obj = get_base_scenario(scenario_name)
                if not base_obj:
                    base_obj = create_empty_base_scenario(scenario_name)
                
                # Update its profile and tariff
                base_obj.original_profile = df
                base_obj.base_tariff = Tariff(
                    name=fin_meta.get('tariff_mode', 'Custom') if fin_meta.get('tariff_mode') else 'Custom',
                    contracted_capacity_kw=grid_limit,
                    fixed_costs_per_year=float(fin_meta.get('fixed_annual_connection_fee', 0.0) or 0.0) + float(fin_meta.get('fixed_annual_transport_fee', 0.0) or 0.0),
                    price_per_kw_peak=float(fin_meta.get('peak_capacity_fee_per_kw_month', 0.0) or 0.0),
                    price_per_kwh=float(fin_meta.get('energy_price_normal_per_kwh', 0.0) or 0.0),
                    is_custom=True
                )
                # Store metadata
                base_obj.metadata = params
                base_obj.metadata['financial_metadata'] = fin_meta
                
            elif save_type == "Sub-Scenario" and parent_scen:
                # Retrieve the parent base scenario
                parent_obj = get_base_scenario(parent_scen)
                if parent_obj:
                    # Construct financial parameters if available
                    fin_params = None
                    if fin_meta:
                        fin_params = FinancialParams(
                            capex=float(fin_meta.get('baseline_grid_capex', 0.0) or 0.0),
                            opex_yearly=float(fin_meta.get('fixed_annual_connection_fee', 0.0) or 0.0) + float(fin_meta.get('fixed_annual_transport_fee', 0.0) or 0.0),
                            lifespan_years=15,
                            inflation_rate=float(fin_meta.get('inflation', 3.0) or 3.0) / 100.0,
                            energy_price_growth=0.04
                        )
                    
                    # Create custom tariff for the sub scenario if it differs
                    sub_tariff = Tariff(
                        name=fin_meta.get('tariff_mode', 'Custom') if fin_meta.get('tariff_mode') else 'Custom',
                        contracted_capacity_kw=grid_limit,
                        fixed_costs_per_year=float(fin_meta.get('fixed_annual_connection_fee', 0.0) or 0.0) + float(fin_meta.get('fixed_annual_transport_fee', 0.0) or 0.0),
                        price_per_kw_peak=float(fin_meta.get('peak_capacity_fee_per_kw_month', 0.0) or 0.0),
                        price_per_kwh=float(fin_meta.get('energy_price_normal_per_kwh', 0.0) or 0.0),
                        is_custom=True
                    )
                    
                    # Extract battery/solar configs from params
                    b_kwh = float(params.get('battery_kwh', params.get('capacity_kwh', 0.0)))
                    b_kw = float(params.get('battery_kw', params.get('max_kw', 0.0)))
                    s_kwp = float(params.get('solar_kwp', params.get('system_size_kwp', 0.0)))
                    
                    # Construct SubScenario
                    new_sub = SubScenario(
                        name=scenario_name,
                        battery_kwh=b_kwh,
                        battery_kw=b_kw,
                        solar_kwp=s_kwp,
                        custom_tariff=sub_tariff,
                        financials=fin_params,
                        simulated_profile=df
                    )
                    
                    # Add to parent (remove duplicate first to handle overwrites cleanly)
                    parent_obj.sub_scenarios = [s for s in parent_obj.sub_scenarios if s.name != scenario_name]
                    parent_obj.add_sub_scenario(new_sub)
        
        if data_source == "CSV":
            st.session_state[f"csv_mapping_ready_{active_scenario}"] = False
            
        st.success(f"Scenario '{scenario_name}' successfully saved in the vault! You can proceed now.")
        st.rerun()

def save_profile_to_vault(vault, active_baseline, df, final_params, grid_limit):
    """
    Pure data-logic function. Saves the processed dataframe and parameters 
    into the global scenario vault without rendering any UI buttons.
    """
    try:
        vault[active_baseline] = {
            'df': df,
            'params': final_params,
            'grid_limit': grid_limit,
            'data_source': final_params.get('data_source', 'Unknown')
        }
        # Das st.session_state Update passiert sicherheitshalber auch hier nochmal
        import streamlit as st
        st.session_state['scenario_vault'] = vault
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"Error saving to vault: {e}")
        return False