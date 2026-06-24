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
    
    if current_mode in ["Solar PV Only", "Combined (All)"] and 'solar_gen_kw' in results.columns:
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['solar_gen_kw'], name="Solar Yield", line=dict(color='#FFC107', width=1), fill='tozeroy'))
    if current_mode in ["Generator Only", "Combined (All)"] and 'generator_action_kw' in results.columns:
        fig_load.add_trace(go.Scattergl(x=results['timestamp'], y=results['generator_action_kw'], name="Generator Output", line=dict(color=colors['gen'], width=1), fill='tozeroy'))
                                  
    fig_load.add_hline(y=grid_limit, line_dash="dash", line_color="red", annotation_text="Grid Limit")
    fig_load.update_layout(height=400, yaxis_title="kW", margin=dict(t=10, b=10), legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_load, use_container_width=True)

    if current_mode in ["Generator Only", "Combined (All)"] and 'generator_fuel_l' in results.columns:
        total_fuel = results['generator_fuel_l'].sum()
        if total_fuel > 0:
            st.error(f"🛢️ **Total Diesel Fuel Consumed:** {total_fuel:,.1f} Liters")
        else:
            st.success("🌱 No generator fuel required! The system handled all peaks.")

    # --- CHART 2: Battery specific charts ---
    if current_mode in ["Battery (BESS) Only", "Combined (All)"]:
        c_left, c_right = st.columns(2)
        with c_left:
            st.write("**Battery Action (kW)**")
            fig_act = go.Figure()
            fig_act.add_trace(go.Bar(x=results['timestamp'], y=results['battery_action_kw'], marker_color=colors['act']))
            fig_act.update_layout(height=230, margin=dict(t=10, b=10))
            st.plotly_chart(fig_act, use_container_width=True)
        with c_right:
            st.write("**Battery SoC (kWh)**")
            fig_soc = go.Figure()
            fig_soc.add_trace(go.Scattergl(x=results['timestamp'], y=results['battery_soc_kwh'], fill='tozeroy', line=dict(color=colors['soc'])))
            fig_soc.update_layout(height=230, margin=dict(t=10, b=10))
            st.plotly_chart(fig_soc, use_container_width=True)

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
                    pdf_data = generate_tech_pdf(f"{report_name}_{current_mode.replace(' ', '')}", pdf_metrics, results, (current_mode in ["Battery (BESS) Only", "Combined (All)"]))
                    st.download_button("⬇️ Download Document", data=pdf_data, file_name=f"{report_name}.pdf", mime="application/pdf")
                except Exception as pdf_error:
                    st.error(f"Error compiling document: {pdf_error}")

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