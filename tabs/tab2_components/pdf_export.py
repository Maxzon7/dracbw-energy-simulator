# tabs/tab2_components/pdf_export.py
import base64
import io
import datetime
from weasyprint import HTML
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def create_static_load_chart(df, grid_limit):
    """
    Generates a static load profile chart using Matplotlib.
    Ensures stable cloud rendering without Kaleido dependencies.
    """
    fig, ax = plt.subplots(figsize=(8, 3.5))
    
    # Plot raw consumption
    ax.plot(df['timestamp'], df['consumption_kw'], label='Original Load (Baseline)', color='#A9A9A9', linewidth=1)
    
    # Plot optimized load if battery simulation was active
    if 'final_grid_load_kw' in df.columns:
        ax.plot(df['timestamp'], df['final_grid_load_kw'], label='Optimized Grid Load', color='#00CC96', linewidth=1.5)
    
    # Plot grid limit
    ax.axhline(y=grid_limit, color='red', linestyle='--', label='Grid Limit')
    
    ax.set_ylabel('Power (kW)')
    ax.legend(loc='upper right', fontsize='small')
    ax.grid(True, linestyle=':', alpha=0.5)
    
    # Format X-Axis nicely
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m. %H:%M'))
    plt.xticks(rotation=30)
    plt.tight_layout()
    
    # Save to memory buffer and encode
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150)
    plt.close(fig)
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.read()).decode('utf-8')

def create_static_soc_chart(df):
    """
    Generates a static State of Charge (SoC) chart.
    """
    fig, ax = plt.subplots(figsize=(8, 2.5))
    
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
    return base64.b64encode(img_buffer.read()).decode('utf-8')

def generate_tech_pdf(report_title: str, metrics: dict, plot_data, battery_enabled: bool) -> io.BytesIO:
    """
    Generates a highly professional PDF report incorporating DRACBV company branding.
    """
    current_date = datetime.date.today().strftime("%d.%m.%Y")
    
    # Generate charts from data
    load_img_base64 = create_static_load_chart(plot_data, metrics['grid_limit'])
    
    soc_html = ""
    if battery_enabled and 'battery_soc_kwh' in plot_data.columns:
        soc_img_base64 = create_static_soc_chart(plot_data)
        soc_html = f"""
        <div class="section-title" style="page-break-before: always;">3. Battery State of Charge (SoC)</div>
        <div class="chart-container">
            <img src="data:image/png;base64,{soc_img_base64}" class="chart">
        </div>
        """
    
    # DRACBV Corporate Design HTML
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @page {{ 
            size: A4; 
            margin: 20mm 20mm 30mm 20mm; 
            @bottom-center {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 8pt;
                color: #7f8c8d;
            }}
        }}
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #2c3e50; line-height: 1.6; }}
        
        /* HEADER */
        .header-table {{ width: 100%; border-bottom: 3px solid #27ae60; padding-bottom: 10px; margin-bottom: 30px; }}
        .header-left {{ text-align: left; font-size: 8pt; color: #555; line-height: 1.3; }}
        .header-right {{ text-align: right; font-size: 20pt; font-weight: bold; color: #2c3e50; vertical-align: top; }}
        .green-text {{ color: #27ae60; }}
        
        /* TYPOGRAPHY */
        .title {{ font-size: 20pt; font-weight: bold; color: #2c3e50; margin-bottom: 5px; text-transform: uppercase; }}
        .subtitle {{ font-size: 11pt; color: #7f8c8d; margin-bottom: 30px; }}
        .section-title {{ font-size: 13pt; font-weight: bold; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; margin-top: 30px; margin-bottom: 15px; color: #27ae60; }}
        
        /* CONTENT BLOCKS */
        .summary-box {{ background-color: #f9f9f9; border-left: 4px solid #27ae60; padding: 15px; margin-bottom: 25px; font-size: 10pt; }}
        table.metrics {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 10pt; }}
        table.metrics th, table.metrics td {{ text-align: left; padding: 10px; border-bottom: 1px solid #ecf0f1; }}
        table.metrics th {{ background-color: #fcfcfc; font-weight: bold; color: #34495e; width: 60%; }}
        
        /* CHARTS */
        .chart-container {{ text-align: center; margin-top: 15px; }}
        .chart {{ max-width: 100%; height: auto; border: 1px solid #ecf0f1; border-radius: 4px; padding: 5px; }}
        
        /* FOOTER */
        .footer {{ position: fixed; bottom: -20mm; left: 0; right: 0; height: 15mm; font-size: 7.5pt; color: #7f8c8d; border-top: 1px solid #ecf0f1; padding-top: 5mm; }}
        .footer-table {{ width: 100%; }}
        .footer-table td {{ text-align: left; vertical-align: top; width: 33%; line-height: 1.4; }}
    </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td class="header-left">
                    <strong>DRACBV Green Energy Solutions</strong><br>
                    Oud-Loosdrechtsedijk 254<br>
                    1231 NJ Loosdrecht<br>
                    +31 (0)20 213 77 70<br>
                    projecten@dracbv.nl | www.dracbv.nl
                </td>
                <td class="header-right">
                    <span class="green-text">DRAC</span>BV
                </td>
            </tr>
        </table>

        <div class="title">Energy Simulation & System Analysis</div>
        <div class="subtitle">Scenario: <strong>{report_title}</strong> | Analysis Date: {current_date}</div>

        <div class="summary-box">
            <strong>Management Summary:</strong><br>
            This technical report evaluates the load profile and simulates hardware-assisted optimizations (such as a Battery Energy Storage System or PV integration) to maintain the defined grid connection limit of <strong>{metrics['grid_limit']:.1f} kW</strong> and execute peak shaving.
        </div>

        <div class="section-title">1. Technical Specifications & Metrics</div>
        <table class="metrics">
            <tr><th>Parameter</th><th>Calculated Value</th></tr>
            <tr><td>Original Peak Load (Baseline)</td><td>{metrics['peak_raw']:.2f} kW</td></tr>
            <tr><td>Target Grid Limit</td><td>{metrics['grid_limit']:.2f} kW</td></tr>
            <tr><td>Required Inverter Power (Minimum)</td><td><strong>{metrics['min_pwr']:.2f} kW</strong></td></tr>
            <tr><td>Required Net Storage Capacity (Minimum)</td><td><strong>{metrics['min_cap']:.2f} kWh</strong></td></tr>
        </table>
        
        <div class="section-title">2. Load Profile Visualization</div>
        <div class="chart-container">
            <img src="data:image/png;base64,{load_img_base64}" class="chart">
        </div>
        
        {soc_html}

        <div class="footer">
            <table class="footer-table">
                <tr>
                    <td><strong>DRACBV Green Energy Solutions</strong><br>Oud-Loosdrechtsedijk 254<br>1231 NJ Loosdrecht</td>
                    <td><strong>Contact</strong><br>+31 (0)20 213 77 70<br>projecten@dracbv.nl</td>
                    <td><strong>Legal</strong><br>IBAN: NL98 INGB 0709 4878 78<br>BTW: NL864308024B01<br>KVK: 87487500</td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """
    
    pdf_buffer = io.BytesIO()
    HTML(string=html_template).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer