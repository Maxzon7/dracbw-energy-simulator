import streamlit as st
import pandas as pd

def render_technical_comparison_matrix(selected_profiles, linked_subs, selected_base_obj, selected_base_name):
    """Generates and displays the Technical Comparison Matrix comparison table."""
    if len(selected_profiles) >= 1:
        st.write("### Technical Comparison Matrix")
        
        comparison_rows = []
        base_df = selected_base_obj.original_profile
        base_limit = selected_base_obj.base_tariff.contracted_capacity_kw
        base_peak = base_df['consumption_kw'].max() if 'consumption_kw' in base_df.columns else base_df.iloc[:, 1].max()
        
        base_limit_str = f"{base_limit:.1f} kW" if base_limit < 99000 else "Unlimited"
        base_margin = base_limit - base_peak
        
        if base_limit >= 99000:
            base_margin_str = "Unlimited"
            base_avail_str = "Unlimited"
            base_feasibility = "✅ Yes"
        else:
            base_margin_str = f"{base_margin:.1f} kW"
            base_avail_str = f"{max(0.0, base_margin):.1f} kW"
            base_feasibility = "Yes" if base_peak <= base_limit else "No"
            
        comparison_rows.append({
            "Scenario Name": f"{selected_base_obj.name} (Base)",
            "Grid Connection": selected_base_obj.base_tariff.name,
            "Grid Capacity": base_limit_str,
            "Battery Power": "NONE",
            "New Peak": f"{base_peak:.1f} kW",
            "Safety Margin": base_margin_str,
            "Available Power": base_avail_str,
            "Technically Sufficient?": base_feasibility
        })
        
        for name in selected_profiles:
            if name == selected_base_name:
                continue
                
            sub_obj = next((s for s in linked_subs if s.name == name), None)
            if not sub_obj:
                continue
                
            sub_df = sub_obj.simulated_profile
            sub_limit = sub_obj.custom_tariff.contracted_capacity_kw if sub_obj.custom_tariff else base_limit
            
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in sub_df.columns else 'consumption_kw'
            sub_peak = sub_df[y_col].max()
            
            sub_limit_str = f"{sub_limit:.1f} kW" if sub_limit < 99000 else "Unlimited"
            sub_margin = sub_limit - sub_peak
            
            if sub_limit >= 99000:
                sub_margin_str = "Unlimited"
                sub_avail_str = "Unlimited"
                sub_feasibility = "✅ Yes"
            else:
                sub_margin_str = f"{sub_margin:.1f} kW"
                sub_avail_str = f"{max(0.0, sub_margin):.1f} kW"
                sub_feasibility = "Yes" if sub_peak <= sub_limit else "No"
                
            b_str = f"{sub_obj.battery_kwh:.1f} kWh / {sub_obj.battery_kw:.1f} kW" if sub_obj.battery_kwh > 0 else "NONE"
            t_name = sub_obj.custom_tariff.name if sub_obj.custom_tariff else selected_base_obj.base_tariff.name
            
            comparison_rows.append({
                "Scenario Name": f"{sub_obj.name}",
                "Grid Connection": t_name,
                "Grid Capacity": sub_limit_str,
                "Battery Power": b_str,
                "New Peak": f"{sub_peak:.1f} kW",
                "Safety Margin": sub_margin_str,
                "Available Power": sub_avail_str,
                "Technically Sufficient?": sub_feasibility
            })
            
        st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True, hide_index=True)
