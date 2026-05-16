from fpdf import FPDF
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import tempfile
import os
import numpy as np

def create_pdf_report(rgb_matrix, ndvi_matrix, ndwi_matrix, savi_matrix, stats, yield_text, suggestion, weather_data, months, history):
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("helvetica", 'B', 20)
    pdf.cell(0, 15, "Advanced Precision Agriculture Report", ln=True, align='C')
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, "Multi-Spectral & Micro-Climate Intelligence", ln=True, align='C')
    pdf.ln(5)
    
    # Weather
    if weather_data:
        pdf.set_font("helvetica", 'B', 14)
        pdf.cell(0, 10, "1. Live Micro-Climate", ln=True)
        pdf.set_font("helvetica", size=12)
        weather_str = f"Temp: {weather_data.get('temperature_2m', '--')}C | Humidity: {weather_data.get('relative_humidity_2m', '--')}% | Rain: {weather_data.get('precipitation', '--')}mm | Wind: {weather_data.get('wind_speed_10m', '--')}km/h"
        pdf.cell(0, 8, weather_str, ln=True)
        pdf.ln(5)
        
    # Stats
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "2. Crop Vitality Metrics", ln=True)
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 8, f"Healthy (NDVI > 0.6): {stats['healthy_pct']:.1f}%", ln=True)
    pdf.cell(0, 8, f"Moderate (NDVI 0.3-0.6): {stats['moderate_pct']:.1f}%", ln=True)
    pdf.cell(0, 8, f"Stressed (NDVI < 0.3): {stats['stressed_pct']:.1f}%", ln=True)
    ndwi_mean = np.nanmean(ndwi_matrix)
    pdf.cell(0, 8, f"Mean NDWI (Moisture): {ndwi_mean:.2f}", ln=True)
    pdf.ln(5)
    
    # Yield
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "3. ML Yield Prediction", ln=True)
    pdf.set_font("helvetica", size=12)
    
    # Handle emoji stripping (MT/ha bounds)
    yield_parts = yield_text.split(' ')
    clean_yield = f"{yield_parts[0]} {yield_parts[1]}"
    if len(yield_parts) > 2:
        clean_yield += f" {yield_parts[2]}"

    pdf.cell(0, 8, f"Predicted Yield: {clean_yield}", ln=True)
    pdf.ln(5)
    
    # Action Plan
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "4. AI Data-Driven Action Plan", ln=True)
    pdf.set_font("helvetica", size=12)
    clean_suggestion = suggestion.encode("latin-1", "ignore").decode("latin-1")
    pdf.multi_cell(0, 8, clean_suggestion)
    pdf.ln(10)
    
    # Visualizations
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 14)
    pdf.cell(0, 10, "5. Geospatial & Time-Series Analytics", ln=True)
    pdf.ln(5)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Avoid thread state bugs in Streamlit by using explicit figure objects, and save as JPG to avoid FPDF PNG Transparency bugs!
        
        # Save RGB
        rgb_path = os.path.join(tmpdir, "rgb.jpg")
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.imshow(rgb_matrix, interpolation='bicubic')
        ax.set_title("True Color Satellite")
        ax.axis('off')
        fig.savefig(rgb_path, bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
        plt.close(fig)
        
        # Save NDVI
        ndvi_path = os.path.join(tmpdir, "ndvi.jpg")
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.imshow(ndvi_matrix, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='bicubic')
        ax.set_title("NDVI (Vigor)")
        ax.axis('off')
        fig.savefig(ndvi_path, bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
        plt.close(fig)
        
        # Save NDWI
        ndwi_path = os.path.join(tmpdir, "ndwi.jpg")
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.imshow(ndwi_matrix, cmap='BrBG', vmin=-1.0, vmax=1.0, interpolation='bicubic')
        ax.set_title("NDWI (Moisture)")
        ax.axis('off')
        fig.savefig(ndwi_path, bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
        plt.close(fig)
        
        # Save SAVI
        savi_path = os.path.join(tmpdir, "savi.jpg")
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.imshow(savi_matrix, cmap='summer', vmin=-0.2, vmax=1.0, interpolation='bicubic')
        ax.set_title("SAVI (Soil Adjusted)")
        ax.axis('off')
        fig.savefig(savi_path, bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
        plt.close(fig)
        
        # Save Time Series
        ts_path = os.path.join(tmpdir, "ts.jpg")
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(months, history, marker='o', linestyle='-', color='#4CAF50', linewidth=2)
        ax.fill_between(months, history, color='#4CAF50', alpha=0.2)
        ax.set_title("6-Month NDVI Trajectory")
        ax.grid(True, linestyle='--', alpha=0.6)
        fig.savefig(ts_path, bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
        plt.close(fig)
        
        y_pos = pdf.get_y()
        # Row 1 Max 2x2 grid fits best
        pdf.image(rgb_path, x=10, y=y_pos, w=90)
        pdf.image(ndvi_path, x=110, y=y_pos, w=90)
        
        # Row 2
        pdf.set_y(y_pos + 70)
        pdf.image(ndwi_path, x=10, y=pdf.get_y(), w=90)
        pdf.image(savi_path, x=110, y=pdf.get_y(), w=90)
        
        # Row 3 (Time Series spanning width)
        pdf.set_y(pdf.get_y() + 70)
        pdf.image(ts_path, x=10, y=pdf.get_y(), w=180)
        
    return bytes(pdf.output())
