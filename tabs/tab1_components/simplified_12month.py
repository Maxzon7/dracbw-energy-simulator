# tabs/tab1_components/simplified_12month.py
import streamlit as st
import pandas as pd
import numpy as np

def render_simplified_12month_ui(active_scenario: str) -> dict:
    st.write("### 📊 12-Month Consumption & Peak Input")
    st.info("Input the monthly electricity consumption (kWh) and recorded peak load (kW) to generate a representative annual load profile.")
    
    st.markdown("#### 📅 Month 1: January (Template)")
    c1, c2 = st.columns(2)
    jan_cons = c1.number_input("January Consumption (kWh)", min_value=1, value=163599, step=1000, key=f"simp_cons_1_{active_scenario}")
    jan_peak = c2.number_input("January Peak Load (kW)", min_value=1.0, value=691.0, step=10.0, key=f"simp_peak_1_{active_scenario}")
    
    copy_to_all = st.checkbox("Copy January values to all months", value=True, key=f"simp_copy_all_{active_scenario}")
    
    monthly_data = {
        1: {"consumption_kwh": jan_cons, "peak_kw": jan_peak}
    }
    
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    if not copy_to_all:
        st.write("---")
        st.markdown("#### 📅 Edit Months 2 - 12")
        
        # Prefilled with January values as placeholders/defaults
        for m in range(2, 13):
            m_name = months[m-1]
            st.markdown(f"**{m_name}**")
            col_a, col_b = st.columns(2)
            m_cons = col_a.number_input(f"{m_name} Consumption (kWh)", min_value=1, value=jan_cons, step=1000, key=f"simp_cons_{m}_{active_scenario}")
            m_peak = col_b.number_input(f"{m_name} Peak Load (kW)", min_value=1.0, value=jan_peak, step=10.0, key=f"simp_peak_{m}_{active_scenario}")
            monthly_data[m] = {"consumption_kwh": m_cons, "peak_kw": m_peak}
    else:
        for m in range(2, 13):
            monthly_data[m] = {"consumption_kwh": jan_cons, "peak_kw": jan_peak}
            
    return {"monthly_data": monthly_data}

def generate_12month_simplified_profile(monthly_data: dict, year: int = 2026) -> pd.DataFrame:
    """
    Generates a full year (8760 hourly) load profile.
    For each month, it distributes the monthly energy (kWh) such that:
      - The monthly peak load matches peak_kw exactly.
      - The monthly total energy consumption matches consumption_kwh exactly.
    """
    start_date = f'{year}-01-01'
    end_date = f'{year}-12-31'
    
    timestamps = pd.date_range(start=start_date, end=f'{end_date} 23:00:00', freq='h')
    df = pd.DataFrame({'timestamp': timestamps})
    df['month'] = df['timestamp'].dt.month
    
    consumption_profile = np.zeros(len(df))
    
    for m in range(1, 13):
        month_mask = df['month'] == m
        m_indices = df[month_mask].index.tolist()
        N_m = len(m_indices)
        
        m_params = monthly_data.get(m, monthly_data[1])
        E_m = float(m_params["consumption_kwh"])
        P_m = float(m_params["peak_kw"])
        
        L_mean = E_m / N_m
        
        if P_m <= L_mean:
            consumption_profile[m_indices] = L_mean
        else:
            days_in_month = pd.Series(df.loc[m_indices, 'timestamp']).dt.day.max()
            K = int(days_in_month)
            
            while K * P_m >= E_m and K > 1:
                K -= 1
                
            if K * P_m >= E_m:
                consumption_profile[m_indices] = L_mean
                continue
                
            L_rest = (E_m - (K * P_m)) / (N_m - K)
            m_load = np.full(N_m, L_rest)
            
            m_timestamps = df.loc[m_indices, 'timestamp']
            peak_indices_in_month = np.where(m_timestamps.dt.hour == 12)[0]
            peak_indices_in_month = peak_indices_in_month[:K]
            
            m_load[peak_indices_in_month] = P_m
            consumption_profile[m_indices] = m_load
            
    df['consumption_kw'] = consumption_profile
    df = df.drop(columns=['month'])
    return df
