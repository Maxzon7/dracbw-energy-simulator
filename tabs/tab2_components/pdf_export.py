# tabs/tab2_components/pdf_export.py
import io
import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter

def create_static_load_chart(df, grid_limit):
    """
    Generates a static load profile chart using Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(7, 3)) # Slightly adjusted for A4 fit
    
    ax.plot(df['timestamp'], df['consumption_kw'], label='Original Load (Baseline)', color='#A9A9A9', linewidth=1)
    
    if 'final_grid_load_kw' in df.columns:
        ax.plot(df['timestamp'], df['final_grid_load_kw'], label='Optimized Grid Load', color='#00CC96', linewidth=1.5)
    
    ax.axhline(y=grid_limit, color='red', linestyle='--', label='Grid Limit')
    
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize='small')
    ax.grid(True, linestyle=':', alpha=0.5)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H:%M'))
    plt.xticks(rotation=30)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def create_static_soc_chart(df):
    """
    Generates a static State of Charge (SoC) chart.
    """
    fig, ax = plt.subplots(figsize=(7, 2.5))
    
    ax.fill_between(df['timestamp'], df['battery_soc_kwh'], color='#636EFA', alpha=0.3)
    ax.plot(df['timestamp'], df['battery_soc_kwh'], color='#636EFA', linewidth=1.5)
    
    ax.set_ylabel('State of Charge (kWh)')
    ax.grid(True, linestyle=':', alpha=0.5)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H:%M'))
    plt.xticks(rotation=30)
    plt.tight_layout()
    
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150)
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def generate_tech_pdf(report_title: str, metrics: dict, plot_data, battery_enabled: bool) -> io.BytesIO:
    """
    Generates a professional PDF report by overlaying technical data 
    onto the official DRACBV Template.pdf watermark.
    """
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    
    # ---------------------------------------------------------
    # 1. CREATE TRANSPARENT OVERLAY (The "Glass Pane")
    # ---------------------------------------------------------
    overlay_buffer = io.BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=A4)
    
    # ReportLab coordinates start at bottom-left (x=0, y=0). 
    # Top of A4 is approx y=840. We start writing below the letterhead.
    
    # Title & Meta (y=700 leaves space for your company header)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.17, 0.24, 0.31) # Dark Slate
    c.drawString(50, 700, "Energy Simulation & System Analysis")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.5, 0.55, 0.55) # Gray
    c.drawString(50, 680, f"Scenario: {report_title} | Analysis Date: {current_date}")
    
    # Summary Box
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.15, 0.68, 0.37) # DRACBV Green
    c.drawString(50, 640, "Management Summary:")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.17, 0.24, 0.31)
    summary_text = (f"This technical report evaluates the load profile and simulates hardware optimizations to "
                    f"maintain the grid limit of {metrics['grid_limit']:.1f} kW.")
    c.drawString(50, 625, summary_text)
    
    # Technical Metrics
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.15, 0.68, 0.37)
    c.drawString(50, 580, "1. Technical Specifications & Metrics")
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.17, 0.24, 0.31)
    c.drawString(50, 560, f"Original Peak Load (Baseline): {metrics['peak_raw']:.2f} kW")
    c.drawString(50, 545, f"Target Grid Limit: {metrics['grid_limit']:.2f} kW")
    
    # Highlight required hardware
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, 530, f"Required Inverter Power (Minimum): {metrics['min_pwr']:.2f} kW")
    c.drawString(50, 515, f"Required Net Storage Capacity (Minimum): {metrics['min_cap']:.2f} kWh")
    
    # Load Profile Chart
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(0.15, 0.68, 0.37)
    c.drawString(50, 470, "2. Load Profile Visualization")
    
    load_img = create_static_load_chart(plot_data, metrics['grid_limit'])
    c.drawImage(ImageReader(load_img), x=40, y=250, width=500, height=210)
    
    # Battery SoC Chart (if enabled)
    if battery_enabled and 'battery_soc_kwh' in plot_data.columns:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 220, "3. Battery State of Charge (SoC)")
        soc_img = create_static_soc_chart(plot_data)
        c.drawImage(ImageReader(soc_img), x=40, y=40, width=500, height=170)
    
    c.save()
    overlay_buffer.seek(0)
    
    # ---------------------------------------------------------
    # 2. MERGE OVERLAY WITH DRACBV TEMPLATE
    # ---------------------------------------------------------
    # Get the absolute path to MVP3/Documents/Template.pdf
    current_dir = os.path.dirname(os.path.abspath(__file__)) # is in tab2_components
    base_dir = os.path.dirname(os.path.dirname(current_dir)) # Up to MVP3 root
    template_path = os.path.join(base_dir, "Documents", "Template.pdf")
    
    # If the template cannot be found for some reason, return just the overlay
    if not os.path.exists(template_path):
        return overlay_buffer
        
    overlay_pdf = PdfReader(overlay_buffer)
    background_pdf = PdfReader(open(template_path, "rb"))
    output = PdfWriter()
    
    # We grab the first page of your Template.pdf
    bg_page = background_pdf.pages[0]
    overlay_page = overlay_pdf.pages[0]
    
    # Stamp the transparent overlay onto the background
    bg_page.merge_page(overlay_page)
    output.add_page(bg_page)
    
    final_output = io.BytesIO()
    output.write(final_output)
    final_output.seek(0)
    
    return final_output