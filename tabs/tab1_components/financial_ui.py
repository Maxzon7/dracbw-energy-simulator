# tabs/tab1_components/financial_ui.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os

def load_tariff_presets():
    """
    Loads the JSON file containing the official grid operator tariffs.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # HIER IST DER FIX: Genau dein Dateiname mit einem 'r'
    json_path = os.path.join(base_dir, "config", "tarif_presets.json") 
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def render_preset_selector(default_preset="🛠️ Custom Tariff"):
    """
    Renders the Preset Dropdown OUTSIDE the form to trigger autofill.
    """
    presets = load_tariff_presets()
    options = ["🛠️ Custom Tariff"]
    mapping = {}
    
    if presets:
        for country, operators in presets.items():
            for op, levels in operators.items():
                for lvl, data in levels.items():
                    label = f"{country} | {op} | {lvl}"
                    options.append(label)
                    # Exaktes Mapping auf unsere 4-Säulen Variablen
                    mapping[label] = {
                        "fixed_annual_connection_fee": data.get("fixed_annual_connection_fee", 0.0),
                        "fixed_annual_transport_fee": data.get("fixed_annual_transport_fee", 0.0),
                        "contracted_capacity_fee_per_kw_year": data.get("contracted_capacity_fee_per_kw_year", 0.0),
                        "peak_capacity_fee_per_kw_month": data.get("peak_capacity_fee_per_kw_month", 0.0),
                        "energy_price_normal_per_kwh": data.get("energy_price_normal_per_kwh", 0.0),
                        "energy_price_laag_per_kwh": data.get("energy_price_laag_per_kwh", 0.0),
                        "contracted_capacity_kw": data.get("max_connection_capacity_kw", 100.0),
                        "national_vat_pct": data.get("national_vat_pct", 0.0),
                        "local_tax_pct": data.get("local_tax_pct", 0.0)
                    }
                    
    # Merge custom tariffs from Tariff Configuration Manager
    custom_presets = st.session_state.get('custom_tariffs', {})
    for country, providers in custom_presets.items():
        for provider_name, data in providers.items():
            label = f"🛠️ [Custom] {country} | {provider_name}"
            options.append(label)
            
            fixed_ann_conn = float(data.get("fixed_monthly_fee", 0.0) or 0.0) * 12.0
            fixed_ann_trans = float(data.get("transport_fixed_fee", 0.0) or 0.0)
            
            if data.get("type") == "AC5_AC4":
                kw_contract = float(data.get("kw_contract_price", 0.0) or 0.0)
                kw_peak = float(data.get("kw_peak_penalty_price", 0.0) or 0.0)
                kwh_price = float(data.get("kwh_transport_price", 0.0) or 0.0)
            else:
                kw_contract = 0.0
                kw_peak = 0.0
                kwh_price = float(data.get("flatrate_price", 0.0) or 0.0)
                
            mapping[label] = {
                "fixed_annual_connection_fee": fixed_ann_conn,
                "fixed_annual_transport_fee": fixed_ann_trans,
                "contracted_capacity_fee_per_kw_year": kw_contract,
                "peak_capacity_fee_per_kw_month": kw_peak,
                "energy_price_normal_per_kwh": kwh_price,
                "energy_price_laag_per_kwh": kwh_price,
                "contracted_capacity_kw": 100.0,
                "national_vat_pct": 0.0,
                "local_tax_pct": 0.0
            }
                    
    default_idx = options.index(default_preset) if default_preset in options else 0
    sel = st.selectbox(
        "⚡ Load Grid Operator Tariffs (Autofill)", 
        options, 
        index=default_idx,
        help="Wähle einen Anbieter, um die Felder unten automatisch auszufüllen."
    )
    return sel, mapping.get(sel, None)

def get_generic_ac_presets() -> dict:
    return {
        "AC1 (3x25A - 17 kW)": {
            "fixed_annual_connection_fee": 200.0,
            "fixed_annual_transport_fee": 250.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.15,
            "energy_price_laag_per_kwh": 0.10,
            "contracted_capacity_kw": 17.0,
            "tariff_mode": "Generic AC1 (3x25A)"
        },
        "AC2 (3x35A - 24 kW)": {
            "fixed_annual_connection_fee": 250.0,
            "fixed_annual_transport_fee": 300.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.15,
            "energy_price_laag_per_kwh": 0.10,
            "contracted_capacity_kw": 24.0,
            "tariff_mode": "Generic AC2 (3x35A)"
        },
        "AC3 (3x50A - 35 kW)": {
            "fixed_annual_connection_fee": 280.0,
            "fixed_annual_transport_fee": 350.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.15,
            "energy_price_laag_per_kwh": 0.10,
            "contracted_capacity_kw": 35.0,
            "tariff_mode": "Generic AC3 (3x50A)"
        },
        "AC4 (3x80A - 55 kW)": {
            "fixed_annual_connection_fee": 320.0,
            "fixed_annual_transport_fee": 440.0,
            "contracted_capacity_fee_per_kw_year": 0.0,
            "peak_capacity_fee_per_kw_month": 0.0,
            "energy_price_normal_per_kwh": 0.15,
            "energy_price_laag_per_kwh": 0.10,
            "contracted_capacity_kw": 55.0,
            "tariff_mode": "Generic AC4 (3x80A)"
        },
        "AC5 (Large Consumer - 150 kW)": {
            "fixed_annual_connection_fee": 1500.0,
            "fixed_annual_transport_fee": 440.0,
            "contracted_capacity_fee_per_kw_year": 25.0,
            "peak_capacity_fee_per_kw_month": 3.50,
            "energy_price_normal_per_kwh": 0.15,
            "energy_price_laag_per_kwh": 0.10,
            "contracted_capacity_kw": 150.0,
            "tariff_mode": "Generic AC5"
        }
    }

def render_universal_multipillar_inputs(working_fin: dict, include_financials: bool = True) -> dict:
    """
    Renders the Universal Multi-Pillar Grid Tariff Engine inputs inside tab1 baseline.
    """
    if not include_financials:
        st.markdown("##### 🔌 Connection Capacity Setup")
        jan_cap_limit = st.number_input(
            "Contracted Capacity Limit (kW)", 
            value=float(working_fin.get('contracted_capacity_kw', 100.0)), 
            min_value=0.0, 
            step=10.0,
            key="mp_cap_limit_nofin"
        )
        st.caption("Financial fields are hidden. You can enable them above.")
        return {
            "tariff_mode": "Universal Multi-Pillar Tariff",
            "contracted_capacity_kw": jan_cap_limit,
            "lifespan_years": 15,
            "energy_price_growth": 4.0,
            "diesel_price_growth": 2.0,
            "inflation": 4.0
        }

    st.markdown("### 🏛️ Universal Multi-Pillar Grid Tariff Engine")
    st.caption("Configure multi-layered capacity penalties, time-of-use energy zones, and late-stage fiscal surcharges.")

    saved_sched = working_fin.get('monthly_tariff_schedule', {})
    def get_m_data(month_num):
        return saved_sched.get(str(month_num), {}) or saved_sched.get(month_num, {})
        
    jan_data = get_m_data(1)

    st.markdown("##### 📅 2.1 The Master Cascade Control")
    use_jan_default = st.checkbox(
        "Use January as global 12-Month contract template",
        value=bool(working_fin.get('use_jan_default', True) if 'use_jan_default' in working_fin else jan_data.get('use_jan_default', True)),
        key="mp_use_jan_default",
        help="If selected, replicates January's parameters across the entire 12-month array. Uncheck to configure monthly variations."
    )

    st.markdown("#### 📅 Month 1: January (Template)")
    
    col_p1, col_p2 = st.columns(2)
    jan_base = col_p1.number_input(
        "Pillar 1: Fixed Service Charges (€/Month)",
        value=float(jan_data.get('base_fee', 0.0)),
        step=50.0,
        key="mp_jan_base",
        help="Fixed monthly service fee (Cargo Comercialización / Transporte), billed regardless of load or energy."
    )
    jan_cap_limit = col_p2.number_input(
        "Pillar 2: Contracted Capacity Limit (kW)",
        value=float(jan_data.get('contracted_capacity_kw', working_fin.get('contracted_capacity_kw', 100.0))),
        min_value=0.0,
        step=10.0,
        key="mp_jan_cap_limit",
        help="Baseline capacity ceiling authorized by contract (Potencia Contratada / Uso de Red)."
    )
    
    col_p2_pr, col_p3 = st.columns(2)
    jan_cap_price = col_p2_pr.number_input(
        "Pillar 2: Contracted Capacity Price (€/kW/Month)",
        value=float(jan_data.get('contracted_capacity_price', 0.0)),
        min_value=0.0,
        step=1.0,
        key="mp_jan_cap_price",
        help="Price per kW of contracted capacity limit."
    )
    jan_peak_penalty = col_p3.number_input(
        "Pillar 3: Measured Peak Charge (€/kW/Month)",
        value=float(jan_data.get('peak_penalty_price', 0.0)),
        min_value=0.0,
        step=1.0,
        key="mp_jan_peak_penalty",
        help="Fee charged against the single highest peak load registered in that month (Consumo de Potencia)."
    )
    
    col_p4, = st.columns(1)
    jan_excess = col_p4.number_input(
        "Pillar 4: Excess Power Penalty Price (€/kW/Month)",
        value=float(jan_data.get('excess_penalty_price', 0.0)),
        min_value=0.0,
        step=1.0,
        key="mp_jan_excess",
        help="Financial penalty rate applied to the kW exceeding the contracted capacity limit (Exceso de Potencia). Billed at severe penalty rates."
    )

    st.markdown("##### 🕒 2.3 Time-of-Use Volumetric Energy Pillars")
    enable_tou = st.checkbox(
        "Enable Time-of-Use Energy Pricing",
        value=bool(jan_data.get('enable_tou', True)),
        key="mp_jan_enable_tou",
        help="Enable time-of-day tiered rates (Pico, Valle, Resto) instead of a flat energy price."
    )
    
    if enable_tou:
        st.markdown("**Energy Tariff Price Zones (Time-of-Use)**")
        jc_tou1, jc_tou2, jc_tou3 = st.columns(3)
        alta_pr = jc_tou1.number_input("Pico Price (€/kWh)", value=float(jan_data.get('alta', {}).get('price', 0.15)), step=0.01, key="mp_jan_alta_pr", help="Active energy price during peak/high-load hours (Energía Pico).")
        alta_start = jc_tou2.number_input("Pico Start Hour", min_value=0, max_value=23, value=int(jan_data.get('alta', {}).get('start_hour', 18)), step=1, key="mp_jan_alta_st")
        alta_end = jc_tou3.number_input("Pico End Hour", min_value=0, max_value=23, value=int(jan_data.get('alta', {}).get('end_hour', 23)), step=1, key="mp_jan_alta_ed")
        
        jc_tou4, jc_tou5, jc_tou6 = st.columns(3)
        baja_pr = jc_tou4.number_input("Valle Price (€/kWh)", value=float(jan_data.get('baja', {}).get('price', 0.10)), step=0.01, key="mp_jan_baja_pr", help="Active energy price during off-peak/night hours (Energía Valle).")
        baja_start = jc_tou5.number_input("Valle Start Hour", min_value=0, max_value=23, value=int(jan_data.get('baja', {}).get('start_hour', 23)), step=1, key="mp_jan_baja_st")
        baja_end = jc_tou6.number_input("Valle End Hour", min_value=0, max_value=23, value=int(jan_data.get('baja', {}).get('end_hour', 5)), step=1, key="mp_jan_baja_ed")
        
        jc_tou7, = st.columns(1)
        resto_pr = jc_tou7.number_input("Resto Price (€/kWh)", value=float(jan_data.get('resto', {}).get('price', 0.12)), step=0.01, key="mp_jan_resto_pr", help="Active energy price for remaining hours (Energía Resto).")
        flat_energy_price = 0.0
    else:
        flat_energy_price = st.number_input("Flat Energy Price (€/kWh)", value=float(jan_data.get('energy_price_normal', 0.15)), step=0.01, key="mp_jan_flat_ee", help="Flat rate price per kWh of energy consumed.")
        alta_pr, alta_start, alta_end = flat_energy_price, 18, 23
        baja_pr, baja_start, baja_end = flat_energy_price, 23, 5
        resto_pr = flat_energy_price

    st.markdown("##### 📊 2.4 Fiscal Surcharges & Credits Block")
    col_f1, = st.columns(1)
    jan_vat = col_f1.number_input("National VAT Surcharge (%)", value=float(jan_data.get('tax_pct', 27.0)), step=1.0, key="mp_jan_vat", help="National VAT percentage applied to the net invoice subtotal.")
    
    default_jan_prov = jan_data.get('provincial_taxes', [
        {"Tax Name": "Sobretasa Provincial Ley 2539", "Rate (%)": 1.0},
        {"Tax Name": "Tasa fisc. y Control", "Rate (%)": 1.5},
        {"Tax Name": "CCCE Ley 6497", "Rate (%)": 9.0}
    ])
    st.markdown("**Provincial Taxes Breakdown (%)**")
    prov_df = pd.DataFrame(default_jan_prov)
    edited_prov = st.data_editor(
        prov_df,
        num_rows="dynamic",
        key="mp_jan_prov_editor"
    )
    jan_prov_taxes = edited_prov.to_dict('records')

    default_jan_adj = jan_data.get('custom_adjustments', [
        {"Charge Name": "Cargo AP Municipal", "Amount (€)": 43091.0, "Is Pre-tax": False},
        {"Charge Name": "Seasonal Adjustment Net", "Amount (€)": 5198935.55, "Is Pre-tax": False},
        {"Charge Name": "Redondeo", "Amount (€)": -0.85, "Is Pre-tax": False}
    ])
    st.markdown("**Custom Charges & Adjustments (€/Month)**")
    adj_df = pd.DataFrame(default_jan_adj)
    edited_adj = st.data_editor(
        adj_df,
        num_rows="dynamic",
        key="mp_jan_adj_editor"
    )
    jan_adjustments = edited_adj.to_dict('records')

    jan_sched = {
        "base_fee": jan_base,
        "contracted_capacity_kw": jan_cap_limit,
        "contracted_capacity_price": jan_cap_price,
        "peak_penalty_price": jan_peak_penalty,
        "excess_penalty_price": jan_excess,
        "enable_tou": enable_tou,
        "energy_price_normal": flat_energy_price,
        "alta": {"price": alta_pr, "start_hour": alta_start, "end_hour": alta_end},
        "baja": {"price": baja_pr, "start_hour": baja_start, "end_hour": baja_end},
        "resto": {"price": resto_pr},
        "tax_pct": jan_vat,
        "provincial_taxes": jan_prov_taxes,
        "custom_adjustments": jan_adjustments
    }

    monthly_schedule = {"1": jan_sched}
    
    if not use_jan_default:
        months_list = ["February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        saved_overrides = []
        for m in range(2, 13):
            if str(m) in saved_sched or m in saved_sched:
                saved_overrides.append(months_list[m-2])
                
        overridden_months = st.multiselect(
            "Select Months with Custom Overrides:", 
            options=months_list, 
            default=saved_overrides, 
            key="mp_overrides"
        )
        
        for m in range(2, 13):
            m_name = months_list[m-2]
            if m_name in overridden_months:
                st.write("---")
                with st.expander(f"📅 Configuration for {m_name}", expanded=True):
                    m_data = get_m_data(m)
                    if not m_data:
                        m_data = jan_sched.copy()
                        
                    mc1, mc2 = st.columns(2)
                    m_base = mc1.number_input(f"Fixed Service Charges (€/Mo) - {m_name}", value=float(m_data.get('base_fee', jan_base)), step=50.0, key=f"mp_base_{m}")
                    m_cap_limit = mc2.number_input(f"Contracted Capacity Limit (kW) - {m_name}", value=float(m_data.get('contracted_capacity_kw', jan_cap_limit)), step=10.0, key=f"mp_cap_lim_{m}")
                    
                    mc_c_pr, mc_pk = st.columns(2)
                    m_cap_price = mc_c_pr.number_input(f"Contracted Capacity Price (€/kW/Mo) - {m_name}", value=float(m_data.get('contracted_capacity_price', jan_cap_price)), step=1.0, key=f"mp_cap_pr_{m}")
                    m_peak_penalty = mc_pk.number_input(f"Measured Peak Charge (€/kW/Mo) - {m_name}", value=float(m_data.get('peak_penalty_price', jan_peak_penalty)), step=1.0, key=f"mp_peak_pen_{m}")
                    
                    mc_ex = st.columns(1)[0]
                    m_excess = mc_ex.number_input(f"Excess Power Penalty Price (€/kW/Mo) - {m_name}", value=float(m_data.get('excess_penalty_price', jan_excess)), step=1.0, key=f"mp_ex_{m}")
                    
                    m_enable_tou = st.checkbox(f"Enable Time-of-Use Energy Pricing - {m_name}", value=bool(m_data.get('enable_tou', enable_tou)), key=f"mp_tou_en_{m}")
                    
                    if m_enable_tou:
                        mc_tou1, mc_tou2, mc_tou3 = st.columns(3)
                        m_alta_pr = mc_tou1.number_input(f"Pico Price (€/kWh) - {m_name}", value=float(m_data.get('alta', {}).get('price', alta_pr)), step=0.01, key=f"mp_alta_pr_{m}")
                        m_alta_start = mc_tou2.number_input(f"Pico Start Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('alta', {}).get('start_hour', alta_start)), step=1, key=f"mp_alta_st_{m}")
                        m_alta_end = mc_tou3.number_input(f"Pico End Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('alta', {}).get('end_hour', alta_end)), step=1, key=f"mp_alta_ed_{m}")
                        
                        mc_tou4, mc_tou5, mc_tou6 = st.columns(3)
                        m_baja_pr = mc_tou4.number_input(f"Valle Price (€/kWh) - {m_name}", value=float(m_data.get('baja', {}).get('price', baja_pr)), step=0.01, key=f"mp_baja_pr_{m}")
                        m_baja_start = mc_tou5.number_input(f"Valle Start Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('baja', {}).get('start_hour', baja_start)), step=1, key=f"mp_baja_st_{m}")
                        m_baja_end = mc_tou6.number_input(f"Valle End Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('baja', {}).get('end_hour', baja_end)), step=1, key=f"mp_baja_ed_{m}")
                        
                        mc_tou7 = st.columns(1)[0]
                        m_resto_pr = mc_tou7.number_input(f"Resto Price (€/kWh) - {m_name}", value=float(m_data.get('resto', {}).get('price', resto_pr)), step=0.01, key=f"mp_resto_pr_{m}")
                        m_flat_ee = 0.0
                    else:
                        m_flat_ee = st.number_input(f"Flat Energy Price (€/kWh) - {m_name}", value=float(m_data.get('energy_price_normal', flat_energy_price)), step=0.01, key=f"mp_flat_ee_{m}")
                        m_alta_pr, m_alta_start, m_alta_end = m_flat_ee, 18, 23
                        m_baja_pr, m_baja_start, m_baja_end = m_flat_ee, 23, 5
                        m_resto_pr = m_flat_ee
                        
                    mc_f1, = st.columns(1)
                    m_vat = mc_f1.number_input(f"National VAT (%) - {m_name}", value=float(m_data.get('tax_pct', jan_vat)), step=1.0, key=f"mp_vat_{m}")
                    
                    default_m_prov = m_data.get('provincial_taxes', jan_prov_taxes)
                    st.write(f"**Provincial Taxes Breakdown (%) - {m_name}**")
                    m_prov_df = pd.DataFrame(default_m_prov)
                    m_edited_prov = st.data_editor(
                        m_prov_df,
                        num_rows="dynamic",
                        key=f"mp_prov_editor_{m}"
                    )
                    m_prov_taxes = m_edited_prov.to_dict('records')
                    
                    default_m_adj = m_data.get('custom_adjustments', jan_adjustments)
                    st.write(f"**Custom Charges & Adjustments (€/Month) - {m_name}**")
                    m_adj_df = pd.DataFrame(default_m_adj)
                    m_edited_adj = st.data_editor(
                        m_adj_df,
                        num_rows="dynamic",
                        key=f"mp_adj_editor_{m}"
                    )
                    m_adjustments = m_edited_adj.to_dict('records')
                    
                    monthly_schedule[str(m)] = {
                        "base_fee": m_base,
                        "contracted_capacity_kw": m_cap_limit,
                        "contracted_capacity_price": m_cap_price,
                        "peak_penalty_price": m_peak_penalty,
                        "excess_penalty_price": m_excess,
                        "enable_tou": m_enable_tou,
                        "energy_price_normal": m_flat_ee,
                        "alta": {"price": m_alta_pr, "start_hour": m_alta_start, "end_hour": m_alta_end},
                        "baja": {"price": m_baja_pr, "start_hour": m_baja_start, "end_hour": m_baja_end},
                        "resto": {"price": m_resto_pr},
                        "tax_pct": m_vat,
                        "provincial_taxes": m_prov_taxes,
                        "custom_adjustments": m_adjustments
                    }
            else:
                monthly_schedule[str(m)] = jan_sched.copy()
    else:
        for m in range(2, 13):
            monthly_schedule[str(m)] = jan_sched.copy()

    st.divider()
    st.markdown("##### ⚙️ Project Specifics & Infrastructure")
    
    col_s1, col_s2 = st.columns(2)
    base_capex = col_s1.number_input(
        "Baseline Grid CAPEX (€)", 
        value=float(working_fin.get('baseline_grid_capex', 0.0)), 
        step=1000.0,
        key="mp_capex"
    )
    feed_in = col_s2.number_input(
        "Feed-in Tariff (€/kWh)", 
        value=float(working_fin.get('feed_in_tariff', 0.08)), 
        step=0.01,
        key="mp_fit"
    )
    
    col_s3, col_s4 = st.columns(2)
    inflation = col_s3.slider(
        "General Inflation (%)", 
        min_value=0.0, 
        max_value=20.0, 
        value=float(working_fin.get('inflation', 4.0)), 
        step=0.5,
        key="mp_inflation",
        help="Stable general inflation rate. Standard is 4%."
    )
    diesel = col_s4.number_input(
        "Diesel Price (€/L)", 
        value=float(working_fin.get('diesel_price', 1.50)), 
        step=0.05,
        key="mp_diesel"
    )
    
    col_s5, col_s6 = st.columns(2)
    lifespan_years = col_s5.number_input(
        "Project Lifespan (Years)", 
        value=int(working_fin.get('lifespan_years', 15)), 
        min_value=1, 
        max_value=25, 
        step=1,
        key="mp_lifespan"
    )
    
    col_s7, col_s8 = st.columns(2)
    energy_price_growth = col_s7.slider(
        "Electricity Tariff Escalation (%/Yr)", 
        min_value=0.0, 
        max_value=20.0, 
        value=float(working_fin.get('energy_price_growth', 4.0)), 
        step=0.5,
        key="mp_ee_esc"
    )
    diesel_price_growth = col_s8.slider(
        "Diesel Price Escalation (%/Yr)", 
        min_value=0.0, 
        max_value=20.0, 
        value=float(working_fin.get('diesel_price_growth', 2.0)), 
        step=0.5,
        key="mp_di_esc"
    )

    return {
        "tariff_mode": "Universal Multi-Pillar Tariff",
        "use_jan_default": use_jan_default,
        "monthly_tariff_schedule": monthly_schedule,
        "fixed_annual_connection_fee": jan_base * 12.0,
        "fixed_annual_transport_fee": 0.0,
        "contracted_capacity_kw": jan_cap_limit,
        "contracted_capacity_fee_per_kw_year": jan_cap_price * 12.0,
        "peak_capacity_fee_per_kw_month": jan_peak_penalty,
        "energy_price_normal_per_kwh": resto_pr,
        "energy_price_laag_per_kwh": baja_pr,
        "baseline_grid_capex": base_capex,
        "feed_in_tariff": feed_in,
        "inflation": inflation,
        "diesel_price": diesel,
        "lifespan_years": lifespan_years,
        "energy_price_growth": energy_price_growth,
        "diesel_price_growth": diesel_price_growth,
        "national_vat_pct": jan_vat,
        "local_tax_pct": sum(float(p.get('Rate (%)', 0.0) or 0.0) for p in jan_prov_taxes),
        "energy_charge": resto_pr,
        "demand_charge": jan_cap_price * 12.0
    }

def render_financial_inputs(working_fin: dict, include_financials: bool = True, contract_mode: str = "Real Contract Preset") -> dict:
    """
    Renders the manual input fields INSIDE the form.
    Receives 'working_fin' which contains either the loaded preset or the saved vault data.
    """
    if contract_mode == "Universal Multi-Pillar Tariff":
        return render_universal_multipillar_inputs(working_fin, include_financials)
    contracted_kw = float(working_fin.get('contracted_capacity_kw', 100.0))
    fixed_conn = float(working_fin.get('fixed_annual_connection_fee', 0.0))
    fixed_trans = float(working_fin.get('fixed_annual_transport_fee', 0.0))
    contract_price = float(working_fin.get('contracted_capacity_fee_per_kw_year', 0.0))
    peak_price = float(working_fin.get('peak_capacity_fee_per_kw_month', 0.0))
    kwh_norm = float(working_fin.get('energy_price_normal_per_kwh', 0.15))
    kwh_laag = float(working_fin.get('energy_price_laag_per_kwh', 0.10))
    base_capex = float(working_fin.get('baseline_grid_capex', 0.0))
    feed_in = float(working_fin.get('feed_in_tariff', 0.08))
    inflation = float(working_fin.get('inflation', 3.0))
    diesel = float(working_fin.get('diesel_price', 1.50))
    national_vat = float(working_fin.get('national_vat_pct', 0.0))
    local_tax = float(working_fin.get('local_tax_pct', 0.0))

    t_mode = working_fin.get('tariff_mode', "🛠️ Custom Tariff")
    
    if include_financials and t_mode in ["🛠️ Custom Tariff", "🛠️ Volatile Monthly Custom Tariff", "🛠️ Manual Custom Tariff"]:
        st.markdown("##### 📅 Custom Tariff Configuration (Monthly)")
        st.caption("Configure connection fees, peak penalties, and energy rates month-by-month. January serves as the default template.")
        
        saved_sched = working_fin.get('monthly_tariff_schedule', {})
        def get_m_data(month_num):
            return saved_sched.get(str(month_num), {}) or saved_sched.get(month_num, {})
            
        jan_data = get_m_data(1)
        
        # Prefill from legacy if monthly schedule is missing
        if not jan_data and t_mode == "🛠️ Manual Custom Tariff":
            jan_data = {
                "base_fee": fixed_conn / 12.0,
                "contracted_capacity_kw": contracted_kw,
                "contracted_capacity_price": contract_price / 12.0,
                "peak_penalty_price": peak_price,
                "energy_price_normal": kwh_norm,
                "tax_pct": national_vat,
                "local_tax_pct": local_tax
            }
        
        st.markdown("#### 📅 Month 1: January (Template)")
        jc1, jc2 = st.columns(2)
        jan_base = jc1.number_input("Base Connection Fee (€/Mo)", value=float(jan_data.get('base_fee', 0.0)), step=100.0, key=f"jan_base_{contract_mode}", help="Fixed basic fee charged every month regardless of electricity consumption.")
        jan_cap_limit = jc2.number_input("Contracted Capacity Limit (kW)", value=float(jan_data.get('contracted_capacity_kw', contracted_kw)), step=10.0, key=f"jan_cap_lim_{contract_mode}", help="The capacity limit in kW agreed upon in your contract. If your actual load exceeds this, penalty fees are charged.")
        
        # Checkbox for Time-of-Use pricing
        enable_tou = st.checkbox("Enable Time-of-Use Energy Pricing (Alta/Baja/Resto)", value=bool(jan_data.get('enable_tou', False)), key=f"jan_tou_en_{contract_mode}", help="Check this to enable time-of-use pricing bands (Alta, Baja, Resto) instead of a single flat rate.")
        
        if enable_tou:
            jan_cap_price = 0.0
            
            st.markdown("**Energy Tariff Price Zones (Time-of-Use)**")
            jc_tou1, jc_tou2, jc_tou3 = st.columns(3)
            alta_pr = jc_tou1.number_input("Alta Price (€/kWh)", value=float(jan_data.get('alta', {}).get('price', 0.15)), step=0.01, key=f"jan_alta_pr_{contract_mode}", help="Active energy price during peak/high-load hours (Alta).")
            alta_start = jc_tou2.number_input("Alta Start Hour", min_value=0, max_value=23, value=int(jan_data.get('alta', {}).get('start_hour', 18)), step=1, key=f"jan_alta_st_{contract_mode}", help="Starting hour of the Alta pricing window (e.g. 18 for 18:00).")
            alta_end = jc_tou3.number_input("Alta End Hour", min_value=0, max_value=23, value=int(jan_data.get('alta', {}).get('end_hour', 23)), step=1, key=f"jan_alta_ed_{contract_mode}", help="Ending hour of the Alta pricing window (e.g. 23 for 23:00).")
            
            jc_tou4, jc_tou5, jc_tou6 = st.columns(3)
            baja_pr = jc_tou4.number_input("Baja Price (€/kWh)", value=float(jan_data.get('baja', {}).get('price', 0.10)), step=0.01, key=f"jan_baja_pr_{contract_mode}", help="Active energy price during off-peak/night hours (Baja).")
            baja_start = jc_tou5.number_input("Baja Start Hour", min_value=0, max_value=23, value=int(jan_data.get('baja', {}).get('start_hour', 23)), step=1, key=f"jan_baja_st_{contract_mode}", help="Starting hour of the Baja pricing window (e.g. 23 for 23:00).")
            baja_end = jc_tou6.number_input("Baja End Hour", min_value=0, max_value=23, value=int(jan_data.get('baja', {}).get('end_hour', 5)), step=1, key=f"jan_baja_ed_{contract_mode}", help="Ending hour of the Baja pricing window (e.g. 5 for 05:00).")
            
            jc_tou7, = st.columns(1)
            resto_pr = jc_tou7.number_input("Resto Price (€/kWh)", value=float(jan_data.get('resto', {}).get('price', 0.12)), step=0.01, key=f"jan_resto_pr_{contract_mode}", help="Active energy price for all remaining hours outside Alta and Baja (Resto).")
            
            jc_pen1, jc_pen2 = st.columns(2)
            jan_peak_penalty = jc_pen1.number_input("Peak Penalty Price (€/kW/Mo)", value=float(jan_data.get('peak_penalty_price', 0.0)), step=10.0, key=f"jan_peak_pen_{contract_mode}", help="Fee charged per kW of the maximum measured peak load during the month.")
            jan_excess = jc_pen2.number_input("Excess Penalty Price (€/kW/Mo)", value=float(jan_data.get('excess_penalty_price', 0.0)), step=10.0, key=f"jan_ex_{contract_mode}", help="Penalty fee charged per kW by which your actual peak load exceeded your contracted capacity limit.")
            flat_energy_price = 0.0
        else:
            jc3, jc4 = st.columns(2)
            jan_cap_price = jc3.number_input("Contracted Capacity Price (€/kW/Mo)", value=float(jan_data.get('contracted_capacity_price', 0.0)), step=1.0, key=f"jan_cap_pr_{contract_mode}", help="Capacity price charged monthly per kW of your contracted capacity limit.")
            
            # Default Peak Penalty Price is by default the Contracted Capacity Price
            default_peak = float(jan_data.get('peak_penalty_price', jan_cap_price))
            jan_peak_penalty = jc4.number_input("Peak Penalty Price (€/kW/Mo)", value=default_peak, step=1.0, key=f"jan_peak_pen_{contract_mode}", help="Fee charged per kW of the maximum measured peak load during the month. Defaults to the contracted capacity price if not set.")
            
            jc5, jc6 = st.columns(2)
            jan_excess = jc5.number_input("Excess Penalty Price (€/kW/Mo)", value=float(jan_data.get('excess_penalty_price', jan_cap_price)), step=1.0, key=f"jan_ex_{contract_mode}", help="Penalty fee charged per kW by which your actual peak load exceeded your contracted capacity limit. Defaults to the contracted capacity price if not set.")
            flat_energy_price = jc6.number_input("Energy Price (€/kWh)", value=float(jan_data.get('energy_price_normal', 0.15)), step=0.01, key=f"jan_flat_ee_{contract_mode}", help="Flat rate price per kWh of energy consumed.")
            
            alta_pr, alta_start, alta_end = flat_energy_price, 18, 23
            baja_pr, baja_start, baja_end = flat_energy_price, 23, 5
            resto_pr = flat_energy_price
            
        jc7, jc8, jc9 = st.columns(3)
        jan_vat = jc7.number_input("National VAT (%)", value=float(jan_data.get('tax_pct', 0.0)), step=1.0, key=f"jan_vat_{contract_mode}", help="National value-added tax (VAT) percentage applied to the net invoice total.")
        jan_local_tax = jc8.number_input("Provincial & Municipal Taxes (%)", value=float(jan_data.get('local_tax_pct', 0.0)), step=1.0, key=f"jan_local_tax_{contract_mode}", help="Local, municipal, or provincial tax surcharge percentage applied to the net invoice total.")
        jan_subsidy = jc9.number_input("Subsidies / Credits (€/Mo)", value=float(jan_data.get('subsidy_amount', 0.0)), step=10.0, key=f"jan_sub_{contract_mode}", help="Monthly subsidy amount or credit subtracted from the grid invoice.")
        
        jan_sched = {
            "base_fee": jan_base,
            "contracted_capacity_kw": jan_cap_limit,
            "contracted_capacity_price": jan_cap_price,
            "peak_penalty_price": jan_peak_penalty,
            "excess_penalty_price": jan_excess,
            "enable_tou": enable_tou,
            "energy_price_normal": flat_energy_price,
            "alta": {"price": alta_pr, "start_hour": alta_start, "end_hour": alta_end},
            "baja": {"price": baja_pr, "start_hour": baja_start, "end_hour": baja_end},
            "resto": {"price": resto_pr},
            "tax_pct": jan_vat,
            "local_tax_pct": jan_local_tax,
            "subsidy_amount": jan_subsidy
        }
        
        monthly_schedule = {"1": jan_sched}
        
        # Checkbox for template cascading
        use_jan_default = st.checkbox("Use January as default template for all months", value=bool(jan_data.get('use_jan_default', True)), key=f"use_jan_def_{contract_mode}", help="Uncheck this to enable monthly varying overrides for February through December.")
        jan_sched["use_jan_default"] = use_jan_default
        
        if not use_jan_default:
            months_list = ["February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            saved_overrides = []
            for m in range(2, 13):
                if str(m) in saved_sched or m in saved_sched:
                    saved_overrides.append(months_list[m-2])
                    
            overridden_months = st.multiselect("Select Months with Custom Overrides:", options=months_list, default=saved_overrides, key=f"overrides_{contract_mode}")
            
            for m in range(2, 13):
                m_name = months_list[m-2]
                if m_name in overridden_months:
                    st.write("---")
                    with st.expander(f"📅 Configuration for {m_name}", expanded=True):
                        m_data = get_m_data(m)
                        
                        mc1, mc2 = st.columns(2)
                        m_base = mc1.number_input(f"Base Connection Fee (€/Mo) - {m_name}", value=float(m_data.get('base_fee', jan_base)), step=100.0, key=f"m_base_{m}_{contract_mode}")
                        m_cap_limit = mc2.number_input(f"Contracted Capacity Limit (kW) - {m_name}", value=float(m_data.get('contracted_capacity_kw', jan_cap_limit)), step=10.0, key=f"m_cap_lim_{m}_{contract_mode}")
                        
                        m_enable_tou = st.checkbox(f"Enable Time-of-Use Energy Pricing (Alta/Baja/Resto) - {m_name}", value=bool(m_data.get('enable_tou', enable_tou)), key=f"m_tou_en_{m}_{contract_mode}")
                        
                        if m_enable_tou:
                            m_cap_price = 0.0
                            
                            mc_tou1, mc_tou2, mc_tou3 = st.columns(3)
                            m_alta_pr = mc_tou1.number_input(f"Alta Price (€/kWh) - {m_name}", value=float(m_data.get('alta', {}).get('price', alta_pr)), step=0.01, key=f"m_alta_pr_{m}_{contract_mode}")
                            m_alta_start = mc_tou2.number_input(f"Alta Start Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('alta', {}).get('start_hour', m_data.get('alta', {}).get('start_hour', alta_start))), step=1, key=f"m_alta_st_{m}_{contract_mode}")
                            m_alta_end = mc_tou3.number_input(f"Alta End Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('alta', {}).get('end_hour', m_data.get('alta', {}).get('end_hour', alta_end))), step=1, key=f"m_alta_ed_{m}_{contract_mode}")
                            
                            mc_tou4, mc_tou5, mc_tou6 = st.columns(3)
                            m_baja_pr = mc_tou4.number_input(f"Baja Price (€/kWh) - {m_name}", value=float(m_data.get('baja', {}).get('price', baja_pr)), step=0.01, key=f"m_baja_pr_{m}_{contract_mode}")
                            m_baja_start = mc_tou5.number_input(f"Baja Start Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('baja', {}).get('start_hour', m_data.get('baja', {}).get('start_hour', baja_start))), step=1, key=f"m_baja_st_{m}_{contract_mode}")
                            m_baja_end = mc_tou6.number_input(f"Baja End Hour - {m_name}", min_value=0, max_value=23, value=int(m_data.get('baja', {}).get('end_hour', m_data.get('baja', {}).get('end_hour', baja_end))), step=1, key=f"m_baja_ed_{m}_{contract_mode}")
                            
                            mc_tou7, = st.columns(1)
                            m_resto_pr = mc_tou7.number_input(f"Resto Price (€/kWh) - {m_name}", value=float(m_data.get('resto', {}).get('price', resto_pr)), step=0.01, key=f"m_resto_pr_{m}_{contract_mode}")
                            
                            mc_pen1, mc_pen2 = st.columns(2)
                            m_peak_penalty = mc_pen1.number_input(f"Peak Penalty (€/kW/Mo) - {m_name}", value=float(m_data.get('peak_penalty_price', jan_peak_penalty)), step=10.0, key=f"m_peak_pen_{m}_{contract_mode}")
                            m_excess = mc_pen2.number_input(f"Excess Penalty (€/kW/Mo) - {m_name}", value=float(m_data.get('excess_penalty_price', jan_excess)), step=10.0, key=f"m_ex_{m}_{contract_mode}")
                            m_flat_ee = 0.0
                        else:
                            mc3, mc4 = st.columns(2)
                            m_cap_price = mc3.number_input(f"Contracted Capacity Price (€/kW/Mo) - {m_name}", value=float(m_data.get('contracted_capacity_price', jan_cap_price)), step=1.0, key=f"m_cap_pr_{m}_{contract_mode}")
                            m_peak_penalty = mc4.number_input(f"Peak Penalty (€/kW/Mo) - {m_name}", value=float(m_data.get('peak_penalty_price', m_cap_price)), step=1.0, key=f"m_peak_pen_{m}_{contract_mode}")
                            
                            mc5, mc6 = st.columns(2)
                            m_excess = mc5.number_input(f"Excess Penalty Price (€/kW/Mo) - {m_name}", value=float(m_data.get('excess_penalty_price', m_cap_price)), step=1.0, key=f"m_ex_{m}_{contract_mode}")
                            m_flat_ee = mc6.number_input(f"Energy Price (€/kWh) - {m_name}", value=float(m_data.get('energy_price_normal', flat_energy_price)), step=0.01, key=f"m_flat_ee_{m}_{contract_mode}")
                            
                            m_alta_pr, m_alta_start, m_alta_end = m_flat_ee, 18, 23
                            m_baja_pr, m_baja_start, m_baja_end = m_flat_ee, 23, 5
                            m_resto_pr = m_flat_ee
                            
                        mc7, mc8, mc9 = st.columns(3)
                        m_vat = mc7.number_input(f"National VAT (%) - {m_name}", value=float(m_data.get('tax_pct', jan_vat)), step=1.0, key=f"m_vat_{m}_{contract_mode}")
                        m_local_tax = mc8.number_input(f"Provincial & Municipal Taxes (%) - {m_name}", value=float(m_data.get('local_tax_pct', jan_local_tax)), step=1.0, key=f"m_local_tax_{m}_{contract_mode}")
                        m_subsidy = mc9.number_input(f"Subsidies/Credits (€/Mo) - {m_name}", value=float(m_data.get('subsidy_amount', jan_subsidy)), step=10.0, key=f"m_sub_{m}_{contract_mode}")
                        
                        monthly_schedule[str(m)] = {
                            "base_fee": m_base,
                            "contracted_capacity_kw": m_cap_limit,
                            "contracted_capacity_price": m_cap_price,
                            "peak_penalty_price": m_peak_penalty,
                            "excess_penalty_price": m_excess,
                            "enable_tou": m_enable_tou,
                            "energy_price_normal": m_flat_ee,
                            "alta": {"price": m_alta_pr, "start_hour": m_alta_start, "end_hour": m_alta_end},
                            "baja": {"price": m_baja_pr, "start_hour": m_baja_start, "end_hour": m_baja_end},
                            "resto": {"price": m_resto_pr},
                            "tax_pct": m_vat,
                            "local_tax_pct": m_local_tax,
                            "subsidy_amount": m_subsidy
                        }
                else:
                    monthly_schedule[str(m)] = jan_sched.copy()
        else:
            for m in range(2, 13):
                monthly_schedule[str(m)] = jan_sched.copy()
                
        st.divider()
        st.markdown("##### ⚙️ Project Specifics & Infrastructure")
        c1, c2, c3 = st.columns(3)
        c1.metric("Grid Capacity Limit (Jan)", f"{jan_cap_limit:.1f} kW")
        base_capex = c2.number_input("Baseline Grid CAPEX (€)", value=float(working_fin.get('baseline_grid_capex', 0.0)), step=1000.0, key="vol_capex")
        feed_in = c3.number_input("Feed-in Tariff (€/kWh)", value=float(working_fin.get('feed_in_tariff', 0.08)), step=0.01, key="vol_fit")
        
        c4, c5, c6 = st.columns(3)
        inflation = c4.number_input("General Inflation (%)", value=float(working_fin.get('inflation', 3.0)), step=0.5, key="vol_inf")
        diesel = c5.number_input("Diesel Price (€/L)", value=float(working_fin.get('diesel_price', 1.50)), step=0.05, key="vol_diesel")
        lifespan_years = c6.number_input("Project Lifespan (Years)", value=int(working_fin.get('lifespan_years', 15)), min_value=1, max_value=25, step=1, key="vol_life")
        
        c7, c8 = st.columns(2)
        energy_price_growth = c7.number_input("Electricity Tariff Escalation (%/Yr)", value=float(working_fin.get('energy_price_growth', 4.0)), step=0.5, key="vol_ee_esc")
        diesel_price_growth = c8.number_input("Diesel Price Escalation (%/Yr)", value=float(working_fin.get('diesel_price_growth', 2.0)), step=0.5, key="vol_di_esc")
        
        return {
            "tariff_mode": "🛠️ Custom Tariff",
            "monthly_tariff_schedule": monthly_schedule,
            "fixed_annual_connection_fee": jan_base * 12.0,
            "fixed_annual_transport_fee": 0.0,
            "contracted_capacity_kw": jan_cap_limit,
            "contracted_capacity_fee_per_kw_year": jan_cap_price * 12.0,
            "peak_capacity_fee_per_kw_month": jan_peak_penalty,
            "energy_price_normal_per_kwh": resto_pr,
            "energy_price_laag_per_kwh": baja_pr,
            "baseline_grid_capex": base_capex,
            "feed_in_tariff": feed_in,
            "inflation": inflation,
            "diesel_price": diesel,
            "lifespan_years": lifespan_years,
            "energy_price_growth": energy_price_growth,
            "diesel_price_growth": diesel_price_growth,
            "national_vat_pct": jan_vat,
            "local_tax_pct": jan_local_tax,
            "energy_charge": resto_pr,
            "demand_charge": jan_cap_price * 12.0
        }

    if include_financials:
        st.markdown("##### ✍️ 4-Pillar Tariff & Financial Parameters")
        st.caption("Values are pre-filled if a Preset is selected. You can freely overwrite them here before saving.")
        
        col1, col2 = st.columns(2)
        with col1:
            fixed_conn = st.number_input("1. Annual Connection Fee (€/Yr)", value=fixed_conn, step=10.0)
            fixed_trans = st.number_input("2. Annual Transport Fee (€/Yr)", value=fixed_trans, step=10.0)
            contract_price = st.number_input("3. Contracted Capacity Price (€/kW/Yr)", value=contract_price, step=1.0)
        with col2:
            peak_price = st.number_input("4. Monthly Peak Penalty (€/kW/Mo)", value=peak_price, step=0.1)
            kwh_norm = st.number_input("Energy Price Normal (€/kWh)", value=kwh_norm, format="%.4f", step=0.01)
            kwh_laag = st.number_input("Energy Price Off-Peak (€/kWh)", value=kwh_laag, format="%.4f", step=0.01)
            
        st.divider()
        st.markdown("##### 🏛️ Taxes & Duties Surcharges (Optional)")
        c_tax1, c_tax2 = st.columns(2)
        national_vat = c_tax1.number_input("National VAT (%)", value=national_vat, min_value=0.0, max_value=100.0, step=1.0)
        local_tax = c_tax2.number_input("Provincial & Municipal Taxes (%)", value=local_tax, min_value=0.0, max_value=100.0, step=0.5)
            
        st.divider()
        st.markdown("##### ⚙️ Project Specifics & Infrastructure")
        c1, c2, c3 = st.columns(3)
        
        if contract_mode == "Generic Grid Limit (No Contract)":
            contracted_kw = c1.number_input("Grid Connection Capacity (kW)", value=contracted_kw, min_value=0.0, step=10.0)
        else:
            c1.metric("Grid Capacity Limit", f"{contracted_kw:.1f} kW")
            
        base_capex = c2.number_input("Baseline Grid CAPEX (€)", value=base_capex, step=1000.0)
        feed_in = c3.number_input("Feed-in Tariff (€/kWh)", value=feed_in, step=0.01)
        
        c4, c5, c6 = st.columns(3)
        inflation = c4.number_input("General Inflation (%)", value=inflation, step=0.5)
        diesel = c5.number_input("Diesel Price (€/L)", value=diesel, step=0.05)
        lifespan_years = c6.number_input("Project Lifespan (Years)", value=int(working_fin.get('lifespan_years', 15)), min_value=1, max_value=25, step=1)
        
        c7, c8 = st.columns(2)
        energy_price_growth = c7.number_input("Electricity Tariff Escalation (%/Yr)", value=float(working_fin.get('energy_price_growth', 4.0)), step=0.5)
        diesel_price_growth = c8.number_input("Diesel Price Escalation (%/Yr)", value=float(working_fin.get('diesel_price_growth', 2.0)), step=0.5)
    else:
        st.markdown("##### 🔌 Connection Capacity Setup")
        if contract_mode == "Generic Grid Limit (No Contract)":
            contracted_kw = st.number_input("Grid Connection Capacity (kW)", value=contracted_kw, min_value=0.0, step=10.0)
        elif contract_mode == "No Contract (Consumption Only)":
            st.info("Grid connection limit is set to 0.0 kW (Off-grid / Consumption Only).")
            contracted_kw = 0.0
        else:
            st.metric("Grid Capacity Limit", f"{contracted_kw:.1f} kW")
        
        # In non-financial mode, pricing is kept at 0 or preset values, but hidden from UI
        st.caption("Financial fields are hidden. You can enable them above.")
        lifespan_years = 15
        energy_price_growth = 4.0
        diesel_price_growth = 2.0

    # We output the data so the form submit button can save it
    return {
        "tariff_mode": working_fin.get('tariff_mode', "🛠️ Custom Tariff"),
        "fixed_annual_connection_fee": fixed_conn,
        "fixed_annual_transport_fee": fixed_trans,
        "contracted_capacity_kw": contracted_kw,
        "contracted_capacity_fee_per_kw_year": contract_price,
        "peak_capacity_fee_per_kw_month": peak_price,
        "energy_price_normal_per_kwh": kwh_norm,
        "energy_price_laag_per_kwh": kwh_laag,
        "baseline_grid_capex": base_capex,
        "feed_in_tariff": feed_in,
        "inflation": inflation,
        "diesel_price": diesel,
        "lifespan_years": lifespan_years,
        "energy_price_growth": energy_price_growth,
        "diesel_price_growth": diesel_price_growth,
        "national_vat_pct": national_vat,
        "local_tax_pct": local_tax,
        "energy_charge": kwh_norm, # Legacy fallback
        "demand_charge": contract_price + (peak_price * 12) # Legacy fallback
    }

def render_financial_summary(p_fin: dict):
    """
    Renders the clean overview. Call this in Tab 0!
    """
    if not p_fin:
        return
        
    with st.expander("💳 Active Financial & Tariff Overview", expanded=True):
        st.success(f"**Active Tariff:** {p_fin.get('tariff_mode', 'N/A')}")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown("**1. Fixed Grid Costs**")
            st.write(f"- Connection Fee: `{p_fin.get('fixed_annual_connection_fee', 0):,.2f} €/Yr`")
            st.write(f"- Transport Fee: `{p_fin.get('fixed_annual_transport_fee', 0):,.2f} €/Yr`")
        with sc2:
            st.markdown("**2. Capacity Metrics**")
            st.write(f"- Contracted Limit: `{p_fin.get('contracted_capacity_kw', 0):,.0f} kW`")
            st.write(f"- Contract Price: `{p_fin.get('contracted_capacity_fee_per_kw_year', 0):,.2f} €/kW/Yr`")
            st.write(f"- Peak Penalty: `{p_fin.get('peak_capacity_fee_per_kw_month', 0):,.2f} €/kW/Mo`")
        with sc3:
            st.markdown("**3. Energy & Global**")
            st.write(f"- Energy (Normal): `{p_fin.get('energy_price_normal_per_kwh', 0):,.4f} €/kWh`")
            st.write(f"- Energy (Laag): `{p_fin.get('energy_price_laag_per_kwh', 0):,.4f} €/kWh`")
            st.write(f"- Inflation: `{p_fin.get('inflation', 0):.1f} %`")

# ---------------------------------------------------------
# The calculation functions remain the same as the last step
# ---------------------------------------------------------
def calculate_year1_baseline_costs(df, fin_params):
    temp_df = df.copy()
    if 'timestamp' in temp_df.columns:
        temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
        temp_df['month'] = temp_df['timestamp'].dt.month
        try:
            delta = temp_df['timestamp'].iloc[1] - temp_df['timestamp'].iloc[0]
            factor = 60 / (delta.seconds / 60)
        except:
            factor = 4.0
    else:
        res = len(temp_df) / 8760
        pts_per_month = int(730 * res)
        temp_df['month'] = (temp_df.index // pts_per_month) + 1
        temp_df['month'] = temp_df['month'].clip(upper=12)
        factor = 4.0 if len(temp_df) == 35040 else 1.0

    load_col = 'final_grid_load_kw' if 'final_grid_load_kw' in temp_df.columns else 'consumption_kw'
    
    monthly_schedule = fin_params.get('monthly_tariff_schedule', {})
    if monthly_schedule:
        peak_costs_y1 = 0.0
        energy_cost_y1 = 0.0
        fixed_costs_y1 = 0.0
        excess_costs_y1 = 0.0
        
        def is_hour_in_range(hour, start, end):
            if start == end:
                return False
            if start < end:
                return start <= hour < end
            else:
                return (hour >= start) | (hour < end)
                
        for m in range(1, 13):
            m_mask = temp_df['month'] == m
            m_df = temp_df[m_mask]
            if len(m_df) == 0:
                continue
            m_peak = m_df[load_col].max()
            
            m_data = monthly_schedule.get(str(m), {}) or monthly_schedule.get(m, {})
            if not m_data:
                m_data = monthly_schedule.get('1', {}) or monthly_schedule.get(1, {})
                
            base_fee = float(m_data.get('base_fee', 0.0) or 0.0)
            contracted_kw = float(m_data.get('contracted_capacity_kw', 0.0) or 0.0)
            contract_price = float(m_data.get('contracted_capacity_price', 0.0) or 0.0)
            peak_penalty_price = float(m_data.get('peak_penalty_price', 0.0) or 0.0)
            excess_price = float(m_data.get('excess_penalty_price', 0.0) or 0.0)
            tax_pct = float(m_data.get('tax_pct', 0.0) or 0.0)
            subsidy = float(m_data.get('subsidy_amount', 0.0) or 0.0)
            
            # Pico-Peak if TOU is enabled, else absolute peak
            enable_tou = bool(m_data.get('enable_tou', True))
            pico_peak = m_peak
            if enable_tou and 'timestamp' in m_df.columns:
                m_df_copy = m_df.copy()
                m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                pico_df = m_df_copy[alta_mask]
                if len(pico_df) > 0:
                    pico_peak = pico_df[load_col].max()
            
            m_excess = (m_peak - contracted_kw) * excess_price if m_peak > contracted_kw else 0.0
            
            # Energy cost
            alta_price = float(m_data.get('alta', {}).get('price', 0.0) or 0.0)
            alta_start = int(m_data.get('alta', {}).get('start_hour', 18))
            alta_end = int(m_data.get('alta', {}).get('end_hour', 23))
            baja_price = float(m_data.get('baja', {}).get('price', 0.0) or 0.0)
            baja_start = int(m_data.get('baja', {}).get('start_hour', 23))
            baja_end = int(m_data.get('baja', {}).get('end_hour', 5))
            resto_price = float(m_data.get('resto', {}).get('price', 0.0) or 0.0)
            
            m_energy = 0.0
            if 'timestamp' in m_df.columns:
                m_df_copy = m_df.copy()
                m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                
                alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                baja_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, baja_start, baja_end))
                resto_mask = ~(alta_mask | baja_mask)
                
                e_alta = m_df_copy[alta_mask][load_col].sum() / factor
                e_baja = m_df_copy[baja_mask][load_col].sum() / factor
                e_resto = m_df_copy[resto_mask][load_col].sum() / factor
                
                m_energy = (e_alta * alta_price) + (e_baja * baja_price) + (e_resto * resto_price)
            else:
                m_energy = (m_df[load_col].sum() / factor) * resto_price

            # Surcharges & Adjustments
            prov_taxes = m_data.get('provincial_taxes', [])
            custom_adjustments = m_data.get('custom_adjustments', [])
            
            pre_tax_adj = 0.0
            post_tax_adj = 0.0
            for adj in custom_adjustments:
                amt = float(adj.get('Amount (€)', adj.get('amount', 0.0)) or 0.0)
                is_pre = bool(adj.get('Is Pre-tax', adj.get('is_pre_tax', False)))
                if is_pre:
                    pre_tax_adj += amt
                else:
                    post_tax_adj += amt
            
            total_tax_pct = tax_pct
            for p_tax in prov_taxes:
                total_tax_pct += float(p_tax.get('Rate (%)', p_tax.get('rate', 0.0)) or 0.0)
            tax_factor = 1.0 + (total_tax_pct / 100.0)
            
            # Apply tax factors to each component
            stabilization_credit = float(m_data.get('stabilization_credit', 0.0) or 0.0)
            post_tax_adj -= stabilization_credit
            
            fixed_costs_y1 += (base_fee + (contracted_kw * contract_price) - subsidy + pre_tax_adj) * tax_factor + post_tax_adj
            peak_costs_y1 += (pico_peak * peak_penalty_price) * tax_factor
            excess_costs_y1 += m_excess * tax_factor
            energy_cost_y1 += m_energy * tax_factor
            
        return peak_costs_y1, energy_cost_y1, fixed_costs_y1, excess_costs_y1
    
    else:
        monthly_peaks = temp_df.groupby('month')[load_col].max()
        peak_costs_y1 = monthly_peaks.sum() * fin_params.get('peak_capacity_fee_per_kw_month', 0.0)
        
        if 'timestamp' in temp_df.columns:
            temp_df['is_normal'] = (temp_df['timestamp'].dt.dayofweek < 5) & (temp_df['timestamp'].dt.hour >= 7) & (temp_df['timestamp'].dt.hour < 23)
        else:
            temp_df['is_normal'] = True
            
        energy_normal = temp_df[temp_df['is_normal']][load_col].sum() / factor
        energy_laag = temp_df[~temp_df['is_normal']][load_col].sum() / factor if 'is_normal' in temp_df.columns else 0.0
        
        energy_cost_y1 = (energy_normal * fin_params.get('energy_price_normal_per_kwh', 0.0)) + \
                         (energy_laag * fin_params.get('energy_price_laag_per_kwh', 0.0))
                         
        fixed_conn_y1 = fin_params.get('fixed_annual_connection_fee', 0.0)
        fixed_trans_y1 = fin_params.get('fixed_annual_transport_fee', 0.0)
        contracted_kw = fin_params.get('contracted_capacity_kw', 0.0)
        contracted_cost_y1 = contracted_kw * fin_params.get('contracted_capacity_fee_per_kw_year', 0.0)
        
        fixed_costs_y1 = fixed_conn_y1 + fixed_trans_y1 + contracted_cost_y1
        
        excess_costs_y1 = 0.0
        contract_price_yr = fin_params.get('contracted_capacity_fee_per_kw_year', 0.0)
        contract_price_mo = contract_price_yr / 12.0
        if contracted_kw > 0 and contract_price_mo > 0:
            for m, peak in monthly_peaks.items():
                if peak > contracted_kw:
                    excess_costs_y1 += (peak - contracted_kw) * contract_price_mo
        
        return peak_costs_y1, energy_cost_y1, fixed_costs_y1, excess_costs_y1

def render_financial_projection(df: pd.DataFrame, fin_params: dict):
    if df is None or df.empty:
        return
        
    with st.expander("📈 15-Year Baseline Grid Cost Projection", expanded=True):
        if 'contracted_capacity_fee_per_kw_year' not in fin_params:
            st.warning("⚠️ Legacy pricing detected. Please click 'Save Baseline' to upgrade.")
            
        peak_costs_y1, energy_cost_y1, fixed_costs_y1, excess_costs_y1 = calculate_year1_baseline_costs(df, fin_params)
        base_grid_capex = fin_params.get('baseline_grid_capex', 0.0)
        inflation = fin_params.get('inflation', 3.0) / 100.0
        
        years = list(range(1, 16))
        e_costs, p_costs, f_costs, ex_costs = [], [], [], []
        
        for y in years:
            multiplier = (1 + inflation) ** (y - 1)
            e_costs.append(energy_cost_y1 * multiplier)
            p_costs.append(peak_costs_y1 * multiplier)
            f_costs.append(fixed_costs_y1 * multiplier) 
            ex_costs.append(excess_costs_y1 * multiplier)
            
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=f_costs, name="Fixed & Contracted Costs (€)", marker_color="#2c3e50"))
        fig.add_trace(go.Bar(x=years, y=e_costs, name="Energy Volume Cost (€)", marker_color="#3498db"))
        fig.add_trace(go.Bar(x=years, y=p_costs, name="Monthly Peak Penalties (€)", marker_color="#e74c3c"))
        fig.add_trace(go.Bar(x=years, y=ex_costs, name="Excess Capacity Penalties (€)", marker_color="#e67e22"))
        
        total_y1 = energy_cost_y1 + peak_costs_y1 + fixed_costs_y1 + excess_costs_y1
        
        fig.update_layout(barmode='stack', title=f"Base Year 1 Total Grid Costs: {total_y1:,.0f} €", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

def render_baseline_invoice_summary(df: pd.DataFrame, fin_params: dict):
    if df is None or df.empty:
        return
        
    with st.expander("🧾 Estimated Monthly Invoice Cost Breakdown", expanded=True):
        st.info("Estimated average monthly billing structure under baseline conditions, modeled after standard industrial invoices.")
        
        monthly_schedule = fin_params.get('monthly_tariff_schedule', {})
        
        if monthly_schedule:
            temp_df = df.copy()
            if 'timestamp' in temp_df.columns:
                temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'])
                temp_df['month'] = temp_df['timestamp'].dt.month
                try:
                    delta = temp_df['timestamp'].iloc[1] - temp_df['timestamp'].iloc[0]
                    factor = 60 / (delta.seconds / 60)
                except:
                    factor = 4.0
            else:
                res = len(temp_df) / 8760
                pts_per_month = int(730 * res)
                temp_df['month'] = (temp_df.index // pts_per_month) + 1
                temp_df['month'] = temp_df['month'].clip(upper=12)
                factor = 4.0 if len(temp_df) == 35040 else 1.0

            load_col = 'final_grid_load_kw' if 'final_grid_load_kw' in temp_df.columns else 'consumption_kw'
            
            def is_hour_in_range(hour, start, end):
                if start == end:
                    return False
                if start < end:
                    return start <= hour < end
                else:
                    return (hour >= start) | (hour < end)
                    
            m_fixed_list, m_cap_list, m_peak_list, m_excess_list, m_energy_list = [], [], [], [], []
            m_tax_breakdown = {}
            m_adj_breakdown = {}
            m_gross_list = []
            
            for m in range(1, 13):
                m_mask = temp_df['month'] == m
                m_df = temp_df[m_mask]
                if len(m_df) == 0:
                    continue
                m_peak = m_df[load_col].max()
                
                m_data = monthly_schedule.get(str(m), {}) or monthly_schedule.get(m, {})
                if not m_data:
                    m_data = monthly_schedule.get('1', {}) or monthly_schedule.get(1, {})
                    
                base_fee = float(m_data.get('base_fee', 0.0) or 0.0)
                contracted_kw = float(m_data.get('contracted_capacity_kw', 0.0) or 0.0)
                contract_price = float(m_data.get('contracted_capacity_price', 0.0) or 0.0)
                peak_penalty_price = float(m_data.get('peak_penalty_price', 0.0) or 0.0)
                excess_price = float(m_data.get('excess_penalty_price', 0.0) or 0.0)
                tax_pct = float(m_data.get('tax_pct', 0.0) or 0.0)
                subsidy = float(m_data.get('subsidy_amount', 0.0) or 0.0)
                
                alta_price = float(m_data.get('alta', {}).get('price', 0.0) or 0.0)
                alta_start = int(m_data.get('alta', {}).get('start_hour', 18))
                alta_end = int(m_data.get('alta', {}).get('end_hour', 23))
                baja_price = float(m_data.get('baja', {}).get('price', 0.0) or 0.0)
                baja_start = int(m_data.get('baja', {}).get('start_hour', 23))
                baja_end = int(m_data.get('baja', {}).get('end_hour', 5))
                resto_price = float(m_data.get('resto', {}).get('price', 0.0) or 0.0)
                
                m_fixed = base_fee - subsidy
                m_capacity = contracted_kw * contract_price
                
                # Pico peak
                enable_tou = bool(m_data.get('enable_tou', True))
                pico_peak = m_peak
                if enable_tou and 'timestamp' in m_df.columns:
                    m_df_copy = m_df.copy()
                    m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                    alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                    pico_df = m_df_copy[alta_mask]
                    if len(pico_df) > 0:
                        pico_peak = pico_df[load_col].max()
                        
                m_peak_penalty = pico_peak * peak_penalty_price
                m_excess = (m_peak - contracted_kw) * excess_price if m_peak > contracted_kw else 0.0
                
                m_energy = 0.0
                if 'timestamp' in m_df.columns:
                    m_df_copy = m_df.copy()
                    m_df_copy['hour'] = m_df_copy['timestamp'].dt.hour
                    alta_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, alta_start, alta_end))
                    baja_mask = m_df_copy['hour'].apply(lambda h: is_hour_in_range(h, baja_start, baja_end))
                    resto_mask = ~(alta_mask | baja_mask)
                    e_alta = m_df_copy[alta_mask][load_col].sum() / factor
                    e_baja = m_df_copy[baja_mask][load_col].sum() / factor
                    e_resto = m_df_copy[resto_mask][load_col].sum() / factor
                    m_energy = (e_alta * alta_price) + (e_baja * baja_price) + (e_resto * resto_price)
                else:
                    m_energy = (m_df[load_col].sum() / factor) * resto_price
                    
                net_m = m_fixed + m_capacity + m_peak_penalty + m_excess + m_energy
                
                # Accumulate net components
                m_fixed_list.append(m_fixed)
                m_cap_list.append(m_capacity)
                m_peak_list.append(m_peak_penalty)
                m_excess_list.append(m_excess)
                m_energy_list.append(m_energy)
                
                # Surcharges & Adjustments
                prov_taxes = m_data.get('provincial_taxes', [])
                custom_adjustments = m_data.get('custom_adjustments', [])
                
                pre_tax_adj = 0.0
                post_tax_adj = 0.0
                for adj in custom_adjustments:
                    name = adj.get('Charge Name', adj.get('name', 'Adjustment'))
                    amt = float(adj.get('Amount (€)', adj.get('amount', 0.0)) or 0.0)
                    is_pre = bool(adj.get('Is Pre-tax', adj.get('is_pre_tax', False)))
                    if is_pre:
                        pre_tax_adj += amt
                    else:
                        post_tax_adj += amt
                    
                    if name not in m_adj_breakdown:
                        m_adj_breakdown[name] = []
                    m_adj_breakdown[name].append(amt)
                
                net_with_pre_tax = net_m + pre_tax_adj
                
                # National VAT
                vat_val = net_with_pre_tax * (tax_pct / 100.0)
                if "National VAT" not in m_tax_breakdown:
                    m_tax_breakdown["National VAT"] = []
                m_tax_breakdown["National VAT"].append(vat_val)
                
                total_tax_m = vat_val
                
                # Provincial taxes
                for p_tax in prov_taxes:
                    name = p_tax.get('Tax Name', p_tax.get('name', 'Provincial Tax'))
                    rate = float(p_tax.get('Rate (%)', p_tax.get('rate', 0.0)) or 0.0)
                    tax_val = net_with_pre_tax * (rate / 100.0)
                    if name not in m_tax_breakdown:
                        m_tax_breakdown[name] = []
                    m_tax_breakdown[name].append(tax_val)
                    total_tax_m += tax_val
                    
                gross_m = net_with_pre_tax + total_tax_m + post_tax_adj
                
                # Legacy stabilization credit fallback
                stabilization_credit = float(m_data.get('stabilization_credit', 0.0) or 0.0)
                gross_m = max(0.0, gross_m - stabilization_credit)
                m_gross_list.append(gross_m)
                
            monthly_fixed = sum(m_fixed_list) / len(m_fixed_list)
            monthly_capacity = sum(m_cap_list) / len(m_cap_list)
            monthly_peak_penalty = sum(m_peak_list) / len(m_peak_list)
            monthly_excess_penalty = sum(m_excess_list) / len(m_excess_list)
            monthly_energy = sum(m_energy_list) / len(m_energy_list)
            
            net_subtotal = monthly_fixed + monthly_capacity + monthly_peak_penalty + monthly_energy + monthly_excess_penalty
            gross_total = sum(m_gross_list) / len(m_gross_list)
            
            # Average breakdowns
            avg_taxes = {}
            for name, val_list in m_tax_breakdown.items():
                avg_taxes[name] = sum(val_list) / len(val_list)
                
            avg_adjs = {}
            for name, val_list in m_adj_breakdown.items():
                avg_adjs[name] = sum(val_list) / len(val_list)
                
            jan_data = monthly_schedule.get('1', {}) or monthly_schedule.get(1, {})
            contracted_kw = float(jan_data.get('contracted_capacity_kw', 430.0))
            
            st.markdown("#### 1. Net Electrical Charges (12-Month Average)")
            col_net1, col_net2 = st.columns(2)
            with col_net1:
                st.write(f"• Fixed Connection Fee (Averaged): `€ {monthly_fixed:,.2f} / Mo`")
                st.write(f"• Grid Capacity Charge (~{contracted_kw:.1f} kW): `€ {monthly_capacity:,.2f} / Mo`")
            with col_net2:
                st.write(f"• Peak Load Penalty (Averaged): `€ {monthly_peak_penalty:,.2f} / Mo`")
                st.write(f"• Excess Capacity Penalty (Averaged): `€ {monthly_excess_penalty:,.2f} / Mo`")
                st.write(f"• Active Energy Volume Cost (Averaged): `€ {monthly_energy:,.2f} / Mo`")
                
            st.markdown(f"**Net Electrical Subtotal: `€ {net_subtotal:,.2f} / Mo`**")
            st.divider()
            
            st.markdown("#### 2. Taxes, Duties & Adjustments (12-Month Average)")
            # Render taxes breakdown
            tax_sum_avg = 0.0
            for name, val in avg_taxes.items():
                st.write(f"• {name}: `€ {val:,.2f} / Mo`")
                tax_sum_avg += val
                
            # Render adjustments breakdown
            adj_sum_avg = 0.0
            for name, val in avg_adjs.items():
                sign = "-" if val < 0 else "+"
                st.write(f"• {name}: `{sign} € {abs(val):,.2f} / Mo`")
                adj_sum_avg += val
                
            # Legacy stabilization credit
            legacy_credit = float(jan_data.get('stabilization_credit', 0.0) or 0.0)
            if legacy_credit > 0:
                st.write(f"• Grid Stabilization Credit (Legacy): `- € {legacy_credit:,.2f} / Mo`")
                adj_sum_avg -= legacy_credit
                
            st.markdown(f"**Total Surcharges & Adjustments: `€ {tax_sum_avg + adj_sum_avg:,.2f} / Mo`**")
            st.divider()
            
            st.metric(label="Estimated Average Monthly Bill (Gross)", value=f"€ {gross_total:,.2f} / Mo", help="Average of net electrical charges plus national/local taxes and custom adjustments.")
            return
        
        # Calculate annual values
        peak_costs_y1, energy_cost_y1, fixed_costs_y1, excess_costs_y1 = calculate_year1_baseline_costs(df, fin_params)
        
        # Unpack params
        fixed_conn = float(fin_params.get('fixed_annual_connection_fee', 0.0) or 0.0)
        fixed_trans = float(fin_params.get('fixed_annual_transport_fee', 0.0) or 0.0)
        contracted_kw = float(fin_params.get('contracted_capacity_kw', 0.0) or 0.0)
        contract_price = float(fin_params.get('contracted_capacity_fee_per_kw_year', 0.0) or 0.0)
        
        # Scale to monthly values
        monthly_fixed = (fixed_conn + fixed_trans) / 12.0
        monthly_capacity = (contracted_kw * contract_price) / 12.0
        monthly_peak_penalty = peak_costs_y1 / 12.0
        monthly_energy = energy_cost_y1 / 12.0
        monthly_excess_penalty = excess_costs_y1 / 12.0
        
        net_subtotal = monthly_fixed + monthly_capacity + monthly_peak_penalty + monthly_energy + monthly_excess_penalty
        
        vat_pct = float(fin_params.get('national_vat_pct', 0.0) or 0.0) / 100.0
        local_pct = float(fin_params.get('local_tax_pct', 0.0) or 0.0) / 100.0
        
        vat_tax = net_subtotal * vat_pct
        local_tax = net_subtotal * local_pct
        gross_total = net_subtotal + vat_tax + local_tax
        
        # Display as columns and metrics
        st.markdown("#### 1. Net Electrical Charges")
        col_net1, col_net2 = st.columns(2)
        with col_net1:
            st.write(f"• Fixed Commercialization & Transport Fee: `€ {monthly_fixed:,.2f} / Mo`")
            st.write(f"• Grid Capacity Charge ({contracted_kw:.1f} kW contracted): `€ {monthly_capacity:,.2f} / Mo`")
        with col_net2:
            st.write(f"• Peak Load Penalty (Peak Demand): `€ {monthly_peak_penalty:,.2f} / Mo`")
            st.write(f"• Excess Capacity Penalty: `€ {monthly_excess_penalty:,.2f} / Mo`")
            st.write(f"• Active Energy Volume Cost: `€ {monthly_energy:,.2f} / Mo`")
            
        st.markdown(f"**Net Electrical Subtotal: `€ {net_subtotal:,.2f} / Mo`**")
        st.divider()
        
        st.markdown("#### 2. Taxes & Duties (Estimated)")
        col_tax1, col_tax2 = st.columns(2)
        with col_tax1:
            st.write(f"• National VAT ({vat_pct * 100:.1f}%): `€ {vat_tax:,.2f} / Mo`")
        with col_tax2:
            st.write(f"• Provincial & Municipal Taxes ({local_pct * 100:.1f}%): `€ {local_tax:,.2f} / Mo`")
            
        st.markdown(f"**Total Taxes Subtotal: `€ {vat_tax + local_tax:,.2f} / Mo`**")
        st.divider()
        
        # Large highlighted metric for gross invoice total
        st.metric(label="Estimated Average Monthly Bill (Gross)", value=f"€ {gross_total:,.2f} / Mo", help="Sum of net electrical charges plus national and local taxes.")