# tabs/tab2_components/feasibility_check.py
import streamlit as st
import pandas as pd

def render_feasibility_check(results: pd.DataFrame, grid_limit: float, current_params: dict, current_mode: str):
    """
    Renders the technical feasibility evaluation block based on grid limit breaches and battery C-rate.
    All outputs are natively translated to professional English.
    """
    peak_new = results['final_grid_load_kw'].max()
    
    # Safely extract battery configurations
    b_cap = current_params.get('battery', current_params).get('b_cap', 0) if isinstance(current_params, dict) else 0
    
    # Calculate C-Rate (Max discharge relative to usable capacity)
    max_discharge = results.get('battery_action_kw', pd.Series([0])).max()
    c_rate = (max_discharge / b_cap) if b_cap > 0 else 0
    
    # 1. Check: Was the grid limit breached? (Tolerance factor: 0.1 kW due to rounding)
    if peak_new > (grid_limit + 0.1):
        st.error(
            f"❌ **Technically NOT Feasible (Simulation Failed):**\n\n"
            f"The proposed hardware system cannot complete the required peak shaving. The optimized grid peak load ({peak_new:.1f} kW) "
            f"still breaches your established grid connection limit of {grid_limit:.1f} kW.\n\n"
            f"**Root Cause:** The battery power rating (kW) is insufficient, the energy capacity (kWh) is too small to bridge the entire duration of the peak, "
            f"or the system lacks sufficient recharge intervals/PV yield between consecutive peak events."
        )
    
    # 2. Check: Is the battery operational stress (C-Rate) realistic?
    elif c_rate > 1.2:
        st.warning(
            f"⚠️ **Technically Questionable (High Operational Risk):**\n\n"
            f"While the grid connection limit is mathematically maintained, the system configuration demands an extreme discharge rate (C-Rate: {c_rate:.2f}C).\n\n"
            f"**Root Cause:** The BESS asset is forced to draw {max_discharge:.1f} kW out of only {b_cap:.1f} kWh of physical capacity. Standard commercial-grade "
            f"storage solutions are typically limited to continuous rates between 0.5C and 1.0C. This configuration will cause severe thermal stress and accelerated "
            f"degradation in real-world deployment.\n\n"
            f"**Solution:** Increase the total battery capacity (kWh) to reduce hardware stress!"
        )
           
    # 3. Check: System is safe and stable
    else:
        extra_info = f"(Max hardware stress: {c_rate:.2f}C)" if b_cap > 0 else "(Pure Solar PV operation)"
        st.success(
            f"✅ **Technically Feasible & Validated!**\n\n"
            f"The proposed solution is physically stable. The optimized grid peak load is safely throttled to {peak_new:.1f} kW "
            f"(Limit: {grid_limit:.1f} kW), and hardware operating parameters are fully respected {extra_info}."
        )