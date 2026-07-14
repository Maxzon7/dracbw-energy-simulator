# tabs/tab2_components/results_viewer.py
import streamlit as st
import plotly.graph_objects as go
from tabs.tab2_components.feasibility_check import render_feasibility_check
from tabs.tab2_components.performance_matrix import render_performance_matrix
from tabs.tab2_components.pdf_export import generate_tech_pdf
import copy

def render_results_and_charts(results, baseline_df, grid_limit, res, current_mode, current_params, project_metadata, selected_name, is_draft, colors, report_name):
    """
    Handles all UI rendering for the right-hand column in Tab 2.
    Draws charts, displays performance matrices, and manages PDF exports.
    """
    if is_draft:
        st.subheader(f"⚡ Live View: [UNSAVED DRAFT PREVIEW]")
    else:
        st.subheader(f"⚡ Live View: {selected_name}")
        
    render_feasibility_check(results, grid_limit, current_params, current_mode)
    
    # --- CHART 1: The Main Load Chart ---
    fig_load = go.Figure()
    fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['consumption_kw'], name="Original Demand", line=dict(color=colors['raw'], width=1)))
    fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['final_grid_load_kw'], name="Optimized Grid Demand", line=dict(color=colors['opt'], width=2)))
    
    has_solar = 'solar_gen_kw' in results.columns and results['solar_gen_kw'].sum() > 0
    has_battery = 'battery_action_kw' in results.columns and (results['battery_action_kw'] != 0.0).any()
    has_generator = 'generator_action_kw' in results.columns and results['generator_action_kw'].sum() > 0
    has_fuel = 'generator_fuel_l' in results.columns and results['generator_fuel_l'].sum() > 0

    if has_solar:
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name="Solar Yield", line=dict(color=colors.get('sol', '#FFC107'), width=1), fill='tozeroy'))
    if has_battery:
        battery_discharge = results['battery_action_kw'].clip(lower=0.0)
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=battery_discharge, name="Battery Discharge", line=dict(color=colors['act'], width=1), fill='tozeroy'))
        
        battery_charge = results['battery_action_kw'].clip(upper=0.0).abs()
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=battery_charge, name="Battery Charge", line=dict(color=colors.get('chg', '#AB63FA'), width=1), fill='tozeroy'))
    if has_generator:
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name="Generator Output", line=dict(color=colors['gen'], width=1), fill='tozeroy'))
                                  
    if grid_limit > 0.0 and grid_limit < 99000.0:
        fig_load.add_hline(y=grid_limit, line_dash="dash", line_color=colors.get('lim', '#FF0000'), annotation_text="Grid Limit")
    fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_load, use_container_width=True)

    if has_fuel:
        total_fuel = results['generator_fuel_l'].sum()
        if total_fuel > 0:
            st.error(f"🛢️ **Total Diesel Fuel Consumed:** {total_fuel:,.1f} Liters")
        else:
            st.success("🌱 No generator fuel required! The system handled all peaks.")

    # --- CHART 2: Sub-charts (Dynamic responsive layout) ---
    if has_battery and has_solar:
        import numpy as np
        c_left, c_right = st.columns(2)
        with c_left:
            st.write("**Solar Energy Utilization (kW)**")
            solar_gen = results['solar_gen_kw']
            cons = results['consumption_kw']
            bat_action = results['battery_action_kw']
            
            solar_self_cons = np.minimum(solar_gen, cons)
            
            # Solar charging battery (occurs when BESS is charging, i.e., action < 0)
            bat_charge = np.where(bat_action < 0, np.abs(bat_action), 0.0)
            solar_surplus = np.maximum(0.0, solar_gen - cons)
            solar_to_bat = np.minimum(solar_surplus, bat_charge)
            
            # Remaining solar excess exported or curtailed
            solar_excess = np.maximum(0.0, solar_gen - solar_self_cons - solar_to_bat)
            
            fig_sol_util = go.Figure()
            fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_self_cons, name="Covering Demand", stackgroup='one', line=dict(width=0.5, color=colors.get('sol_self', '#4CAF50')), fill='tonexty'))
            fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_to_bat, name="To Battery", stackgroup='one', line=dict(width=0.5, color=colors.get('sol_bat', '#AB63FA')), fill='tonexty'))
            fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_excess, name="Excess (Export/Curtail)", stackgroup='one', line=dict(width=0.5, color=colors.get('sol_exc', '#FF9800')), fill='tonexty'))
            
            fig_sol_util.update_layout(height=230, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_sol_util, use_container_width=True)
            
        with c_right:
            st.write("**Battery SoC (kWh)**")
            fig_soc = go.Figure()
            fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color=colors['soc'])))
            fig_soc.update_layout(height=230, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_soc, use_container_width=True)
            
    elif has_battery:
        # BESS Only: full-width SoC chart
        st.write("**Battery SoC (kWh)**")
        fig_soc = go.Figure()
        fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color=colors['soc'])))
        fig_soc.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_soc, use_container_width=True)
        
    elif has_solar:
        # Solar Only: full-width Solar Utilization chart
        import numpy as np
        st.write("**Solar Energy Utilization (kW)**")
        solar_gen = results['solar_gen_kw']
        cons = results['consumption_kw']
        solar_self_cons = np.minimum(solar_gen, cons)
        solar_excess = np.maximum(0.0, solar_gen - solar_self_cons)
        
        fig_sol_util = go.Figure()
        fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_self_cons, name="Covering Demand", stackgroup='one', line=dict(width=0.5, color=colors.get('sol_self', '#4CAF50')), fill='tonexty'))
        fig_sol_util.add_trace(go.Scatter(x=results['timestamp'], y=solar_excess, name="Excess (Export/Curtail)", stackgroup='one', line=dict(width=0.5, color=colors.get('sol_exc', '#FF9800')), fill='tonexty'))
        
        fig_sol_util.update_layout(height=300, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_sol_util, use_container_width=True)

    peak_orig, min_reqs = render_performance_matrix(results, baseline_df, grid_limit, res, current_mode, current_params, project_metadata)

    # --- PDF EXPORT ---
    st.divider()
    if st.button("📄 Generate Technical PDF Report", type="primary"):
        if is_draft:
            st.error("Please Save (Commit) your changes to the vault before generating a PDF.")
        else:
            with st.spinner("Compiling technical evaluation..."):
                try:
                    pdf_metrics = {"grid_limit": grid_limit, "peak_raw": peak_orig, "min_pwr": min_reqs['min_power_kw'], "min_cap": min_reqs['true_min_capacity_kwh']}
                    pdf_data = generate_tech_pdf(f"{report_name}_{current_mode.replace(' ', '')}", pdf_metrics, results, has_battery)
                    st.download_button("⬇️ Download Document", data=pdf_data, file_name=f"{report_name}.pdf", mime="application/pdf")
                except Exception as pdf_error:
                    st.error(f"Error compiling document: {pdf_error}")

    # --- CSV EXPORT ---
    st.divider()
    with st.expander("Export Simulation Results as CSV", expanded=False):
        st.write("Customize column names for the CSV export:")
        
        col_name_inputs = {}
        
        # Check active columns and provide text inputs
        if "timestamp" in results.columns:
            col_name_inputs["timestamp"] = st.text_input("Timestamp Column Name", value="Timestamp", key=f"csv_col_time_{selected_name}")
        if "consumption_kw" in results.columns:
            col_name_inputs["consumption_kw"] = st.text_input("Original Load Column Name", value="Original Load", key=f"csv_col_cons_{selected_name}")
        if "final_grid_load_kw" in results.columns:
            col_name_inputs["final_grid_load_kw"] = st.text_input("Optimized Grid Demand Column Name", value="Optimized Grid Demand", key=f"csv_col_opt_{selected_name}")
        if "battery_action_kw" in results.columns:
            col_name_inputs["battery_action_kw"] = st.text_input("Battery Action Column Name", value="Battery Action", key=f"csv_col_bat_act_{selected_name}")
        if "battery_soc_kwh" in results.columns:
            col_name_inputs["battery_soc_kwh"] = st.text_input("Battery State of Charge Column Name", value="Battery State of Charge", key=f"csv_col_bat_soc_{selected_name}")
        if "solar_gen_kw" in results.columns:
            col_name_inputs["solar_gen_kw"] = st.text_input("Solar Yield Column Name", value="Solar Yield", key=f"csv_col_sol_gen_{selected_name}")
        if "generator_action_kw" in results.columns:
            col_name_inputs["generator_action_kw"] = st.text_input("Generator Output Column Name", value="Generator Output", key=f"csv_col_gen_act_{selected_name}")
        if "generator_fuel_l" in results.columns:
            col_name_inputs["generator_fuel_l"] = st.text_input("Generator Fuel Column Name", value="Generator Fuel Consumption", key=f"csv_col_gen_fuel_{selected_name}")

        cols_to_export = [col for col in col_name_inputs.keys() if col in results.columns]
        if cols_to_export:
            export_df = results[cols_to_export].copy()
            export_df.rename(columns=col_name_inputs, inplace=True)
            csv_data = export_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download Simulation Results (CSV)",
                data=csv_data,
                file_name=f"{selected_name}_simulation_export.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"csv_dl_btn_{selected_name}"
            )

def render_scenario_clone_ui(vault, selected_name, is_draft):
    """Handles the cloning of scenarios into the vault."""
    st.divider()
    st.write("### 💾 Create a Copy (Optional)")
    
    sub_scenario_name = st.text_input("Name this Copy:", value=f"{selected_name}_Copy")
    save_disabled = False
    vault_button_text = "🚀 Save as New Copy"
    
    if sub_scenario_name in vault:
        st.warning(f"⚠️ Variant '{sub_scenario_name}' already exists.")
        if not st.checkbox("Confirm: Overwrite", value=False): save_disabled = True
        else: vault_button_text = "⚠️ OVERWRITE"
    
    if is_draft:
        st.error("Commit current draft before duplicating.")
    else:
        if st.button(vault_button_text, type="primary", use_container_width=True, disabled=save_disabled):
            vault[sub_scenario_name] = copy.deepcopy(vault[selected_name])
            st.session_state['scenario_vault'] = vault
            st.success("✅ Copy created!")
            st.rerun()