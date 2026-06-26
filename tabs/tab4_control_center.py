# tabs/tab4_control_center.py
import streamlit as st
import json
import pandas as pd
from io import StringIO

# --- NEW CLASS-BASED IMPORTS ---
from logic.storage_manager import get_all_base_scenarios, init_storage
from classes.models import BaseScenario, SubScenario, Tariff, FinancialParams

# ==========================================
# SERIALIZATION HELPERS (Classes to JSON)
# ==========================================
def serialize_base(base: BaseScenario) -> dict:
    """Converts a BaseScenario Object into a JSON-friendly dictionary."""
    data = {
        "name": base.name,
        "id": base.id,
        "original_profile": base.original_profile.to_json(orient='records', date_format='iso') if base.original_profile is not None else None,
        "base_tariff": {
            "name": base.base_tariff.name,
            "contracted_capacity_kw": base.base_tariff.contracted_capacity_kw,
            "fixed_costs_per_year": base.base_tariff.fixed_costs_per_year,
            "price_per_kw_peak": base.base_tariff.price_per_kw_peak,
            "price_per_kwh": base.base_tariff.price_per_kwh,
            "is_custom": base.base_tariff.is_custom
        },
        "sub_scenarios": []
    }
    
    for sub in base.sub_scenarios:
        sub_data = {
            "name": sub.name,
            "id": sub.id,
            "battery_kwh": sub.battery_kwh,
            "battery_kw": sub.battery_kw,
            "solar_kwp": sub.solar_kwp,
            "custom_tariff": None,
            "financials": None,
            "simulated_profile": sub.simulated_profile.to_json(orient='records', date_format='iso') if sub.simulated_profile is not None else None,
        }
        
        if sub.custom_tariff:
            sub_data["custom_tariff"] = {
                "name": sub.custom_tariff.name,
                "contracted_capacity_kw": sub.custom_tariff.contracted_capacity_kw,
                "fixed_costs_per_year": sub.custom_tariff.fixed_costs_per_year,
                "price_per_kw_peak": sub.custom_tariff.price_per_kw_peak,
                "price_per_kwh": sub.custom_tariff.price_per_kwh,
                "is_custom": sub.custom_tariff.is_custom
            }
            
        if sub.financials:
            sub_data["financials"] = {
                "capex": sub.financials.capex,
                "opex_yearly": sub.financials.opex_yearly,
                "lifespan_years": sub.financials.lifespan_years,
                "inflation_rate": sub.financials.inflation_rate,
                "energy_price_growth": sub.financials.energy_price_growth
            }
            
        data["sub_scenarios"].append(sub_data)
        
    return data

# ==========================================
# DESERIALIZATION HELPERS (JSON to Classes)
# ==========================================
def deserialize_base(data: dict) -> BaseScenario:
    """Rebuilds a BaseScenario Object from a dictionary."""
    t_data = data.get("base_tariff", {})
    base_t = Tariff(
        name=t_data.get("name", "Imported"),
        contracted_capacity_kw=t_data.get("contracted_capacity_kw", 0),
        fixed_costs_per_year=t_data.get("fixed_costs_per_year", 0),
        price_per_kw_peak=t_data.get("price_per_kw_peak", 0),
        price_per_kwh=t_data.get("price_per_kwh", 0),
        is_custom=t_data.get("is_custom", False)
    )

    df_base = None
    if data.get("original_profile"):
        df_base = pd.read_json(StringIO(data["original_profile"]), orient='records')
        if 'timestamp' in df_base.columns:
            df_base['timestamp'] = pd.to_datetime(df_base['timestamp'])

    base = BaseScenario(
        name=data.get("name", "Imported Project"),
        id=data.get("id"),
        original_profile=df_base,
        base_tariff=base_t
    )

    for s_data in data.get("sub_scenarios", []):
        df_sub = None
        if s_data.get("simulated_profile"):
            df_sub = pd.read_json(StringIO(s_data["simulated_profile"]), orient='records')
            if 'timestamp' in df_sub.columns:
                df_sub['timestamp'] = pd.to_datetime(df_sub['timestamp'])

        fin_obj = None
        if s_data.get("financials"):
            f_data = s_data["financials"]
            fin_obj = FinancialParams(
                capex=f_data.get("capex", 0),
                opex_yearly=f_data.get("opex_yearly", 0),
                lifespan_years=f_data.get("lifespan_years", 15),
                inflation_rate=f_data.get("inflation_rate", 0.02),
                energy_price_growth=f_data.get("energy_price_growth", 0.04)
            )

        tar_obj = None
        if s_data.get("custom_tariff"):
            st_data = s_data["custom_tariff"]
            tar_obj = Tariff(
                name=st_data.get("name", "Custom"),
                contracted_capacity_kw=st_data.get("contracted_capacity_kw", 0),
                fixed_costs_per_year=st_data.get("fixed_costs_per_year", 0),
                price_per_kw_peak=st_data.get("price_per_kw_peak", 0),
                price_per_kwh=st_data.get("price_per_kwh", 0),
                is_custom=st_data.get("is_custom", False)
            )

        sub = SubScenario(
            name=s_data.get("name", "Imported Variant"),
            id=s_data.get("id"),
            battery_kwh=s_data.get("battery_kwh", 0),
            battery_kw=s_data.get("battery_kw", 0),
            solar_kwp=s_data.get("solar_kwp", 0),
            custom_tariff=tar_obj,
            financials=fin_obj,
            simulated_profile=df_sub
        )
        base.add_sub_scenario(sub)

    return base

# ==========================================
# MAIN UI RENDERER
# ==========================================
def render_tab4_control_center():
    st.header("🎛️ Control Center & Data Management")
    st.write("Manage your project data, export configurations, or import existing save files.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📥 Export Project Data")
        st.write("Download all current projects, variants, and financial settings as a single backup file.")

        bases = get_all_base_scenarios()
        if not bases:
            st.info("No projects available to export. Create a scenario in Tab 1 first.")
        else:
            export_data = [serialize_base(b) for b in bases]
            json_str = json.dumps(export_data, indent=2)

            st.download_button(
                label="📦 Download Workspace (.drac)",
                data=json_str,
                file_name="workspace_export.drac",
                mime="application/json",
                type="primary",
                use_container_width=True
            )

    with col2:
        st.subheader("📤 Import Project Data")
        st.write("Upload a previously saved .drac file to instantly restore your workspace.")

        uploaded_file = st.file_uploader("Upload .drac save file", type=["drac", "json"])
        
        if uploaded_file is not None:
            if st.button("🔄 Restore Workspace", type="primary", use_container_width=True):
                try:
                    content = uploaded_file.getvalue().decode("utf-8")
                    data_list = json.loads(content)
                    
                    # Reset storage and load imported classes
                    init_storage()
                    st.session_state.project_portfolio = []
                    
                    for b_data in data_list:
                        restored_base = deserialize_base(b_data)
                        st.session_state.project_portfolio.append(restored_base)
                        
                    st.success("✅ Workspace restored successfully! You can now view the data in Tabs 1-3.")
                except Exception as e:
                    st.error(f"Error loading file. Make sure it's a valid .drac file. Details: {e}")