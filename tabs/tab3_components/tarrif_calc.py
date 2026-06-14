import streamlit as st

def render_custom_tariff_form():
    """
    Renders a UI form to create and save custom energy tariffs.
    This allows users to define new pricing structures dynamically without modifying the underlying source code.
    """
    st.subheader("Tariff Configuration Manager")
    
    # Dropdown to select existing or new country
    # Note: These options will later be populated dynamically from the JSON database
    existing_countries = ["Netherlands", "Germany", "+ Add New Country"]
    selected_country = st.selectbox("Select Target Country", existing_countries)
    
    if selected_country == "+ Add New Country":
        new_country = st.text_input("Enter New Country Name")
    
    # Form wrapper to prevent app refresh on every keystroke
    with st.form("custom_tariff_form"):
        st.markdown("#### Define Tariff Parameters")
        
        tariff_name = st.text_input("Tariff Name (e.g., 'Liander Custom 2027')")
        
        # Determine the billing logic
        tariff_type = st.radio(
            "Connection Billing Type", 
            ["Large Consumer (kW/kWh based)", "Small Consumer (Flatrate / Capacity based)"]
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            currency = st.selectbox("Currency", ["EUR", "USD", "GBP"])
            fixed_monthly_fee = st.number_input("Fixed Monthly Fee", min_value=0.0, value=0.0, step=10.0)
            transport_fixed_fee = st.number_input("Transport Fixed Fee", min_value=0.0, value=0.0, step=10.0)
            
        with col2:
            if tariff_type == "Large Consumer (kW/kWh based)":
                kw_contract_price = st.number_input("Price per Contracted kW", min_value=0.0, value=0.0, step=0.1)
                kw_peak_penalty_price = st.number_input("Penalty Price per Peak kW", min_value=0.0, value=0.0, step=0.1)
                kwh_transport_price = st.number_input("Transport Price per kWh", min_value=0.0000, value=0.0000, step=0.0010, format="%.4f")
            else:
                flatrate_price = st.number_input("Monthly Flatrate Price (e.g., 2x80A limit)", min_value=0.0, value=0.0, step=10.0)
        
        # The submit button triggers the form data processing
        submitted = st.form_submit_button("Save Custom Tariff")
        
        if submitted:
            if not tariff_name:
                st.error("Please provide a valid Tariff Name before saving.")
            else:
                # Placeholder for backend integration
                # Here we will later pass the gathered variables to the TariffManager class
                st.success(f"Tariff '{tariff_name}' has been successfully generated and queued for saving.")

def render_tariff_builder_ui():
    """
    Renders a secure, self-contained UI form to create and inject custom energy tariffs.
    Saves the results into the session state so the financial engine can access them immediately.
    """
    # Ensure the short-term memory for custom tariffs exists
    if 'custom_tariffs' not in st.session_state:
        st.session_state['custom_tariffs'] = {}

    with st.expander("⚙️ Tariff Configuration Manager (Create Custom Tariffs)", expanded=False):
        st.info("Design a custom energy tariff. Once saved, it will be injected into the calculation engine's memory for the current session.")
        
        with st.form("custom_tariff_builder_form"):
            col_name, col_type = st.columns(2)
            
            with col_name:
                provider_name = st.text_input("Tariff / Provider Name", placeholder="e.g., E.ON Custom 2027")
                target_country = st.selectbox("Target Country", ["Netherlands", "Germany", "Argentina", "Other"])
            
            with col_type:
                billing_type = st.radio("Billing Structure", ["Large Consumer (kW/kWh based)", "Small Consumer (Flatrate based)"])
            
            st.divider()
            st.write("**Pricing Parameters**")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                currency = st.selectbox("Currency", ["EUR", "USD", "GBP"])
                fixed_monthly = st.number_input("Fixed Monthly Fee", min_value=0.0, value=0.0, step=10.0)
                fixed_transport = st.number_input("Fixed Transport Fee", min_value=0.0, value=0.0, step=10.0)
            
            with c2:
                if billing_type == "Large Consumer (kW/kWh based)":
                    kw_contract = st.number_input("Price per Contracted kW", min_value=0.0, value=0.0, step=0.1)
                    kw_peak = st.number_input("Penalty Price per Peak kW", min_value=0.0, value=0.0, step=0.1)
                else:
                    flatrate = st.number_input("Monthly Capacity Flatrate (e.g., 2x80A)", min_value=0.0, value=0.0, step=10.0)
            
            with c3:
                if billing_type == "Large Consumer (kW/kWh based)":
                    kwh_transport = st.number_input("Transport Price per kWh", min_value=0.0000, value=0.0000, step=0.0010, format="%.4f")
            
            # Form submission trigger
            submitted = st.form_submit_button("Save & Inject Custom Tariff", type="primary", use_container_width=True)
            
            if submitted:
                if not provider_name:
                    st.error("Operation failed: Please enter a valid Tariff Name to proceed.")
                else:
                    # Ensure country structure exists
                    if target_country not in st.session_state['custom_tariffs']:
                        st.session_state['custom_tariffs'][target_country] = {}
                        
                    # Standardized data model insertion
                    if billing_type == "Large Consumer (kW/kWh based)":
                        st.session_state['custom_tariffs'][target_country][provider_name] = {
                            "type": "AC5_AC4",
                            "fixed_monthly_fee": fixed_monthly,
                            "transport_fixed_fee": fixed_transport,
                            "kw_contract_price": kw_contract,
                            "kw_peak_penalty_price": kw_peak,
                            "kwh_transport_price": kwh_transport,
                            "currency": currency
                        }
                    else:
                        st.session_state['custom_tariffs'][target_country][provider_name] = {
                            "type": "2x80A",
                            "fixed_monthly_fee": fixed_monthly,
                            "transport_fixed_fee": fixed_transport,
                            "flatrate_price": flatrate,
                            "currency": currency
                        }
                    st.success(f"Successfully injected '{provider_name}' into the active memory for {target_country}!")