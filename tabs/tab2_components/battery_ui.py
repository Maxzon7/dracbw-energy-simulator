# tabs/tab2_components/battery_ui.py
import streamlit as st

def render_battery_ui(scenario_id: str) -> dict:
    """
    Layer 1: Renders advanced UI inputs for the BESS (Battery Energy Storage System).
    Includes targeted shaving thresholds, recharge boundary windows, and financial parameters.
    """
    st.write("### BESS Storage Dimensioning")
    st.info("Configure the storage hardware limits, target operational thresholds, and battery recharging strategy.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Hardware Capacity & Power**")
        b_cap = st.number_input(
            "Storage Capacity (kWh)", 
            min_value=10.0, max_value=5000.0, value=200.0, step=50.0,
            key=f"bat_cap_{scenario_id}"
        )
        b_pwr = st.number_input(
            "Max Inverter Power (kW)", 
            min_value=5.0, max_value=2000.0, value=100.0, step=25.0,
            key=f"bat_pwr_{scenario_id}"
        )
        
        st.divider()
        st.write("**Peak Shaving Target**")
        shaving_threshold = st.number_input(
            "Target Shaving Threshold (kW)",
            min_value=10.0, max_value=5000.0, value=120.0, step=10.0,
            help="The battery will discharge to keep the grid demand strictly at or below this value.",
            key=f"bat_thresh_{scenario_id}"
        )

    with col2:
        st.write("**Intelligent Recharge Control**")
        charge_pwr_limit = st.slider(
            "Max Recharge Power Limit (kW)",
            min_value=5, max_value=500, value=30, step=5,
            help="Limits how fast the battery pulls power to recharge, preventing secondary grid peaks.",
            key=f"bat_chg_lim_{scenario_id}"
        )
        
        st.write("#### Allowed Charging Window")
        charge_start_hour = st.slider(
            "Window Start Time (Hour)", min_value=0, max_value=23, value=22,
            key=f"bat_chg_start_{scenario_id}"
        )
        charge_end_hour = st.slider(
            "Window End Time (Hour)", min_value=0, max_value=23, value=6,
            key=f"bat_chg_end_{scenario_id}"
        )
        
        green_charging = st.toggle(
            "Green Charging Only (Solar Surplus)", 
            value=False,
            help="If enabled, the battery will refuse grid electricity and only recharge via free local solar excess.",
            key=f"bat_green_{scenario_id}"
        )

    st.divider()
    
    st.write("**Physical Efficiency Parameters**")
    col_eff1, col_eff2 = st.columns(2)
    with col_eff1:
        efficiency = st.slider(
            "Round-Trip Efficiency (%)", 
            min_value=75, max_value=98, value=92,
            help="Total AC-to-AC conversion efficiency. Splitted equally via square root on charge/discharge cycles.",
            key=f"bat_eff_{scenario_id}"
        )
    with col_eff2:
        initial_soc_pct = st.slider(
            "Initial State of Charge (%)", min_value=0, max_value=100, value=50,
            key=f"bat_soc_init_{scenario_id}"
        )

    # --- NEU: Financial Estimates (CAPEX/OPEX) ---
    st.divider()
    with st.expander("$$ Financial Estimates (CAPEX & OPEX)", expanded=False):
        st.write("Configure the estimated capital expenditure and maintenance costs for the ROI analysis.")
        c_fin1, c_fin2, c_fin3 = st.columns(3)
        
        capex_per_kwh = c_fin1.number_input(
            "Storage CAPEX (€/kWh)", 
            min_value=50.0, max_value=1500.0, value=400.0, step=10.0,
            key=f"bat_capex_kwh_{scenario_id}"
        )
        capex_per_kw = c_fin2.number_input(
            "Inverter CAPEX (€/kW)", 
            min_value=50.0, max_value=1000.0, value=150.0, step=10.0,
            key=f"bat_capex_kw_{scenario_id}"
        )
        opex_pct = c_fin3.number_input(
            "Annual OPEX (% of CAPEX)", 
            min_value=0.0, max_value=10.0, value=1.5, step=0.1,
            help="Estimated yearly maintenance, insurance, and cooling costs.",
            key=f"bat_opex_{scenario_id}"
        )
        
        total_bat_capex = (b_cap * capex_per_kwh) + (b_pwr * capex_per_kw)
        st.info(f"**Estimated Battery Investment (CAPEX): {total_bat_capex:,.0f} €**")

    return {
        "b_cap": b_cap,
        "b_pwr": b_pwr,
        "shaving_threshold": shaving_threshold,
        "charge_pwr_limit": charge_pwr_limit,
        "charge_start_hour": charge_start_hour,
        "charge_end_hour": charge_end_hour,
        "green_charging": green_charging,
        "efficiency": efficiency,
        "initial_soc_pct": initial_soc_pct,
        "capex_per_kwh": capex_per_kwh,
        "capex_per_kw": capex_per_kw,
        "opex_pct": opex_pct,
        "total_capex": total_bat_capex
    }