# tabs/tab1_components/upload.py
import streamlit as st
from logic.energy_logic import load_and_clean_csv, process_consumption_data

def render_csv_upload_section():
    """
    Handles CSV file upload, parameter selection, and data processing.
    Saves the final processed dataframe to session_state['filtered_data'].
    """
    t = st.session_state['t']
    
    st.subheader(t["header_data"])
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
    
    if uploaded_file:
        default_name = uploaded_file.name.rsplit('.', 1)[0]
        st.session_state['report_name'] = st.text_input("Report Title", value=f"Report_{default_name}")
    
    st.subheader(t["header_grid"])
    grid_limit = st.number_input(t["grid_limit"], value=50.0, step=5.0)
    res = st.selectbox(t["resolution"], [1, 5, 15, 60], index=2)
    col_raw = st.color_picker("Raw Load Color", "#A9A9A9")
    
    # Save parameters to session state for downstream tabs
    st.session_state['grid_limit'] = grid_limit
    st.session_state['resolution'] = res
    st.session_state['col_raw'] = col_raw

    # Process data if file exists
    if uploaded_file:
        try:
            raw_df = load_and_clean_csv(uploaded_file)
            data = process_consumption_data(raw_df, res)
            
            min_date, max_date = data['timestamp'].min().date(), data['timestamp'].max().date()
            selected_dates = st.date_input(t["analysis_period"], [min_date, max_date])
            
            if len(selected_dates) == 2:
                # Lock data into global memory
                filtered_df = data[(data['timestamp'].dt.date >= selected_dates[0]) & 
                                   (data['timestamp'].dt.date <= selected_dates[1])]
                
                st.session_state['filtered_data'] = filtered_df
                
                # --- NEU: ZEITRAUM-ANZEIGE FÜR COMPONENT ---
                if len(filtered_df) > 0:
                    start_dt = filtered_df['timestamp'].min()
                    end_dt = filtered_df['timestamp'].max()
                    duration_days = (end_dt.date() - start_dt.date()).days + 1  # Inklusive Starttag
                    
                    st.info(
                        f"📅 **Selected Timeframe:**\n\n"
                        f"• **Start:** {start_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"• **End:** {end_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"• **Total Duration:** {duration_days} days"
                    )
                # --- ENDE NEU ---
                
        except Exception as e:
            st.error(f"CSV Processing Error: {e}")