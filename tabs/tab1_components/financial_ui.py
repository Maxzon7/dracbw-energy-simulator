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

def render_preset_selector():
    """
    Renders the Preset Dropdown OUTSIDE the form to trigger autofill.
    """
    presets = load_tariff_presets()
    options = ["🛠️ Manual Custom Tariff"]
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
                        "contracted_capacity_kw": data.get("max_connection_capacity_kw", 100.0)
                    }
                    
    sel = st.selectbox("⚡ Load Grid Operator Tariffs (Autofill)", options, help="Wähle einen Anbieter, um die Felder unten automatisch auszufüllen.")
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

def render_financial_inputs(working_fin: dict, include_financials: bool = True, contract_mode: str = "Real Contract Preset") -> dict:
    """
    Renders the manual input fields INSIDE the form.
    Receives 'working_fin' which contains either the loaded preset or the saved vault data.
    """
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
        "tariff_mode": working_fin.get('tariff_mode', "🛠️ Manual Custom Tariff"),
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
        temp_df['is_normal'] = (temp_df['timestamp'].dt.dayofweek < 5) & (temp_df['timestamp'].dt.hour >= 7) & (temp_df['timestamp'].dt.hour < 23)
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
        temp_df['is_normal'] = True 
        factor = 4.0 if len(temp_df) == 35040 else 1.0

    monthly_peaks = temp_df.groupby('month')['consumption_kw'].max()
    peak_costs_y1 = monthly_peaks.sum() * fin_params.get('peak_capacity_fee_per_kw_month', 0.0)
    
    energy_normal = temp_df[temp_df['is_normal']]['consumption_kw'].sum() / factor
    energy_laag = temp_df[~temp_df['is_normal']]['consumption_kw'].sum() / factor if 'is_normal' in temp_df.columns else 0
    
    energy_cost_y1 = (energy_normal * fin_params.get('energy_price_normal_per_kwh', 0.0)) + \
                     (energy_laag * fin_params.get('energy_price_laag_per_kwh', 0.0))
                     
    fixed_conn_y1 = fin_params.get('fixed_annual_connection_fee', 0.0)
    fixed_trans_y1 = fin_params.get('fixed_annual_transport_fee', 0.0)
    contracted_kw = fin_params.get('contracted_capacity_kw', 0.0)
    contracted_cost_y1 = contracted_kw * fin_params.get('contracted_capacity_fee_per_kw_year', 0.0)
    
    fixed_costs_y1 = fixed_conn_y1 + fixed_trans_y1 + contracted_cost_y1
    
    return peak_costs_y1, energy_cost_y1, fixed_costs_y1

def render_financial_projection(df: pd.DataFrame, fin_params: dict):
    if df is None or df.empty:
        return
        
    with st.expander("📈 15-Year Baseline Grid Cost Projection", expanded=True):
        if 'contracted_capacity_fee_per_kw_year' not in fin_params:
            st.warning("⚠️ Legacy pricing detected. Please click 'Save Baseline' to upgrade.")
            
        peak_costs_y1, energy_cost_y1, fixed_costs_y1 = calculate_year1_baseline_costs(df, fin_params)
        base_grid_capex = fin_params.get('baseline_grid_capex', 0.0)
        inflation = fin_params.get('inflation', 3.0) / 100.0
        
        years = list(range(1, 16))
        e_costs, p_costs, f_costs = [], [], []
        
        for y in years:
            multiplier = (1 + inflation) ** (y - 1)
            e_costs.append(energy_cost_y1 * multiplier)
            p_costs.append(peak_costs_y1 * multiplier)
            f_costs.append(fixed_costs_y1 * multiplier) 
            
        fig = go.Figure()
        fig.add_trace(go.Bar(x=years, y=f_costs, name="Fixed & Contracted Costs (€)", marker_color="#2c3e50"))
        fig.add_trace(go.Bar(x=years, y=e_costs, name="Energy Volume Cost (€)", marker_color="#3498db"))
        fig.add_trace(go.Bar(x=years, y=p_costs, name="Monthly Peak Penalties (€)", marker_color="#e74c3c"))
        
        total_y1 = energy_cost_y1 + peak_costs_y1 + fixed_costs_y1
        
        fig.update_layout(barmode='stack', title=f"Base Year 1 Total Grid Costs: {total_y1:,.0f} €", height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)