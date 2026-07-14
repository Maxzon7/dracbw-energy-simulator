# tabs/tab3_components/pdf_comparison_export.py
import io
import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pypdf import PdfReader, PdfWriter

from tabs.tab3_components.financial_engine import generate_15_year_cashflow

def compile_matplotlib_load_chart(selected_profiles, get_df_for_name, custom_colors, limit):
    """
    Generates a combined load profile chart with Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(8.5, 3.5))
    for name in selected_profiles:
        df = get_df_for_name(name)
        if df is not None and not df.empty:
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in df.columns else 'consumption_kw'
            if y_col not in df.columns:
                y_col = df.columns[-1]
            x_col = df['timestamp'] if 'timestamp' in df.columns else df.index
            color = custom_colors.get(name, '#333333')
            ax.plot(x_col, df[y_col], label=name, color=color, linewidth=1.0, alpha=0.85)
            
    if limit > 0 and limit < 99000:
        ax.axhline(y=limit, color='red', linestyle='--', label='Grid Limit', linewidth=1.2)
        
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H:%M'))
    plt.xticks(rotation=20, fontsize=8)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=180)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def compile_matplotlib_soc_chart(selected_profiles, get_df_for_name, linked_subs, custom_colors):
    """
    Generates a combined battery State of Charge (SoC) chart with Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    has_data = False
    for name in selected_profiles:
        sub = next((s for s in linked_subs if s.name == name), None)
        if sub and sub.battery_kwh > 0:
            df = get_df_for_name(name)
            if df is not None and 'battery_soc_kwh' in df.columns:
                x_col = df['timestamp'] if 'timestamp' in df.columns else df.index
                color = custom_colors.get(name, '#636EFA')
                ax.plot(x_col, df['battery_soc_kwh'], label=f"{name} SoC", color=color, linewidth=1.0)
                has_data = True
                
    if not has_data:
        plt.close(fig)
        return None
        
    ax.set_ylabel('State of Charge (kWh)')
    ax.legend(loc='upper right', fontsize=7, framealpha=0.9)
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H:%M'))
    plt.xticks(rotation=20, fontsize=8)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=180)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def compile_matplotlib_cashflow_chart(selected_profiles, base_scenario, linked_subs, custom_colors):
    """
    Generates a combined cumulative cashflow comparison chart with Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    has_data = False
    for name in selected_profiles:
        sub = next((s for s in linked_subs if s.name == name), None)
        if sub and sub.financials:
            df_cashflow = generate_15_year_cashflow(sub, base_scenario)
            color = custom_colors.get(name, '#1f77b4')
            ax.plot(df_cashflow["Jahr"], df_cashflow["Kumulierter_Cashflow"], label=name, color=color, marker='o', linewidth=1.2, markersize=3)
            has_data = True
            
    if not has_data:
        plt.close(fig)
        return None
        
    ax.set_ylabel('Cumulative Cashflow (€)')
    ax.set_xlabel('Years')
    ax.legend(loc='lower right', fontsize=7, framealpha=0.9)
    ax.grid(True, linestyle=':', alpha=0.5)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=180)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def merge_with_template(overlay_buffer, template_path):
    """
    Merges every transparent page in overlay_buffer onto the background first page of Template.pdf.
    """
    if not os.path.exists(template_path):
        return overlay_buffer
        
    overlay_pdf = PdfReader(overlay_buffer)
    output = PdfWriter()
    
    for page_idx in range(len(overlay_pdf.pages)):
        bg_reader = PdfReader(open(template_path, "rb"))
        bg_page = bg_reader.pages[0]
        bg_page.merge_page(overlay_pdf.pages[page_idx])
        output.add_page(bg_page)
        
    final_output = io.BytesIO()
    output.write(final_output)
    final_output.seek(0)
    return final_output

def compile_report_pdf(base_scenario, selected_profiles, linked_subs,
                       title, client, description,
                       incl_table, incl_load, incl_soc, incl_cashflow, custom_colors):
    """
    Assembles a multi-page ReportLab document using tables, paragraph flowables, 
    and matplotlib plots. Stamped on top of the corporate template layout.
    """
    overlay_buffer = io.BytesIO()
    
    # Document Template setup leaving margins for company header
    doc = SimpleDocTemplate(
        overlay_buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=140, 
        bottomMargin=65
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#7F8C8D'),
        spaceAfter=20
    )
    
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#00CC96'), # DRACBV Green style
        spaceBefore=12,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        textColor=colors.HexColor('#2C3E50'),
        leading=14,
        spaceAfter=15
    )
    
    elements = []
    
    # 1. Header details
    elements.append(Paragraph(title, title_style))
    current_date = datetime.date.today().strftime("%d %B %Y")
    elements.append(Paragraph(f"<b>Client/Project:</b> {client} | <b>Date:</b> {current_date}", meta_style))
    
    # 2. Executive Summary / Notes
    if description:
        elements.append(Paragraph("Executive Summary", h2_style))
        elements.append(Paragraph(description.replace('\n', '<br/>'), body_style))
        
    # 3. Technical Comparison Matrix Table
    if incl_table:
        elements.append(Paragraph("Technical Evaluation Matrix", h2_style))
        
        table_data = [[
            "Scenario Name", "Connection", "Grid Limit", 
            "Battery System", "Peak Load", "Margin", "Feasible?"
        ]]
        
        def get_df_for_name(name):
            if name == base_scenario.name:
                return base_scenario.original_profile
            else:
                sub = next((s for s in linked_subs if s.name == name), None)
                return sub.simulated_profile if sub else None
                
        base_df = base_scenario.original_profile
        base_limit = base_scenario.base_tariff.contracted_capacity_kw
        base_peak = base_df['consumption_kw'].max() if 'consumption_kw' in base_df.columns else base_df.iloc[:, 1].max()
        base_limit_str = f"{base_limit:.1f} kW" if base_limit < 99000 else "Unlimited"
        
        if base_limit >= 99000:
            base_margin_str = "Unlimited"
            base_feasibility = "Yes"
        else:
            base_margin = base_limit - base_peak
            base_margin_str = f"{base_margin:.1f} kW"
            base_feasibility = "Yes" if base_peak <= base_limit else "No"
            
        table_data.append([
            base_scenario.name + " (Base)",
            base_scenario.base_tariff.name,
            base_limit_str,
            "NONE",
            f"{base_peak:.1f} kW",
            base_margin_str,
            base_feasibility
        ])
        
        for name in selected_profiles:
            if name == base_scenario.name:
                continue
            sub_obj = next((s for s in linked_subs if s.name == name), None)
            if not sub_obj:
                continue
                
            sub_df = sub_obj.simulated_profile
            sub_limit = sub_obj.custom_tariff.contracted_capacity_kw if sub_obj.custom_tariff else base_limit
            y_col = 'final_grid_load_kw' if 'final_grid_load_kw' in sub_df.columns else 'consumption_kw'
            sub_peak = sub_df[y_col].max()
            sub_limit_str = f"{sub_limit:.1f} kW" if sub_limit < 99000 else "Unlimited"
            
            if sub_limit >= 99000:
                sub_margin_str = "Unlimited"
                sub_feasibility = "Yes"
            else:
                sub_margin = sub_limit - sub_peak
                sub_margin_str = f"{sub_margin:.1f} kW"
                sub_feasibility = "Yes" if sub_peak <= sub_limit else "No"
                
            b_str = f"{sub_obj.battery_kwh:.1f}kWh/{sub_obj.battery_kw:.1f}kW" if sub_obj.battery_kwh > 0 else "NONE"
            t_name = sub_obj.custom_tariff.name if sub_obj.custom_tariff else base_scenario.base_tariff.name
            
            table_data.append([
                sub_obj.name,
                t_name,
                sub_limit_str,
                b_str,
                f"{sub_peak:.1f} kW",
                sub_margin_str,
                sub_feasibility
            ])
            
        col_widths = [110, 80, 60, 85, 55, 60, 45]
        rep_table = Table(table_data, colWidths=col_widths)
        t_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8F9FA')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        rep_table.setStyle(t_style)
        elements.append(rep_table)
        elements.append(Spacer(1, 15))
        
    # Append page break for charts if any chosen
    if incl_load or incl_soc or incl_cashflow:
        elements.append(PageBreak())
        
        if incl_load:
            elements.append(Paragraph("System Load Profiles Comparison", h2_style))
            load_img_buf = compile_matplotlib_load_chart(selected_profiles, get_df_for_name, custom_colors, base_limit)
            elements.append(Image(load_img_buf, width=480, height=200))
            elements.append(Spacer(1, 10))
            
        if incl_soc:
            soc_img_buf = compile_matplotlib_soc_chart(selected_profiles, get_df_for_name, linked_subs, custom_colors)
            if soc_img_buf:
                elements.append(Paragraph("BESS State of Charge (SoC)", h2_style))
                elements.append(Image(soc_img_buf, width=480, height=160))
                elements.append(Spacer(1, 10))
                
        if incl_cashflow:
            cash_img_buf = compile_matplotlib_cashflow_chart(selected_profiles, base_scenario, linked_subs, custom_colors)
            if cash_img_buf:
                if incl_load and incl_soc:
                    elements.append(PageBreak())
                elements.append(Paragraph("15-Year Cumulative Cashflow Comparison", h2_style))
                elements.append(Image(cash_img_buf, width=480, height=160))
                
    doc.build(elements)
    overlay_buffer.seek(0)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(os.path.dirname(current_dir)) 
    template_path = os.path.join(base_dir, "Documents", "Template.pdf")
    
    return merge_with_template(overlay_buffer, template_path)

def render_comparison_pdf_downloader(base_scenario, selected_profiles, linked_subs):
    """
    Renders the Streamlit PDF report configurator accordion box.
    """
    st.write("")
    with st.expander("📥 Professional PDF Report Configurator", expanded=False):
        st.write("Configure and compile a custom PDF analysis report for your client.")
        
        col1, col2 = st.columns(2)
        rep_title = col1.text_input("Report Title:", value="Energy System Optimization Report", key="pdf_rep_title")
        rep_client = col2.text_input("Client / Project Reference:", value=base_scenario.name, key="pdf_rep_client")
        
        rep_desc = st.text_area("Executive Summary / Custom Remarks:", 
                                value="This comprehensive comparison evaluates the technical feasibility and long-term financial feasibility of the proposed PV, battery storage, and generator configurations.", 
                                height=100, key="pdf_rep_desc")
        
        st.write("Select visual charts to include:")
        incl_table = st.checkbox("Include Technical Comparison Table", value=True, key="pdf_incl_table")
        incl_load = st.checkbox("Include Combined Load Profiles Chart", value=True, key="pdf_incl_load")
        incl_soc = st.checkbox("Include Battery State of Charge (SoC) Chart", value=True, key="pdf_incl_soc")
        incl_cashflow = st.checkbox("Include Cumulative Cashflow Chart", value=True, key="pdf_incl_cashflow")
        
        st.write("Customize scenario colors in PDF charts:")
        custom_colors = {}
        c_cols = st.columns(min(max(len(selected_profiles), 1), 4))
        for idx, name in enumerate(selected_profiles):
            col_picker_key = f"pdf_col_{name.replace(' ', '_')}"
            color_palette = ["#333333", "#00CC96", "#636EFA", "#FFA15A", "#AB63FA", "#FFC107", "#8B0000"]
            default_hex = color_palette[idx % len(color_palette)]
            custom_colors[name] = c_cols[idx % len(c_cols)].color_picker(f"{name}:", value=default_hex, key=col_picker_key)
            
        if st.button("🚀 Compile PDF Report", type="primary", use_container_width=True, key="pdf_btn_compile"):
            with st.spinner("Generating Matplotlib curves and compiling PDF layout..."):
                try:
                    pdf_data = compile_report_pdf(
                        base_scenario, selected_profiles, linked_subs,
                        rep_title, rep_client, rep_desc,
                        incl_table, incl_load, incl_soc, incl_cashflow, custom_colors
                    )
                    if pdf_data:
                        st.session_state['compiled_pdf_bytes'] = pdf_data.getvalue()
                        st.success("PDF Report compiled successfully! Click the button below to download.")
                except Exception as e:
                    st.error(f"Failed to generate PDF: {e}")
                    
        if 'compiled_pdf_bytes' in st.session_state:
            st.download_button(
                label="📥 Download PDF Report",
                data=st.session_state['compiled_pdf_bytes'],
                file_name=f"Comparison_Report_{base_scenario.name}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="pdf_btn_download"
            )
