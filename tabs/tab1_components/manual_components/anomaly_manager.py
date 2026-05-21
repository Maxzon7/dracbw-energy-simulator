# tabs/tab1_components/manual_components/anomaly_manager.py
import streamlit as st
import datetime
import uuid
from data_models.scenarios import AnomalyConfig

def render_anomaly_manager():
    """
    Renders the Upgraded Anomaly & Event Manager UI components.
    Saves configurations directly to session state.
    """
    st.subheader("⚡ Upgraded Anomaly & Event Manager")
    st.info("Inject complex peaks, plant shutdowns, or completely random event blocks into your timeline.")
    
    if 'current_anomalies' not in st.session_state:
        st.session_state['current_anomalies'] = []
    if 'temp_random_dates' not in st.session_state:
        st.session_state['temp_random_dates'] = []

    # 1. Configuration Form Window
    with st.expander("➕ Create New Dynamic Anomaly", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            anomaly_type = st.selectbox("Load Behavior Profile", 
                options=['additional_load', 'fixed_value', 'reduction'],
                format_func=lambda x: {
                    'additional_load': "📈 Additional Peak Load (+ kW)",
                    'fixed_value': "📌 Set Fixed Constant Load (= kW)",
                    'reduction': "📉 Load Reduction / Shutdown (- kW)"
                }[x]
            )
            value_kw = st.number_input("Target Value (kW)", min_value=0.0, value=50.0, step=10.0)
            
        with col2:
            st.write("**Daily Active Window**")
            start_time = st.time_input("Start Time Raster", value=datetime.time(8, 0))
            end_time = st.time_input("End Time Raster", value=datetime.time(14, 0))

        st.divider()

        frequency_type = st.radio("Frequency & Distribution Pattern", 
            options=['regular', 'block', 'random'],
            format_func=lambda x: {
                'regular': "🔄 Recurring Pattern (Selected Weekdays)",
                'block': "📅 Continuous Block (Date Range Interval)",
                'random': "🎯 Random Selector (Custom Calendar Days)"
            }[x],
            horizontal=True
        )

        regular_days = []
        block_start = None
        block_end = None
        random_dates = []

        if frequency_type == 'regular':
            regular_days = st.multiselect("Select Target Weekdays", 
                options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            )
        elif frequency_type == 'block':
            date_range = st.date_input("Select Event Horizon Duration", 
                                       value=[datetime.date.today(), datetime.date.today() + datetime.timedelta(days=7)])
            if len(date_range) == 2:
                block_start, block_end = date_range
        elif frequency_type == 'random':
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                new_date = st.date_input("Pick Custom Target Date")
            with col_d2:
                st.write("") 
                st.write("") 
                if st.button("➕ Add Day"):
                    if new_date not in st.session_state['temp_random_dates']:
                        st.session_state['temp_random_dates'].append(new_date)
            
            if st.session_state['temp_random_dates']:
                st.write("**Target Days Registered:**")
                for d in st.session_state['temp_random_dates']:
                    st.markdown(f"- {d.strftime('%d.%m.%Y')}")
                random_dates = st.session_state['temp_random_dates']

        if st.button("💾 Save Anomaly to Profile Pipeline", type="primary", use_container_width=True):
            new_anomaly = AnomalyConfig(
                id=str(uuid.uuid4())[:8],
                anomaly_type=anomaly_type,
                value_kw=value_kw,
                frequency_type=frequency_type,
                start_time=start_time.strftime("%H:%M"),
                end_time=end_time.strftime("%H:%M"),
                regular_days=regular_days,
                block_start_date=block_start.strftime("%Y-%m-%d") if block_start else None,
                block_end_date=block_end.strftime("%Y-%m-%d") if block_end else None,
                random_dates=[d.strftime("%Y-%m-%d") for d in random_dates]
            )
            st.session_state['current_anomalies'].append(new_anomaly)
            st.session_state['temp_random_dates'] = [] 
            st.success("Anomaly added to baseline configuration pipeline!")
            st.rerun()

    # List overview and remove actions
    if st.session_state['current_anomalies']:
        st.write("### 🗃️ Active Anomalies inside this Scenario Configuration")
        for idx, an in enumerate(st.session_state['current_anomalies']):
            col_info, col_del = st.columns([5, 1])
            with col_info:
                type_lbl = {"additional_load": "+kW", "fixed_value": "=kW", "reduction": "-kW"}[an.anomaly_type]
                st.info(f"**{type_lbl}** ({an.value_kw} kW) | {an.start_time} - {an.end_time} | Type: *{an.frequency_type}*")
            with col_del:
                if st.button("❌ Remove", key=f"del_{an.id}", use_container_width=True):
                    st.session_state['current_anomalies'].pop(idx)
                    st.rerun()