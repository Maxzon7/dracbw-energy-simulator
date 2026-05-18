import streamlit as st
import plotly.graph_objects as go
from logic.energy_logic import simulate_battery_logic, get_exact_minimum_requirements

def render_tab2_scenarios(t: dict):
    """
    Renders the Scenarios tab. Applies battery simulations to the baseline data 
    stored in the session state and allows PDF export.
    """
    st.header(t.get("tab_scenarios", "2. Battery Scenarios"))
    
    # Check if baseline data exists on our "notepad" (session state)
    if 'filtered_data' not in st.session_state or st.session_state['filtered_data'] is None:
        st.warning(t.get("no_data_warn", "Please upload and process data in the Baseline tab first."))
        return
        
    # Retrieve data and settings from session state
    filtered_data = st.session_state['filtered_data']
    grid_limit = st.session_state['grid_limit']
    res = st.session_state['resolution']
    col_raw = st.session_state.get('col_raw', '#A9A9A9')
    report_name = st.session_state.get('report_name', 'Energy_Report')
    
    col_input, col_chart = st.columns([1, 3])
    
    with col_input:
        st.subheader(t["header_battery"])
        show_battery = st.toggle(t["enable_bat"], value=True)
        b_cap = st.slider(t["bat_cap"], 0, 500, 100, disabled=not show_battery)
        b_pwr = st.slider(t["bat_pwr"], 0, 200, 50, disabled=not show_battery)
        
        st.subheader(t["header_colors"])
        col_opt = st.color_picker("Optimized Load Color", "#00CC96")
        col_soc = st.color_picker("SoC Color", "#636EFA")
        col_act = st.color_picker("Battery Action Color", "#FFA15A")
        
        # Calculate Hardware Requirements
        min_reqs = get_exact_minimum_requirements(filtered_data, grid_limit, res)
        st.divider()
        st.markdown(f"**{t['metrics_title']}**")
        st.metric(t["metric_peak"], f"{filtered_data['consumption_kw'].max():.1f} kW")
        st.metric(t["metric_min_pwr"], f"{min_reqs['min_power_kw']:.1f} kW")
        st.metric(t["metric_min_cap"], f"{min_reqs['true_min_capacity_kwh']:.1f} kWh")

    with col_chart:
        if not show_battery:
            st.warning(t["no_bat_warn"])
            return

        # Run Battery Simulation
        results = simulate_battery_logic(filtered_data, grid_limit, b_cap, b_pwr, res)
        
        # Main Load Chart
        st.subheader(t["chart_load"])
        fig_load = go.Figure()
        fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['consumption_kw'], 
                                 name="Raw", line=dict(color=col_raw, width=1)))
        fig_load.add_trace(go.Scatter(x=results['timestamp'], y=results['final_grid_load_kw'], 
                                 name="Optimized", line=dict(color=col_opt, width=2)))
        fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red")
        fig_load.update_layout(height=350, yaxis_title="kW", margin=dict(t=10, b=10))
        st.plotly_chart(fig_load, use_container_width=True)

        # Bottom Charts (Action and SoC)
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
            
        # --- PDF EXPORT ---
        st.divider()
        st.subheader("Export Results")
        
        pdf_metrics = {
            "grid_limit": grid_limit,
            "peak_raw": filtered_data['consumption_kw'].max(),
            "min_pwr": min_reqs['min_power_kw'],
            "min_cap": min_reqs['true_min_capacity_kwh']
        }
        
        if st.button(t.get("pdf_button", "Generate PDF Report")): 
            with st.spinner("Creating PDF..."):
                try:
                    from functions.pdf_converter import generate_tech_pdf
                    pdf_data = generate_tech_pdf(
                        report_title=report_name, 
                        metrics=pdf_metrics, 
                        plot_data=results, 
                        battery_enabled=True
                    )
                    
                    st.download_button(
                        label=t.get("pdf_download", "Download Technical PDF"), 
                        data=pdf_data,
                        file_name=f"{report_name}.pdf",
                        mime="application/pdf"
                    )
                except Exception as pdf_error:
                    st.error(f"Error during PDF generation: {pdf_error}")