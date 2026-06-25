# tabs/tab3_components/financial_engine.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from classes.models import BaseScenario, SubScenario

def render_financial_dashboard(selected_profiles: list, selected_base: str, vault: dict):
    """
    Dynamically calculates and visualizes the 15-year cashflow, ROI, and Net Present Value (NPV)
    for all selected hardware sub-scenarios against the baseline.
    Generates detailed year-by-year cashflow series and auto-saves them back into the vault.
    """
    st.write("### 💶 Executive Financial Dashboard (DCF & ROI Analysis)")
    
    col_info, col_wacc = st.columns([2, 1])
    with col_info:
        st.info("Discounted Cash Flow (DCF) projection over 15 years including CAPEX, OPEX, grid tariffs, fuel costs, and compounding energy inflation.")
    with col_wacc:
        discount_rate = st.number_input(
            "Discount Rate / WACC (%)", 
            value=5.0, step=0.5, 
            help="Used to discount future cashflows to calculate the Net Present Value (NPV)."
        ) / 100.0
    
    # 1. Extract Baseline Financial DNA
    base_data = vault[selected_base]
    base_df = base_data['df']
    base_fin = base_data.get('params', {}).get('financial_metadata', {})
    
    e_price = base_fin.get('energy_charge', 0.25)
    p_price = base_fin.get('demand_charge', 120.0)
    base_grid_capex = base_fin.get('baseline_grid_capex', 0.0) 
    fit = base_fin.get('feed_in_tariff', 0.08)
    inflation = base_fin.get('inflation', 3.0) / 100.0
    diesel_price = base_fin.get('diesel_price', 1.50) # NEW: Unpack fuel price
    
    res = base_data.get('params', {}).get('resolution', 15)
    factor = 60 / res
    
    # 2. Calculate Baseline BAU (Business As Usual) Costs
    base_kwh = base_df['consumption_kw'].sum() / factor
    base_peak = base_df['consumption_kw'].max()
    base_grid_bill_yr1 = (base_kwh * e_price) + (base_peak * p_price)
    
    fig = go.Figure()
    fig.add_hline(y=0, line_color="white", line_width=1)
    
    summary_data = []
    detailed_tables = {}
    
    # 3. Calculate Advanced Cashflow Series for every Variant
    for name in selected_profiles:
        if name == selected_base:
            continue # Baseline itself has no comparative ROI
            
        scen = vault[name]
        sub_df = scen['df']
        hw_params = scen.get('params', {}).get('hardware_params', {})
        
        # Safely extract CAPEX/OPEX depending on Isolated vs. Combined mode
        capex = hw_params.get('total_capex', 0)
        opex_pct = hw_params.get('opex_pct', 0) / 100.0
        degradation_pct = hw_params.get('degradation_pct', 0) / 100.0
        opex_yr1 = capex * opex_pct
        
        # NEU: Variablen für den Batterietausch vorbereiten
        rep_year = 99 # Default: Findet nicht statt
        rep_base_cost = 0.0
        
        if capex > 0: # Isoliertes Szenario
            if 'replacement_year' in hw_params: # Es ist eine Batterie
                rep_year = hw_params.get('replacement_year', 10)
                rep_pct = hw_params.get('replacement_pct', 100.0) / 100.0
                rep_base_cost = hw_params.get('total_storage_capex', 0) * rep_pct
                
        elif capex == 0: # Combined Cascade Szenario (Hardware steckt in Unter-Ordnern)
            c1 = hw_params.get('solar', {}).get('total_capex', 0)
            c2 = hw_params.get('battery', {}).get('total_capex', 0)
            o1 = c1 * (hw_params.get('solar', {}).get('opex_pct', 0) / 100.0)
            o2 = c2 * (hw_params.get('battery', {}).get('opex_pct', 0) / 100.0)
            d1 = hw_params.get('solar', {}).get('degradation_pct', 0) / 100.0
            d2 = hw_params.get('battery', {}).get('degradation_pct', 0) / 100.0
            
            capex = c1 + c2
            opex_yr1 = o1 + o2
            
            # Weighted average degradation based on CAPEX split
            if capex > 0:
                degradation_pct = ((c1 * d1) + (c2 * d2)) / capex
            else:
                degradation_pct = 0.0
                
            # Batterietausch aus dem Combined-Objekt extrahieren
            bat_params = hw_params.get('battery', {})
            rep_year = bat_params.get('replacement_year', 99)
            rep_pct = bat_params.get('replacement_pct', 100.0) / 100.0
            rep_base_cost = bat_params.get('total_storage_capex', 0) * rep_pct
            
        if capex == 0:
            continue # Skip non-hardware scenarios
            
        # Variant Operational Costs (Grid interaction only)
        sub_kwh = sub_df['final_grid_load_kw'].clip(lower=0.0).sum() / factor
        sub_peak = sub_df['final_grid_load_kw'].max()
        sub_export = sub_df.get('grid_feed_in_kw', pd.Series([0])).sum() / factor
        
        sub_grid_bill_yr1 = (sub_kwh * e_price) + (sub_peak * p_price) - (sub_export * fit)
        grid_savings_yr1 = base_grid_bill_yr1 - sub_grid_bill_yr1
        
        # GENERATOR FUEL COSTS
        annual_fuel_l = sub_df.get('generator_fuel_l', pd.Series([0])).sum()
        fuel_cost_yr1 = annual_fuel_l * diesel_price
        
        # --- 15-YEAR CASHFLOW CASCADING MATHEMATICS ---
        cf_table = []
        
        # Net Year 0 cashflow accounts for avoided grid upgrade costs minus new hardware investments
        net_year0 = base_grid_capex - capex
        cum_cf = net_year0
        cum_npv = net_year0
        
        # Year 0: Initial Investment / Avoided Baseline Cost
        cf_table.append({
            "Year": 0, 
            "CAPEX (€)": round(-capex, 2), 
            "OPEX (€)": 0, 
            "Fuel Cost (€)": 0,
            "Grid Savings (€)": round(base_grid_capex, 2),
            "Net Cashflow (€)": round(net_year0, 2), 
            "Cumulative Cashflow (€)": round(cum_cf, 2), 
            "Present Value (PV)": round(net_year0, 2), 
            "Cumulative NPV (€)": round(cum_npv, 2)
        })
        
        break_even_yr = 0 if cum_cf >= 0 else "> 15"
        
        # Years 1 to 15: Operations & Compounding
        for y in range(1, 16):
            infl_multiplier = (1 + inflation) ** (y - 1)
            deg_multiplier = (1 - degradation_pct) ** (y - 1)
            
            sav_y = grid_savings_yr1 * infl_multiplier * deg_multiplier
            opx_y = opex_yr1 * infl_multiplier
            fuel_y = fuel_cost_yr1 * infl_multiplier
            
            # NEU: Prüfen, ob in diesem Jahr der Batterietausch fällig ist
            rep_y = 0.0
            if y == rep_year:
                # Ersatzteile unterliegen auch der normalen wirtschaftlichen Inflation
                rep_y = rep_base_cost * infl_multiplier 

            net_y = sav_y - opx_y - fuel_y - rep_y
            cum_cf += net_y
            
            # Discounting for Net Present Value (NPV)
            pv_y = net_y / ((1 + discount_rate) ** y)
            cum_npv += pv_y
            
            cf_table.append({
                "Year": y, 
                "CAPEX (€)": round(-rep_y, 2), # Wenn rep_y > 0, taucht es hier sauber auf!
                "OPEX (€)": round(-opx_y, 2), 
                "Fuel Cost (€)": round(-fuel_y, 2),
                "Grid Savings (€)": round(sav_y, 2), 
                "Net Cashflow (€)": round(net_y, 2), 
                "Cumulative Cashflow (€)": round(cum_cf, 2), 
                "Present Value (PV)": round(pv_y, 2), 
                "Cumulative NPV (€)": round(cum_npv, 2)
            })
            
            if break_even_yr == "> 15" and cum_cf >= 0:
                break_even_yr = y
                
        # --- SAVE FINANCIALS DIRECTLY INTO THE ACTIVE VAULT ---
        vault[name]['financial_metrics'] = {
            "discount_rate_used": discount_rate,
            "roi_years": break_even_yr,
            "net_present_value": cum_npv,
            "total_15y_profit": cum_cf,
            "cashflow_series": cf_table
        }
        
        # Add Line to Waterfall Chart
        plot_y = [row["Cumulative Cashflow (€)"] for row in cf_table]
        fig.add_trace(go.Scatter(
            x=list(range(16)), y=plot_y, mode='lines+markers', name=name,
            hovertemplate="Year %{x}<br>Cashflow: %{y:,.0f} €"
        ))
        
        # Add to Summary Dashboard
        summary_data.append({
            "Variant Scenario": name,
            "Total CAPEX": f"- {capex:,.0f} €",
            "Year 1 Net Savings": f"+ {grid_savings_yr1 - opex_yr1 - fuel_cost_yr1:,.0f} €",
            "Fuel Penalty (Y1)": f"- {fuel_cost_yr1:,.0f} €" if fuel_cost_yr1 > 0 else "0 €",
            "Break-Even (ROI)": f"{break_even_yr} Years" if isinstance(break_even_yr, str) or break_even_yr > 0 else "Instant (Day 1)",
            "15Y Cum. Cashflow": f"{cum_cf:,.0f} €",
            "15Y Net Present Value (NPV)": f"{cum_npv:,.0f} €"
        })
        
        detailed_tables[name] = cf_table
        
    # --- RENDER OUTPUTS ---
    if summary_data:
        fig.update_layout(
            height=400, margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Operating Year", yaxis_title="Cumulative Net Cashflow (€)",
            hovermode="x unified", legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("#### 🏆 Financial Performance Summary")
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.divider()
        st.write("#### 📊 Detailed 15-Year Cashflow Series")
        st.info("Analyze the exact yearly progression of grid savings, maintenance costs, fuel burn penalties, and discounted values.")
        
        variant_names = list(detailed_tables.keys())
        ui_tabs = st.tabs([f"🌿 {n}" for n in variant_names])
        
        for idx, t_name in enumerate(variant_names):
            with ui_tabs[idx]:
                df_cf = pd.DataFrame(detailed_tables[t_name])
                st.dataframe(
                    df_cf.style.format({col: "{:,.0f} €" for col in df_cf.columns if "€" in col or "PV" in col}),
                    use_container_width=True, hide_index=True
                )
    else:
        st.warning("Please select at least one hardware variant (with CAPEX configured) to view the financial ROI analysis.")


def generate_15_year_cashflow(sub_scenario: SubScenario, base_scenario: BaseScenario) -> pd.DataFrame:
    """
    Das Herzstück der Finanzsimulation. 
    Nimmt ein SubSzenario und berechnet die jährlichen Kosten/Gewinne.
    Gibt 'None' zurück, wenn der User keine Finanzen aktiviert hat!
    """
    
    # ==========================================
    # 1. DER SICHERHEITSSCHALTER
    # ==========================================
    # Wenn der User in Tab 2 den Finanz-Schalter auf "OFF" gelassen hat,
    # ist dieses Feld 'None'. Wir brechen sofort sicher ab.
    if not sub_scenario.financials:
        return None 
        
    fin = sub_scenario.financials
    lifespan = fin.lifespan_years
    
    # Wir bereiten eine Tabelle vor (Jahr 0 bis Jahr 15)
    jahre = list(range(lifespan + 1))
    df = pd.DataFrame({"Jahr": jahre})
    
    # ==========================================
    # 2. CAPEX (Hardware-Kauf im Jahr 0)
    # ==========================================
    df["Investition_Capex"] = 0.0
    df.loc[df["Jahr"] == 0, "Investition_Capex"] = -fin.capex
    
    # ==========================================
    # 3. OPEX (Laufende Wartung ab Jahr 1)
    # ==========================================
    # Die Wartung steigt jedes Jahr um die allgemeine Inflationsrate
    opex_liste = [0.0] # Jahr 0 hat keine Wartung
    for jahr in range(1, lifespan + 1):
        # OPEX = Basiswert * (1 + Inflation)^Jahr
        laufende_kosten = fin.opex_yearly * ((1 + fin.inflation_rate) ** jahr)
        opex_liste.append(-laufende_kosten)
        
    df["Wartung_Opex"] = opex_liste
    
    # ==========================================
    # 4. DIE NETZKOSTEN & ERSPARNISSE (Platzhalter für Tarif-Logik)
    # ==========================================
    # HIER kommt später die Verknüpfung zu deiner tarrif_calc.py rein.
    # Für den Anfang tun wir so, als ob das System jedes Jahr fiktiv 
    # 25.000 € an Strafen einspart (wachsend mit der Energiepreissteigerung).
    
    ersparnis_liste = [0.0]
    basis_ersparnis_pro_jahr = 25000.0 # TODO: Durch echte Tarif-Ersparnis ersetzen
    
    for jahr in range(1, lifespan + 1):
        ersparnis = basis_ersparnis_pro_jahr * ((1 + fin.energy_price_growth) ** jahr)
        ersparnis_liste.append(ersparnis)
        
    df["Eingesparte_Netzkosten"] = ersparnis_liste
    
    # ==========================================
    # 5. CASHFLOW & AMORTISATION BERECHNEN
    # ==========================================
    # Was bleibt am Ende des Jahres auf dem Konto?
    df["Netto_Cashflow"] = df["Investition_Capex"] + df["Wartung_Opex"] + df["Eingesparte_Netzkosten"]
    
    # Der Kontostand über die Jahre (Kumuliert)
    # Hieran sehen wir später, ab wann die Linie über Null geht (Break-Even!)
    df["Kumulierter_Cashflow"] = df["Netto_Cashflow"].cumsum()
    
    return df

def get_payback_year(cashflow_df: pd.DataFrame) -> float:
    """Sucht das Jahr, in dem der kumulierte Cashflow positiv wird (Break-Even)."""
    if cashflow_df is None:
        return None
        
    gewinn_jahre = cashflow_df[cashflow_df["Kumulierter_Cashflow"] > 0]
    
    if gewinn_jahre.empty:
        return -1.0 # Bedeutet: System amortisiert sich innerhalb von 15 Jahren NIE!
        
    return gewinn_jahre["Jahr"].iloc[0] # Gibt das erste Jahr im Plus zurück