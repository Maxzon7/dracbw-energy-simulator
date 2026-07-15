# tabs/tab2_components/generator_ui.py
import streamlit as st

def render_generator_ui(scenario_id: str, existing_params: dict = None) -> dict:
    """
    Renders the UI inputs for the backup generator.
    """
    if existing_params is None:
        existing_params = {}

    st.write(" **Generator Configuration**")
    c1, c2 = st.columns(2)
    
    gen_pwr = c1.number_input(
        "Max Generator Power (kW)", 
        value=float(existing_params.get("gen_pwr", 250.0)), step=10.0, 
        key=f"gen_pwr_{scenario_id}",
        help="The physical limit of the generator. It cannot push more kW than this."
    )
    
    fuel_rate = c2.number_input(
        "Fuel Consumption (Liters / kWh)", 
        value=float(existing_params.get("fuel_l_per_kwh", 0.28)), step=0.01, 
        key=f"gen_fuel_{scenario_id}",
        help="Average diesel/gas consumption per produced kWh."
    )
    
    # Financial Parameters - conditional on global toggle
    capex_per_year = float(existing_params.get("capex_per_year", 0.0))
    opex_per_hour = float(existing_params.get("opex_per_hour", 0.0))
    
    if st.session_state.get('enable_financials', False):
        st.write(" **Generator Financial Parameters**")
        cf1, cf2 = st.columns(2)
        capex_per_year = cf1.number_input(
            "Generator CAPEX / Annual Rental (€/Yr)",
            value=capex_per_year, step=500.0,
            key=f"gen_capex_{scenario_id}",
            help="Annual cost of purchasing or renting/leasing the generator hardware."
        )
        opex_per_hour = cf2.number_input(
            "Maintenance Cost (€/Operating Hour)",
            value=opex_per_hour, step=1.0,
            key=f"gen_opex_hr_{scenario_id}",
            help="Service, oil, and filters cost per engine running hour."
        )
        
    return {
        "gen_pwr": gen_pwr,
        "fuel_l_per_kwh": fuel_rate,
        "capex_per_year": capex_per_year,
        "opex_per_hour": opex_per_hour
    }