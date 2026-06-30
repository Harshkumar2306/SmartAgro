import streamlit as st
import ee
import geemap
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import rasterio
import ssl
import certifi

# Fix Mac OS SSL Certificate errors globally
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(page_title="Area Selection GEE Fetcher", layout="wide", page_icon="🗺️")

st.title("🗺️ Interactive Area Selection & Analysis (Google Earth Engine)")
st.info("**Project Objective:** The main objective of this project is to use satellite imagery and NDVI to monitor crop health, detect stress regions, and predict crop yield, enabling data-driven decisions in precision agriculture.")
st.markdown("""
Draw a **polygon** or **rectangle** on the map below. 
The system will capture your exact drawn boundary, fetch real Sentinel-2 satellite data intersecting it, compute NDVI on Google Earth Engine, and export the precise cropped area to a GeoTIFF. Finally, it natively analyzes that exact downloaded GeoTIFF to give you regional insights.
""")

from stress_detection import analyze_crop_health
from yield_prediction import estimate_yield
from recommendations import get_agricultural_recommendation

try: # Auth check
    ee.Initialize()
except Exception as e:
    st.error("Google Earth Engine is not initialized! Please run `earthengine authenticate`.")
    st.stop()

col_map, col_dash = st.columns([1.2, 1])

with col_map:
    st.subheader("1. Draw an Area")
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=4)
    
    # Add drawing tools
    draw = Draw(
        draw_options={
            'polyline': False,
            'polygon': True,
            'rectangle': True,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': False}
    )
    draw.add_to(m)
    
    # Render map
    map_data = st_folium(m, height=500, width="100%", returned_objects=["all_drawings"])

with col_dash:
    st.subheader("2. Analyze Selected Area")
    
    if map_data and map_data.get('all_drawings') and len(map_data['all_drawings']) > 0:
        latest_drawing = map_data['all_drawings'][-1]
        geom_geojson = latest_drawing['geometry']
        
        st.success("✅ Area successfully captured from map!")
        
        if st.button("Fetch Satellite Data & Download TIF"):
            with st.spinner("Connecting to Earth Engine & Processing..."):
                try:
                    # Create GEE Geometry from GeoJSON
                    ee_geom = ee.Geometry(geom_geojson)
                    
                    # Compute area for display
                    area_sqkm = ee_geom.area().divide(1e6).getInfo()
                    st.write(f"**Selected Area Size:** ~{area_sqkm:.2f} km²")
                    
                    if area_sqkm > 1000:
                        st.warning("You selected a massive area. Exporting might take a very long time. Consider drawing a smaller region.")
                        
                    end_date = datetime.datetime.now()
                    start_date = end_date - datetime.timedelta(days=365)
                    
                    # Fetch and filter
                    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                  .filterBounds(ee_geom)
                                  .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                                  .sort('CLOUDY_PIXEL_PERCENTAGE'))
                    
                    image = collection.first()
                    
                    if image is None:
                        st.error("No valid low-cloud images found for this area in the last year.")
                    else:
                        st.write(f"✅ Found Image: **{image.date().format('YYYY-MM-dd').getInfo()}**")
                        
                        # Compute NDVI
                        nir = image.select('B8')
                        red = image.select('B4')
                        green = image.select('B3')
                        
                        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
                        
                        # Fix for Water: Compute NDWI (Normalized Difference Water Index)
                        # Water heavily reflects green and absorbs NIR. NDWI > 0 usually indicates water.
                        ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
                        
                        # Where NDWI > 0 (it is water), force the NDVI to be -1 (Non-Vegetation)
                        ndvi = ndvi.where(ndwi.gt(0), -1)
                        
                        # Extract True Color RGB
                        rgb = image.select(['B4', 'B3', 'B2'])
                        
                        # Clip to the drawn polygon
                        ndvi_clipped = ndvi.clip(ee_geom)
                        rgb_clipped = rgb.clip(ee_geom)
                        
                        # Check local directory structure
                        out_dir = os.path.dirname(os.path.abspath(__file__))
                        unique_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        out_file_ndvi = os.path.join(out_dir, f'Area_NDVI_Clip_{unique_id}.tif')
                        out_file_rgb = os.path.join(out_dir, f'Area_RGB_Clip_{unique_id}.tif')
                        
                        st.warning("Exporting exact clipped area analysis from Earth Engine... Please wait.")
                        
                        # Export clipped area NDVI
                        geemap.ee_export_image(
                            ndvi_clipped,
                            filename=out_file_ndvi,
                            scale=10,
                            region=ee_geom,
                            file_per_band=False
                        )
                        
                        # Export clipped area RGB
                        geemap.ee_export_image(
                            rgb_clipped,
                            filename=out_file_rgb,
                            scale=10,
                            region=ee_geom,
                            file_per_band=False
                        )
                        
                        st.success(f"🎉 Process Complete! Satellite datasets successfully exported locally!")
                        st.code(f"Saved NDVI at:\\n{out_file_ndvi}\\nSaved RGB at:\\n{out_file_rgb}")
                        
                        st.markdown("---")
                        st.subheader("📊 Selected Area Analysis")
                        
                        # Read the exported matrices locally 
                        with rasterio.open(out_file_ndvi) as src:
                            ndvi_arr = src.read(1).astype(np.float32)
                            
                        # Read RGB and normalize for display
                        with rasterio.open(out_file_rgb) as src:
                            # Sentinel-2 B4,3,2 range is typically 0-10000. Clamp and scale to 0-1
                            r = src.read(1).astype(np.float32)
                            g = src.read(2).astype(np.float32)
                            b = src.read(3).astype(np.float32)
                            rgb_arr = np.dstack((r, g, b))
                            # Enhance brightness (scale by factor of 3)
                            rgb_arr = np.clip(rgb_arr / 3000.0, 0, 1)

                        # Ignore 0 padding outside polygon boundary during stats if needed, 
                        # but simple classification works
                        stats = analyze_crop_health(ndvi_arr)
                        
                        y_text, y_emoji, yield_color = estimate_yield(stats['healthy_pct'])
                        yield_text = f"{y_text} {y_emoji}"
                        
                        st.markdown("""
                        <style>
                            .metric-card {
                                background-color: #ffffff;
                                border-radius: 10px;
                                padding: 15px;
                                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                                text-align: center;
                                margin-bottom: 15px;
                            }
                            .metric-title { color: #6c757d; font-size: 1rem; font-weight: 600; }
                            .metric-value { font-size: 1.5rem; font-weight: 700; color: #2c3e50; }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        c1, c2, c3, c4 = st.columns(4)
                        c1.markdown(f'<div class="metric-card"><div class="metric-title">Healthy</div><div class="metric-value" style="color:#4CAF50">{stats["healthy_pct"]:.1f}%</div></div>', unsafe_allow_html=True)
                        c2.markdown(f'<div class="metric-card"><div class="metric-title">Moderate</div><div class="metric-value" style="color:#FFC107">{stats["moderate_pct"]:.1f}%</div></div>', unsafe_allow_html=True)
                        c3.markdown(f'<div class="metric-card"><div class="metric-title">Stressed</div><div class="metric-value" style="color:#F44336">{stats["stressed_pct"]:.1f}%</div></div>', unsafe_allow_html=True)
                        c4.markdown(f'<div class="metric-card" style="border-left: 5px solid {yield_color};"><div class="metric-title">Predicted Yield</div><div class="metric-value">{yield_text}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown("### 🗺️ Full Scale Geospatial Maps")
                        
                        map_col1, map_col2 = st.columns(2)
                        
                        with map_col1:
                            fig0, ax0 = plt.subplots(figsize=(10, 8))
                            ax0.imshow(rgb_arr, interpolation='bicubic')
                            ax0.set_title("1. True Color Satellite View", fontsize=14, fontweight='bold')
                            ax0.axis('off')
                            st.pyplot(fig0)
                            
                            fig2, ax2 = plt.subplots(figsize=(10, 8))
                            colors = ['#808080', '#FF0000', '#FFFF00', '#008000']
                            cmap_custom = ListedColormap(colors)
                            im2 = ax2.imshow(stats['class_matrix'], cmap=cmap_custom, vmin=-0.5, vmax=3.5, interpolation='nearest')
                            ax2.set_title("3. Stress Categorization Map", fontsize=14, fontweight='bold')
                            ax2.axis('off')
                            st.pyplot(fig2)
                            
                        with map_col2:
                            fig1, ax1 = plt.subplots(figsize=(10, 8))
                            im1 = ax1.imshow(ndvi_arr, cmap='RdYlGn', vmin=-0.2, vmax=1.0, interpolation='bicubic')
                            ax1.set_title("2. Continuous NDVI Heatmap", fontsize=14, fontweight='bold')
                            ax1.axis('off')
                            st.pyplot(fig1)
                            
                            fig3, ax3 = plt.subplots(figsize=(10, 8))
                            labels = ['Healthy', 'Moderate', 'Stressed']
                            sizes = [stats['healthy_pct'], stats['moderate_pct'], stats['stressed_pct']]
                            if sum(sizes) > 0:
                                ax3.pie(sizes, labels=labels, colors=['#4CAF50', '#FFC107', '#F44336'], autopct='%1.1f%%', startangle=90)
                            else:
                                ax3.text(0.5, 0.5, 'No Vegetation Detected', ha='center', va='center')
                            ax3.set_title("4. Crop Health Context", fontsize=14, fontweight='bold')
                            st.pyplot(fig3)
                            
                        st.markdown("### 💡 Data-Driven Agricultural Action Plan")
                        suggestion = get_agricultural_recommendation(stats['healthy_pct'], stats['moderate_pct'], stats['stressed_pct'])
                        if stats['healthy_pct'] > 70 and stats['stressed_pct'] < 10:
                            st.success(f"**Recommendation:** {suggestion}")
                        elif stats['stressed_pct'] > 30:
                            st.error(f"**Recommendation:** {suggestion}")
                        else:
                            st.warning(f"**Recommendation:** {suggestion}")
                            
                        # Add PDF Download Button
                        try:
                            from report_generator import create_pdf_report
                            pdf_bytes = create_pdf_report(rgb_arr, ndvi_arr, stats, yield_text, suggestion)
                            st.download_button(
                                label="📄 Download Report as PDF",
                                data=pdf_bytes,
                                file_name="GEE_Agri_Report.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"Could not generate PDF: {e}")
                        

                        
                except Exception as e:
                    st.error(f"API Error Occurred: {e}")
    else:
        st.info("Use the **Polygon ⬠** or **Rectangle ⬛** tool on the left map to draw the exact region you want to analyze.")
