import streamlit as st
from tabs.tab2_components.results_viewer import render_results_and_charts

@st.fragment
def render_charts_fragment(calculated_df, plot_base_df, sim_grid_limit, res, scenario_mode, params, project_metadata, selected_base_name):
    # 1. Resolve colors dynamically from session state or fallbacks
    colors_to_use = {
        'raw': st.session_state.get('cp_raw', '#A9A9A9'),
        'opt': st.session_state.get('cp_opt', '#00CC96'),
        'soc': st.session_state.get('cp_soc', '#636EFA'),
        'act': st.session_state.get('cp_act', '#FFA15A'),
        'chg': st.session_state.get('cp_chg', '#AB63FA'),
        'sol': st.session_state.get('cp_sol', '#FFC107'),
        'gen': st.session_state.get('cp_gen', '#8B0000'),
        'lim': st.session_state.get('cp_lim', '#FF0000'),
        'sol_self': st.session_state.get('cp_self', '#4CAF50'),
        'sol_bat': st.session_state.get('cp_sol_bat', '#AB63FA'),
        'sol_exc': st.session_state.get('cp_exc', '#FF9800')
    }
    # Ensure this is synchronized for saving
    st.session_state['chart_colors'] = colors_to_use

    # 2. Render charts
    render_results_and_charts(
        calculated_df, plot_base_df, sim_grid_limit, res,
        scenario_mode, params, project_metadata, selected_base_name, False, colors_to_use, f"Report_{selected_base_name}"
    )
    
    # 3. Render color pickers
    st.write("") # spacing
    with st.expander("🎨 Chart Colors Customization (Farben anpassen)", expanded=False):
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        raw_c = col_c1.color_picker("Original Demand (Raw)", value=colors_to_use['raw'], key="cp_raw")
        opt_c = col_c2.color_picker("Optimized Grid Demand", value=colors_to_use['opt'], key="cp_opt")
        lim_c = col_c3.color_picker("Grid Limit Line", value=colors_to_use['lim'], key="cp_lim")
        soc_c = col_c4.color_picker("BESS SoC", value=colors_to_use['soc'], key="cp_soc")
        
        act_c = col_c1.color_picker("Battery Discharge", value=colors_to_use['act'], key="cp_act")
        chg_c = col_c2.color_picker("Battery Charge", value=colors_to_use['chg'], key="cp_chg")
        sol_c = col_c3.color_picker("Solar Yield (Main)", value=colors_to_use['sol'], key="cp_sol")
        gen_c = col_c4.color_picker("Generator Output", value=colors_to_use['gen'], key="cp_gen")
        
        self_c = col_c1.color_picker("Solar: Covering Demand", value=colors_to_use['sol_self'], key="cp_self")
        bat_c = col_c2.color_picker("Solar: Charging Battery", value=colors_to_use['sol_bat'], key="cp_sol_bat")
        exc_c = col_c3.color_picker("Solar: Excess (Export/Curtail)", value=colors_to_use['sol_exc'], key="cp_exc")
