# demo_mode/demo_components/solar_ui.py
import streamlit as st

def render_demo_solar_ui(key_suffix: str = "") -> dict:
    """
    Renders the simplified Solar PV configuration panel for Demo Mode.
    Returns configured parameters for solar yield calculation.
    """
    t = st.session_state.get('t', {})

    st.write(f"### {t.get('demo_sol_title', '☀️ Solar PV Setup')}")
    st.info(t.get('demo_sol_info', "Configure the solar panels and system layout."))

    # Solar toggle at the component UI level
    has_solar = st.checkbox(t.get('demo_sol_checkbox', 'Integrate Solar PV'), value=True, key=f"demo_sol_integrate_check{key_suffix}")
    if not has_solar:
        return {
            "installed_kwp": 0.0,
            "performance_ratio": 85.0,
            "tilt": "30°",
            "azimuth": "South (180°)",
            "thermal_loss": True,
            "panel_type": "Monocrystalline Silicon",
            "ghi_source": "Open-Meteo API",
            "specific_yield": 950.0,
            "annual_sunshine_hours": 1500.0,
            "yield_factor": 1.0,
            "loss_inverter": 3.0,
            "loss_cabling": 1.5,
            "loss_soiling": 1.0,
            "loss_other": 2.0,
            "temp_coeff": 0.25
        }

    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**{t.get('demo_sol_hardware', 'Hardware Specifications')}**")
        panel_count = st.number_input(
            t.get('demo_sol_panels', "Number of Solar Panels"), 
            min_value=1, max_value=100000, value=500, step=10,
            key=f"demo_sol_panels{key_suffix}"
        )
        panel_wp = st.slider(
            t.get('demo_sol_wp', "Power per Panel (Watt-peak)"), 
            min_value=100, max_value=800, value=420, step=5,
            key=f"demo_sol_wp{key_suffix}"
        )
        
        installed_kwp = (panel_count * panel_wp) / 1000.0
        st.success(f"**{t.get('demo_sol_capacity', 'Total Capacity: ')}{installed_kwp:,.1f} kWp**")

    # Mapping to avoid breaking simulation logic string-matching
    azimuth_map = {
        t.get('demo_sol_az_south', "South (180°)"): "South (180°)",
        t.get('demo_sol_az_north', "North (0°)"): "North (0°)",
        t.get('demo_sol_az_east', "East (90°)"): "East (90°)",
        t.get('demo_sol_az_west', "West (270°)"): "West (270°)"
    }
    tilt_map = {
        t.get('demo_sol_tilt_flat', "0° (Flat)"): "0° (Flat)",
        "15°": "15°",
        "30°": "30°",
        "45°": "45°"
    }

    with col2:
        st.write(f"**{t.get('demo_sol_orientation', 'Orientation')}**")
        azimuth_sel = st.selectbox(
            t.get('demo_sol_azimuth', "Azimuth (Orientation)"), 
            options=list(azimuth_map.keys()),
            index=0,
            key=f"demo_sol_az{key_suffix}"
        )
        tilt_sel = st.selectbox(
            t.get('demo_sol_tilt', "Inclination (Tilt Angle)"), 
            options=list(tilt_map.keys()),
            index=2,
            key=f"demo_sol_tilt{key_suffix}"
        )
        
    azimuth = azimuth_map[azimuth_sel]
    tilt = tilt_map[tilt_sel]

    st.write(f"**{t.get('demo_sol_losses', 'System Losses & Efficiency')}**")
    col_loss1, col_loss2 = st.columns(2)
    with col_loss1:
        pr = st.slider(
            t.get('demo_sol_pr', "System Efficiency (PR %)"), 
            min_value=50, max_value=100, value=85,
            help=t.get('demo_sol_pr_help', "Accounts for losses like inverter efficiency, dust, and cables."),
            key=f"demo_sol_pr{key_suffix}"
        )
    with col_loss2:
        thermal_loss = st.checkbox(
            t.get('demo_sol_therm', "Enable Thermal Losses (>25°C penalty)"), 
            value=True,
            help=t.get('demo_sol_therm_help', "Reduces performance during hot summer hours."),
            key=f"demo_sol_therm{key_suffix}"
        )

    ghi_map = {
        t.get('demo_sol_ghi_api', "Open-Meteo API"): "Open-Meteo API",
        t.get('demo_sol_ghi_yield', "Manual specific yield"): "Manual specific yield",
        t.get('demo_sol_ghi_hours', "Manual sunshine hours"): "Manual sunshine hours"
    }

    # Advanced configurations under expander to prevent cluttering simple mode
    with st.expander(t.get('demo_sol_advanced', "Advanced Solar Parameters & Overrides"), expanded=False):
        panel_type = st.selectbox(
            t.get('demo_sol_panel_type', "Panel Type / Chemistry"),
            ["Monocrystalline Silicon", "Polycrystalline Silicon", "Thin-Film / CdTe"],
            index=0,
            key=f"demo_sol_panel_type{key_suffix}"
        )
        ghi_source_sel = st.selectbox(
            t.get('demo_sol_ghi_source', "Irradiation Data Source"),
            list(ghi_map.keys()),
            index=0,
            key=f"demo_sol_ghi_source{key_suffix}"
        )
        ghi_source = ghi_map[ghi_source_sel]
        
        specific_yield = 950.0
        annual_sunshine_hours = 1500.0
        if ghi_source == "Manual specific yield":
            specific_yield = st.number_input(
                t.get('demo_sol_spec_yield', "Manual Specific Yield (kWh/kWp/year)"),
                min_value=100.0, max_value=3000.0, value=950.0, step=50.0,
                key=f"demo_sol_specific_yield{key_suffix}"
            )
        elif ghi_source == "Manual sunshine hours":
            annual_sunshine_hours = st.number_input(
                t.get('demo_sol_sun_hours', "Manual Equivalent Full-Load Hours (hrs/year)"),
                min_value=100.0, max_value=4000.0, value=1500.0, step=50.0,
                key=f"demo_sol_sun_hours{key_suffix}"
            )
            
        yield_factor = st.slider(
            t.get('demo_sol_yield_factor', "Local Yield Multiplier / Shading Factor"),
            min_value=0.5, max_value=1.5, value=1.0, step=0.05,
            help=t.get('demo_sol_yield_factor_help', "Scales the output to model shadows, local microclimate, etc."),
            key=f"demo_sol_yield_factor{key_suffix}"
        )
        
        st.write(f"**{t.get('demo_sol_detailed_losses', 'Detailed Losses Configuration (%)')}**")
        col_dl1, col_dl2 = st.columns(2)
        loss_inverter = col_dl1.slider(t.get('demo_sol_loss_inv', "Inverter Losses (%)"), 0.0, 10.0, 3.0, step=0.5, key=f"demo_sol_loss_inv{key_suffix}")
        loss_cabling = col_dl2.slider(t.get('demo_sol_loss_cab', "Cabling Losses (%)"), 0.0, 5.0, 1.5, step=0.1, key=f"demo_sol_loss_cab{key_suffix}")
        loss_soiling = col_dl1.slider(t.get('demo_sol_loss_soil', "Soiling & Dirt Losses (%)"), 0.0, 5.0, 1.0, step=0.1, key=f"demo_sol_loss_soil{key_suffix}")
        loss_other = col_dl2.slider(t.get('demo_sol_loss_oth', "Other System Losses (%)"), 0.0, 10.0, 2.0, step=0.5, key=f"demo_sol_loss_oth{key_suffix}")
        
        temp_coeff = st.slider(
            t.get('demo_sol_temp_coeff', "Temperature Loss Coefficient (%/°C above 25°C)"),
            0.0, 1.0, 0.25, step=0.05,
            key=f"demo_sol_temp_coeff{key_suffix}"
        )

    return {
        "installed_kwp": installed_kwp,
        "performance_ratio": pr,
        "tilt": tilt,
        "azimuth": azimuth,
        "thermal_loss": thermal_loss,
        "panel_type": panel_type,
        "ghi_source": ghi_source,
        "specific_yield": specific_yield,
        "annual_sunshine_hours": annual_sunshine_hours,
        "yield_factor": yield_factor,
        "loss_inverter": loss_inverter,
        "loss_cabling": loss_cabling,
        "loss_soiling": loss_soiling,
        "loss_other": loss_other,
        "temp_coeff": temp_coeff
    }
