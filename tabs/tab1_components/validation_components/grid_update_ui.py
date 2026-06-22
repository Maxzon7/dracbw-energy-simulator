# tabs/tab2_components/grid_upgrade_ui.py
import streamlit as st

def render_grid_upgrade_ui(scenario_id: str) -> dict:
    """
    Renders the UI for configuring a physical Grid Upgrade (Netzausbau).
    Instead of adding hardware to shave peaks, this expands the available grid capacity.
    """
    st.write("### 🔌 Grid Upgrade Parameters")
    st.info("This option simulates buying a larger grid connection instead of using local hardware.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_grid_limit = st.number_input(
            "New Grid Capacity (kW)", 
            min_value=10.0, max_value=5000.0, value=250.0, step=10.0,
            key=f"grid_limit_{scenario_id}",
            help="The expanded grid connection size (e.g., 250 kW for AC5)."
        )
        
        upgrade_capex = st.number_input(
            "Upgrade CapEx (€)", 
            min_value=0.0, value=63000.0, step=1000.0,
            key=f"grid_capex_{scenario_id}",
            help="One-time costs for trenching, transformer installation, etc."
        )

    with col2:
        monthly_fixed_costs = st.number_input(
            "New Monthly Fixed Costs (€)", 
            min_value=0.0, value=1500.0, step=100.0,
            key=f"grid_monthly_{scenario_id}",
            help="Additional monthly fixed fees (e.g., Trafo rental, higher capacity tariffs)."
        )
        
        # We can add an estimated lead time just to show the boss we think about real-world problems
        lead_time = st.selectbox(
            "Estimated Lead Time",
            ["0-6 Months", "6-12 Months", "1-2 Years", "2+ Years (Grid Congestion)"],
            key=f"grid_lead_{scenario_id}"
        )

    return {
        "new_grid_limit_kw": new_grid_limit,
        "upgrade_capex": upgrade_capex,
        "monthly_fixed_costs": monthly_fixed_costs,
        "lead_time": lead_time
    }