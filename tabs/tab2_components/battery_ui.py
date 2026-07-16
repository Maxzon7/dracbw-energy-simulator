# tabs/tab2_components/battery_ui.py
import streamlit as st

def render_battery_ui(scenario_id: str, default_grid_limit: float = 120.0, existing_params: dict = None) -> dict:
    """
    Layer 1: Renders advanced UI inputs for the BESS (Battery Energy Storage System).
    Uses 'existing_params' to persist user inputs across tab switches (Two-Way Sync).
    """
    # Fallback to an empty dictionary if nothing is passed
    if existing_params is None:
        existing_params = {}

    st.write("### BESS Storage Dimensioning")
    st.info("Configure the storage hardware limits, target operational thresholds, and battery recharging strategy.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Hardware Capacity & Power**")
        col_b1, col_b2 = st.columns(2)
        num_batteries = col_b1.number_input(
            "Number of Batteries",
            min_value=1, max_value=1000,
            value=int(existing_params.get("num_batteries", 10)),
            key=f"bat_num_{scenario_id}"
        )
        cap_per_module = col_b2.number_input(
            "Capacity per Module (kWh)",
            min_value=1.0, max_value=500.0,
            value=float(existing_params.get("cap_per_module", 20.0)),
            key=f"bat_mod_cap_{scenario_id}"
        )
        # Read from session state if available to bypass Streamlit form reload lag
        num_batteries = int(st.session_state.get(f"bat_num_{scenario_id}", num_batteries))
        cap_per_module = float(st.session_state.get(f"bat_mod_cap_{scenario_id}", cap_per_module))
        b_cap = float(num_batteries * cap_per_module)
        st.success(f"**Total Storage Capacity: {b_cap:,.1f} kWh**")
        
        b_pwr = st.number_input(
            "Max Inverter Power (kW)", 
            min_value=5.0, max_value=2000.0, 
            value=float(existing_params.get("b_pwr", 100.0)), 
            step=25.0,
            key=f"bat_pwr_{scenario_id}"
        )
        
        st.divider()
        st.write("**Peak Shaving Target**")
        
        safe_grid_limit = max(10.0, min(5000.0, float(default_grid_limit)))
        shaving_threshold = st.number_input(
            "Target Shaving Threshold (kW)",
            min_value=10.0, max_value=5000.0, 
            value=float(existing_params.get("shaving_threshold", safe_grid_limit)),
            step=10.0,
            help="The battery will discharge to keep the grid demand strictly at or below this value.",
            key=f"bat_thresh_{scenario_id}"
        )

    with col2:
        st.write("**Intelligent Recharge Control**")
        charge_pwr_limit = st.slider(
            "Max Recharge Power Limit (kW)",
            min_value=5, max_value=500, 
            value=int(existing_params.get("charge_pwr_limit", 30)),
            step=5,
            key=f"bat_chg_lim_{scenario_id}"
        )
        
        st.write("#### Allowed Charging Window")
        charge_start_hour = st.slider(
            "Window Start Time (Hour)", min_value=0, max_value=23, 
            value=int(existing_params.get("charge_start_hour", 22)),
            key=f"bat_chg_start_{scenario_id}"
        )
        charge_end_hour = st.slider(
            "Window End Time (Hour)", min_value=0, max_value=23, 
            value=int(existing_params.get("charge_end_hour", 6)),
            key=f"bat_chg_end_{scenario_id}"
        )
        
        green_charging = st.toggle(
            "Green Charging Only (Solar Surplus)", 
            value=bool(existing_params.get("green_charging", False)),
            key=f"bat_green_{scenario_id}"
        )

    st.divider()
    
    st.write("**Physical Efficiency Parameters**")
    col_eff1, col_eff2 = st.columns(2)
    with col_eff1:
        efficiency = st.slider(
            "Round-Trip Efficiency (%)", 
            min_value=75, max_value=98, 
            value=int(existing_params.get("efficiency", 92)),
            key=f"bat_eff_{scenario_id}"
        )
    with col_eff2:
        initial_soc_pct = st.slider(
            "Initial State of Charge (%)", min_value=0, max_value=100, 
            value=int(existing_params.get("initial_soc_pct", 50)),
            key=f"bat_soc_init_{scenario_id}"
        )

    # --- Expandable Advanced Parameters to match Demo Mode sandbox ---
    with st.expander("Advanced Battery Parameters", expanded=False):
        b_type = st.selectbox(
            "Battery Type / Chemistry",
            ["LFP (Lithium Iron Phosphate)", "NMC (Lithium Nickel Manganese Cobalt)", "Lead-Acid", "Flow Battery"],
            index=["LFP (Lithium Iron Phosphate)", "NMC (Lithium Nickel Manganese Cobalt)", "Lead-Acid", "Flow Battery"].index(existing_params.get("battery_type", "LFP (Lithium Iron Phosphate)")),
            key=f"bat_type_{scenario_id}"
        )
        min_soc_pct = st.slider("Min State of Charge (SoC %)", 0, 50, int(existing_params.get("min_soc_pct", 10)), key=f"bat_min_soc_{scenario_id}")
        max_soc_pct = st.slider("Max State of Charge (SoC %)", 50, 100, int(existing_params.get("max_soc_pct", 90)), key=f"bat_max_soc_{scenario_id}")
        
        cycle_life = st.number_input(
            "Cycle Life (Expected total cycles)",
            min_value=500, max_value=15000, value=int(existing_params.get("cycle_life", 6000)), step=500,
            key=f"bat_cycle_life_{scenario_id}"
        )
        temp_cap_coeff = st.slider(
            "Temperature Capacity Penalty (%/°C deviation)",
            0.0, 2.0, float(existing_params.get("temp_cap_coeff", 0.5)), step=0.1,
            help="Capacity loss coefficient per °C deviation from 15°C - 35°C range.",
            key=f"bat_temp_cap_coeff_{scenario_id}"
        )

    # --- Financial Estimates - Conditional on enable_financials ---
    capex_per_kwh = float(existing_params.get("capex_per_kwh", 400.0))
    capex_per_kw = float(existing_params.get("capex_per_kw", 150.0))
    opex_pct = float(existing_params.get("opex_pct", 1.5))
    degradation_pct = float(existing_params.get("degradation_pct", 1.5))
    replacement_year = int(existing_params.get("replacement_year", 10))
    replacement_pct = float(existing_params.get("replacement_pct", 100.0))
    
    total_storage_capex = b_cap * capex_per_kwh
    total_inverter_capex = b_pwr * capex_per_kw
    total_bat_capex = total_storage_capex + total_inverter_capex

    if st.session_state.get('enable_financials', False):
        st.divider()
        with st.expander("Financial Estimates (CAPEX, OPEX & Lifecycle)", expanded=True):
            st.write("Configure the estimated capital expenditure, maintenance costs, and physical wear.")
            c_fin1, c_fin2, c_fin3, c_fin4 = st.columns(4)
            
            capex_per_kwh = c_fin1.number_input(
                "Storage Cells CAPEX (€/kWh)", 
                min_value=50.0, max_value=1500.0, 
                value=capex_per_kwh, 
                step=10.0,
                key=f"bat_capex_kwh_{scenario_id}"
            )
            capex_per_kw = c_fin2.number_input(
                "Inverter CAPEX (€/kW)", 
                min_value=50.0, max_value=1000.0, 
                value=capex_per_kw, 
                step=10.0,
                key=f"bat_capex_kw_{scenario_id}"
            )
            opex_pct = c_fin3.number_input(
                "Annual OPEX (%)", 
                min_value=0.0, max_value=10.0, 
                value=opex_pct, 
                step=0.1,
                key=f"bat_opex_{scenario_id}"
            )
            degradation_pct = c_fin4.number_input(
                "Annual Degradation (%)", 
                min_value=0.0, max_value=10.0, 
                value=degradation_pct, 
                step=0.1,
                key=f"bat_deg_{scenario_id}"
            )
            
            st.write("**Hardware Replacement (End of Life)**")
            c_rep1, c_rep2 = st.columns(2)
            replacement_year = c_rep1.slider(
                "Cell Replacement Year", 
                min_value=5, max_value=15, 
                value=replacement_year,
                key=f"bat_rep_yr_{scenario_id}"
            )
            replacement_pct = c_rep2.number_input(
                "Replacement Cost (% of Storage Cells)", 
                min_value=10.0, max_value=150.0, 
                value=replacement_pct, 
                step=5.0,
                key=f"bat_rep_pct_{scenario_id}"
            )
            
            total_storage_capex = b_cap * capex_per_kwh
            total_inverter_capex = b_pwr * capex_per_kw
            total_bat_capex = total_storage_capex + total_inverter_capex
            
            st.info(f"**Estimated Initial Battery Investment (CAPEX): {total_bat_capex:,.0f} €**")

    # The returned dict is used to update the "Schmierblatt" in Tab 2
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
        "num_batteries": num_batteries,
        "cap_per_module": cap_per_module,
        "battery_type": b_type,
        "min_soc_pct": min_soc_pct,
        "max_soc_pct": max_soc_pct,
        "cycle_life": cycle_life,
        "temp_cap_coeff": temp_cap_coeff,
        "capex_per_kwh": capex_per_kwh,
        "capex_per_kw": capex_per_kw,
        "opex_pct": opex_pct,
        "degradation_pct": degradation_pct,
        "replacement_year": replacement_year,    
        "replacement_pct": replacement_pct,      
        "total_storage_capex": total_storage_capex, 
        "total_capex": total_bat_capex
    }