import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from logic.energy_logic import load_and_clean_csv, process_consumption_data, simulate_battery_logic, get_exact_minimum_requirements
from config.translations import LANGUAGES, CONTENT

def main():
    st.set_page_config(page_title="Pro Energy Simulator", layout="wide")

   
   # --- TRANSLATION SYSTEM ---
    # Fetch the language options from the imported dictionary
    sel_lang = st.sidebar.selectbox("Language Selection", list(LANGUAGES.keys()), index=0)
    lang = LANGUAGES[sel_lang]
    
    # Secure fallback to English in case a missing key is requested
    t = CONTENT.get(lang, CONTENT["en"])
    
    st.title(t["title"])
    st.error(t["warning"])
    
    with st.expander(t["info_title"]):
        st.write(t["info_text"])

    # --- SIDEBAR CONTROLS ---
    st.sidebar.header(t["header_data"])
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=['csv'])
    
    if uploaded_file:
        # Generate default report name based on the uploaded file
        default_name = uploaded_file.name.rsplit('.', 1)[0]
        report_name = st.sidebar.text_input("Report Title", value=f"Report_{default_name}")
    
    st.sidebar.header(t["header_grid"])
    grid_limit = st.sidebar.number_input(t["grid_limit"], value=50.0, step=5.0)
    res = st.sidebar.selectbox(t["resolution"], [1, 5, 15, 60], index=2)
    
    st.sidebar.header(t["header_battery"])
    show_battery = st.sidebar.toggle(t["enable_bat"], value=True)
    b_cap = st.sidebar.slider(t["bat_cap"], 0, 500, 100, disabled=not show_battery)
    b_pwr = st.sidebar.slider(t["bat_pwr"], 0, 200, 50, disabled=not show_battery)
    
    st.sidebar.header(t["header_colors"])
    col_raw = st.sidebar.color_picker("Raw Load Color", "#A9A9A9")
    col_opt = st.sidebar.color_picker("Optimized Load Color", "#00CC96")
    col_soc = st.sidebar.color_picker("SoC Color", "#636EFA")
    col_act = st.sidebar.color_picker("Battery Action Color", "#FFA15A")

    if uploaded_file:
        try:
            # 1. Use our new smart loader to handle the CSV mess
            raw_df = load_and_clean_csv(uploaded_file)
            
            # 2. Process the cleaned dataframe
            data = process_consumption_data(raw_df, res)
            
            min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
            selected_dates = st.sidebar.date_input(t["analysis_period"], [min_date, max_date])
            
            if len(selected_dates) == 2:
                filtered = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                (data['timestamp'].dt.date <= selected_dates[1])]
                
                min_reqs = get_exact_minimum_requirements(filtered, grid_limit, res)
                
                st.subheader(t["metrics_title"])
                m1, m2, m3 = st.columns(3)
                
                m1.metric(t["metric_peak"], f"{filtered['consumption_kw'].max():.1f} kW")
                m2.metric(t["metric_min_pwr"], f"{min_reqs['min_power_kw']:.1f} kW")
                m3.metric(t["metric_min_cap"], f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")

                # Define fig_soc early so it exists even if battery is disabled
                fig_soc = None 

                if show_battery:
                    results = simulate_battery_logic(filtered, grid_limit, b_cap, b_pwr, res)
                    
                    st.subheader(t["chart_load"])
                    fig_load = go.Figure()
                    fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                             name="Raw", line=dict(color=col_raw, width=1)))
                    fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                             name="Optimized", line=dict(color=col_opt, width=2)))
                    fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red")
                    fig_load.update_layout(height=350, yaxis_title="kW", margin=dict(t=10, b=10))
                    st.plotly_chart(fig_load, use_container_width=True)

                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.subheader(t["chart_act"])
                        fig_act = go.Figure()
                        fig_act.add_trace(go.Bar(x=results['timestamp'], y=results['battery_action_kw'], marker_color=col_act))
                        fig_act.update_layout(height=250, yaxis_title="kW", margin=dict(t=10, b=10))
                        st.plotly_chart(fig_act, use_container_width=True)
                        
                    with c_right:
                        st.subheader(t["chart_soc"])
                        fig_soc = go.Figure()
                        fig_soc.add_trace(go.Scatter(x=results['timestamp'], y=results['battery_soc_kwh'], 
                                                     fill='tozeroy', line=dict(color=col_soc)))
                        fig_soc.update_layout(height=250, yaxis_title="kWh", margin=dict(t=10, b=10))
                        st.plotly_chart(fig_soc, use_container_width=True)
                else:
                    st.warning(t["no_bat_warn"])
                    fig_load = go.Figure()
                    fig_load.add_trace(go.Scatter(x=filtered['timestamp'], y=filtered['consumption_kw'], line=dict(color=col_raw)))
                    fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red")
                    st.plotly_chart(fig_load, use_container_width=True)

                # --- EXPORT SECTION ---
                st.divider()
                st.subheader("Export Results")
    
                pdf_metrics = {
                    "grid_limit": grid_limit,
                    "peak_raw": filtered['consumption_kw'].max(),
                    "min_pwr": min_reqs['min_power_kw'],
                    "min_cap": min_reqs['true_min_capacity_kwh']
                }

                if st.button(t.get("pdf_button", "Generate PDF Report")): 
                    with st.spinner("Creating PDF..."):
                        try:
                            from functions.pdf_converter import generate_tech_pdf
                            
                            # Determine which data to send based on battery toggle
                            export_data = results if show_battery else filtered
                            
                            pdf_data = generate_tech_pdf(
                                report_title=report_name, 
                                metrics=pdf_metrics, 
                                plot_data=export_data, 
                                battery_enabled=show_battery
                            )
                            
                            st.download_button(
                                label=t.get("pdf_download", "Download Technical PDF"), 
                                data=pdf_data,
                                file_name=f"{report_name}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as pdf_error:
                            st.error(f"Error during PDF generation: {pdf_error}")

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == "__main__":
    main()