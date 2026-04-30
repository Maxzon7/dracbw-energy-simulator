# functions/pdf_converter.py
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
    ax.plot(df['timestamp'], df['consumption_kw'], label='Raw Load', color='#A9A9A9', linewidth=1)
    
    # Plot optimized load if battery simulation was active
    if 'final_grid_load_kw' in df.columns:
        ax.plot(df['timestamp'], df['final_grid_load_kw'], label='Optimized Load', color='#00CC96', linewidth=1.5)
    
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
    
    ax.set_ylabel('SoC (kWh)')
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
    Generates a technical PDF report containing the project summary, metrics, 
    and static Matplotlib charts.
    """
    current_date = datetime.date.today().strftime("%d.%m.%Y")
    
    # Generate charts from data
    load_img_base64 = create_static_load_chart(plot_data, metrics['grid_limit'])
    
    soc_html = ""
    if battery_enabled and 'battery_soc_kwh' in plot_data.columns:
        soc_img_base64 = create_static_soc_chart(plot_data)
        soc_html = f"""
        <h2>Battery State of Charge (SoC)</h2>
        <img src="data:image/png;base64,{soc_img_base64}" class="chart">
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @page {{ size: A4; margin: 20mm; background-color: #ffffff; }}
        body {{ font-family: Arial, sans-serif; color: #333; line-height: 1.5; }}
        .header {{ border-bottom: 2px solid #1a5276; padding-bottom: 10px; margin-bottom: 20px; }}
        .brand {{ float: right; font-size: 22pt; font-weight: bold; color: #1a5276; }}
        .title {{ font-size: 18pt; font-weight: bold; }}
        .summary {{ background: #f4f6f7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-size: 10pt; text-transform: uppercase; }}
        .chart {{ width: 100%; margin-top: 20px; border: 1px solid #eee; }}
        .footer {{ position: fixed; bottom: 0; width: 100%; font-size: 8pt; color: #999; text-align: center; }}
    </style>
    </head>
    <body>
        <div class="header">
            <div class="brand">DracBW</div>
            <div class="title">{report_title}</div>
            <p>Analysis Date: {current_date}</p>
        </div>

        <div class="summary">
            <strong>Executive Technical Summary:</strong><br>
            This report evaluates the energy consumption profile and simulates a Battery Energy Storage System (BESS) 
            to maintain a grid limit of {metrics['grid_limit']} kW.
        </div>

        <h2>Technical Requirements</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Original Peak Load</td><td>{metrics['peak_raw']:.2f} kW</td></tr>
            <tr><td>Target Grid Limit</td><td>{metrics['grid_limit']:.2f} kW</td></tr>
            <tr><td>Required BESS Power (Inverter)</td><td>{metrics['min_pwr']:.2f} kW</td></tr>
            <tr><td>Required BESS Capacity (Storage)</td><td>{metrics['min_cap']:.2f} kWh</td></tr>
        </table>
        
        <h2>Load Profile Visualization</h2>
        <img src="data:image/png;base64,{load_img_base64}" class="chart">
        
        {soc_html}

        <div class="footer">Generated by DracBW Energy Simulator</div>
    </body>
    </html>
    """
    
    pdf_buffer = io.BytesIO()
    HTML(string=html_template).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer