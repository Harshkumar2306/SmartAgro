import streamlit as st
import numpy as np
import rasterio
from rasterio.io import MemoryFile
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import base64
from io import BytesIO

# Initialize custom CSS
st.set_page_config(page_title="NDVI Precision Agriculture", layout="wide", page_icon="🌾")

st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main .block-container{
        padding-top: 2rem;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-title {
        color: #6c757d;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

from ndvi import calculate_ndvi
from stress_detection import analyze_crop_health
from yield_prediction import estimate_yield
from recommendations import get_agricultural_recommendation, INDIAN_STATES_AGRI_DATA

def load_data(file):
    """Reads image content from a file-like object using rasterio MemoryFile."""
    with MemoryFile(file) as memfile:
        with memfile.open() as src:
            data = src.read(1)
            return data.astype(np.float32)

def display_results(ndvi_matrix, stats, yield_result):
    st.markdown("---")
    st.header("📊 Precision Agriculture Dashboard")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-title">Healthy Vegetation (>0.6)</div>
                <div class="metric-value" style="color: #4CAF50;">{stats["healthy_pct"]:.1f}%</div>
            </div>
        ''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-title">Moderate Vegetation (0.3-0.6)</div>
                <div class="metric-value" style="color: #FFC107;">{stats["moderate_pct"]:.1f}%</div>
            </div>
        ''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''
            <div class="metric-card">
                <div class="metric-title">Stressed Vegetation (<0.3)</div>
                <div class="metric-value" style="color: #F44336;">{stats["stressed_pct"]:.1f}%</div>
            </div>
        ''', unsafe_allow_html=True)

    text, emoji, color = yield_result
    st.markdown(f'''
        <div class="metric-card" style="border-left: 5px solid {color};">
            <div class="metric-title">Estimated Crop Yield</div>
            <div class="metric-value"> {text} {emoji}</div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("### 🗺️ Geographical Mapping")
    map_col1, map_col2 = st.columns(2)
    
    with map_col1:
        st.subheader("NDVI Map")
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(ndvi_matrix, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
        fig.colorbar(im, ax=ax, label='NDVI Value')
        ax.axis('off')
        st.pyplot(fig)
        
    with map_col2:
        st.subheader("Stress Classification Overlay")
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        colors = ['#808080', '#FF0000', '#FFFF00', '#008000']
        cmap_custom = ListedColormap(colors)
        im2 = ax2.imshow(stats['class_matrix'], cmap=cmap_custom, vmin=-0.5, vmax=3.5)
        cbar = fig2.colorbar(im2, ax=ax2, ticks=[0, 1, 2, 3])
        cbar.ax.set_yticklabels(['Non-Vegetation', 'Stressed', 'Moderate', 'Healthy'])
        ax2.axis('off')
        st.pyplot(fig2)
        
    st.markdown("### 📈 Advanced Visualization")
    chart_col1, chart_col2, chart_col3 = st.columns(3)
    
    with chart_col1:
        st.subheader("Health Distribution")
        fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
        labels = ['Healthy', 'Moderate', 'Stressed']
        sizes = [stats['healthy_pct'], stats['moderate_pct'], stats['stressed_pct']]
        colors_pie = ['#4CAF50', '#FFC107', '#F44336']
        ax_pie.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%', startangle=90)
        ax_pie.axis('equal')
        st.pyplot(fig_pie)
        
    with chart_col2:
        st.subheader("Pixel Classification Bar")
        fig_bar, ax_bar = plt.subplots(figsize=(5, 5))
        ax_bar.bar(labels, sizes, color=colors_pie)
        ax_bar.set_ylabel('Percentage (%)')
        st.pyplot(fig_bar)
        
    with chart_col3:
        st.subheader("NDVI Histogram")
        fig_hist, ax_hist = plt.subplots(figsize=(5, 5))
        ax_hist.hist(ndvi_matrix.ravel(), bins=50, color='teal', alpha=0.7)
        ax_hist.set_xlabel('NDVI')
        ax_hist.set_ylabel('Frequency')
        ax_hist.set_xlim([-1, 1])
        st.pyplot(fig_hist)
        
    st.markdown("### 💡 Data-Driven Agricultural Action Plan")
    suggestion = get_agricultural_recommendation(stats['healthy_pct'], stats['moderate_pct'], stats['stressed_pct'])
    if stats['healthy_pct'] > 70 and stats['stressed_pct'] < 10:
        st.success(f"**Recommendation:** {suggestion}")
    elif stats['stressed_pct'] > 30:
        st.error(f"**Recommendation:** {suggestion}")
    else:
        st.warning(f"**Recommendation:** {suggestion}")

def main():
    st.title("🌾 Region-Based NDVI Precision Agriculture System")
    st.subheader("Satellite Imagery Analysis for Crop Monitoring & Yield Prediction")
    
    st.sidebar.title("Navigation")
    menu = st.sidebar.radio("Go to", ["Upload Data & NDVI Analysis", "Crop & Soil Info"])
    
    if menu == "Upload Data & NDVI Analysis":
        st.markdown("### 🛰️ Upload Sentinel-2 Bands (GeoTIFF)")
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            b04_file = st.file_uploader("Upload B04 (Red Band)", type=['tif', 'tiff'])
        with col_up2:
            b08_file = st.file_uploader("Upload B08 (NIR Band)", type=['tif', 'tiff'])
            
        if b04_file is not None and b08_file is not None:
            if st.button("🚀 Analyze Data"):
                with st.spinner("Processing satellite imagery... Please wait."):
                    try:
                        red_band = load_data(b04_file)
                        nir_band = load_data(b08_file)
                        
                        if red_band.shape != nir_band.shape:
                            st.error("Uploaded images must have the same dimensions!")
                        else:
                            st.success("Images loaded successfully!")
                            ndvi_matrix = calculate_ndvi(red_band, nir_band)
                            stats = analyze_crop_health(ndvi_matrix)
                            yield_result = estimate_yield(stats['healthy_pct'])
                            
                            display_results(ndvi_matrix, stats, yield_result)
                    except Exception as e:
                        st.error(f"Error processing files: {e}")
                        
    elif menu == "Crop & Soil Info":
        st.markdown("### 🇮🇳 Region-Based Agricultural Information")
        st.write("Explore state-specific crop guidelines and soil data for precision farming.")
        
        state_list = list(INDIAN_STATES_AGRI_DATA.keys())
        selected_state = st.selectbox("Select Indian State", state_list)
        
        if selected_state:
            data = INDIAN_STATES_AGRI_DATA[selected_state]
            st.markdown(f'''
            <div class="metric-card" style="text-align: left; padding: 30px;">
                <h3 style="color: #4CAF50;">{selected_state}</h3>
                <hr>
                <p><b>🌱 Soil Type:</b> {data["soil_type"]}</p>
                <p><b>🌾 Major Crops Grown:</b> {data["major_crops"]}</p>
                <p><b>🌟 Suitable Crops:</b> {data["suitable_crops"]}</p>
                <p><b>🌦️ Crop Requirements:</b> {data["requirements"]}</p>
            </div>
            ''', unsafe_allow_html=True)
            
if __name__ == "__main__":
    main()
