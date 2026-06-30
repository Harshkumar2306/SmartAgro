import os
import io
import base64
import datetime
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import rasterio
from rasterio.io import MemoryFile
import requests
import pystac_client
import planetary_computer
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
from pydantic import BaseModel
import concurrent.futures
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds

from backend.ndvi import calculate_ndvi
from backend.stress_detection import analyze_crop_health
from backend.yield_prediction import estimate_yield
from backend.recommendations import get_agricultural_recommendation, INDIAN_STATES_AGRI_DATA
import math

app = FastAPI(title="Smart Agri API")

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fig_to_base64(fig):
    """Helper to convert matplotlib figure to base64 string"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', transparent=True)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def generate_maps(ndvi_matrix, class_matrix, rgb_matrix=None, ndwi_matrix=None, savi_matrix=None):
    """Generates base64 strings for the different map visualisations."""
    maps = {}
    
    # 1. NDVI Map
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(ndvi_matrix, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
    fig.colorbar(im, ax=ax, label='NDVI Value')
    ax.axis('off')
    maps['ndvi_map'] = fig_to_base64(fig)
    
    # 2. Stress Map
    fig2, ax2 = plt.subplots(figsize=(6, 5))
    colors = ['#808080', '#FF0000', '#FFFF00', '#008000']
    cmap_custom = ListedColormap(colors)
    im2 = ax2.imshow(class_matrix, cmap=cmap_custom, vmin=-0.5, vmax=3.5)
    cbar = fig2.colorbar(im2, ax=ax2, ticks=[0, 1, 2, 3])
    cbar.ax.set_yticklabels(['Non-Vegetation', 'Stressed', 'Moderate', 'Healthy'])
    ax2.axis('off')
    maps['stress_map'] = fig_to_base64(fig2)
    
    if rgb_matrix is not None:
        fig3, ax3 = plt.subplots(figsize=(6, 5))
        ax3.imshow(rgb_matrix)
        ax3.axis('off')
        maps['rgb_map'] = fig_to_base64(fig3)
        
    if ndwi_matrix is not None:
        fig4, ax4 = plt.subplots(figsize=(6, 5))
        im4 = ax4.imshow(ndwi_matrix, cmap='BrBG', vmin=-1.0, vmax=1.0)
        fig4.colorbar(im4, ax=ax4, label='NDWI Value')
        ax4.axis('off')
        maps['ndwi_map'] = fig_to_base64(fig4)
        
    if savi_matrix is not None:
        fig5, ax5 = plt.subplots(figsize=(6, 5))
        im5 = ax5.imshow(savi_matrix, cmap='YlGn', vmin=-0.2, vmax=1.0)
        fig5.colorbar(im5, ax=ax5, label='SAVI Value')
        ax5.axis('off')
        maps['savi_map'] = fig_to_base64(fig5)
        
    return maps

def load_data_from_bytes(file_bytes):
    with MemoryFile(file_bytes) as memfile:
        with memfile.open() as src:
            data = src.read(1)
            return data.astype(np.float32)

@app.post("/api/analyze-local")
async def analyze_local(b04: UploadFile = File(...), b08: UploadFile = File(...)):
    """Analyze local Sentinel-2 GeoTIFF bands."""
    try:
        b04_bytes = await b04.read()
        b08_bytes = await b08.read()
        
        red_band = load_data_from_bytes(b04_bytes)
        nir_band = load_data_from_bytes(b08_bytes)
        
        if red_band.shape != nir_band.shape:
            raise HTTPException(status_code=400, detail="Images must have the same dimensions.")
            
        ndvi_matrix = calculate_ndvi(red_band, nir_band)
        stats = analyze_crop_health(ndvi_matrix)
        
        y_text, y_emoji, yield_color = estimate_yield(stats['healthy_pct'])
        suggestion = get_agricultural_recommendation(stats['healthy_pct'], stats['moderate_pct'], stats['stressed_pct'])
        
        maps = generate_maps(ndvi_matrix, stats['class_matrix'])
        
        # Remove numpy array from stats before sending
        stats.pop('class_matrix')
        
        return {
            "stats": stats,
            "yield": {"text": y_text, "emoji": y_emoji, "color": yield_color},
            "recommendation": suggestion,
            "maps": maps
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AreaRequest(BaseModel):
    bbox: list[float] # [min_lon, min_lat, max_lon, max_lat]

# Re-use Planetary Computer logic
def get_planetary_data(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=120)
    time_range = f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"

    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=[min_lon, min_lat, max_lon, max_lat],
        datetime=time_range,
        query={"eo:cloud_cover": {"lt": 20}},
        sortby=[{"field": "eo:cloud_cover", "direction": "asc"}],
        max_items=3, # Restored for Hugging Face 16GB RAM limit
    )

    all_items = list(search.items())
    if not all_items:
        raise ValueError("No cloud-free Sentinel-2 imagery found.")

    image_date = all_items[0].datetime.strftime("%Y-%m-%d") if all_items[0].datetime else "Unknown"
    
    # High-Resolution (256x256) restored!
    target_size = 256
    red_canvas = np.zeros((target_size, target_size), dtype=np.float32)
    nir_canvas = np.zeros((target_size, target_size), dtype=np.float32)
    green_canvas = np.zeros((target_size, target_size), dtype=np.float32)
    blue_canvas = np.zeros((target_size, target_size), dtype=np.float32)
    bbox_4326 = [min_lon, min_lat, max_lon, max_lat]
    
    import gc

    def process_band(item, band_name, canvas):
        if band_name not in item.assets: return 0.0
        href = item.assets[band_name].href
        try:
            # Memory unlocked for Hugging Face Spaces (16GB RAM)
            env = rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", 
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff", 
                VSI_CACHE=True, 
                GDAL_HTTP_MULTIMAC="YES", 
                GDAL_HTTP_MERGE_CONSECUTIVE_READS="YES"
            )
            with env, rasterio.open(href) as src:
                src_bounds = transform_bounds("EPSG:4326", src.crs, *bbox_4326)
                window = from_bounds(*src_bounds, transform=src.transform)
                from rasterio.enums import Resampling
                # Professional interpolation (bilinear) instead of nearest
                data = src.read(1, window=window, boundless=True, fill_value=0, out_shape=(target_size, target_size), resampling=Resampling.bilinear).astype(np.float32)
                if data.shape[0] == 0 or data.shape[1] == 0: return 0.0
                fill_mask = (canvas == 0) & (data > 0)
                canvas[fill_mask] = data[fill_mask]
                return np.sum(canvas > 0) / canvas.size
        except Exception: 
            return 0.0
        finally:
            gc.collect()

    for item in all_items:
        # Process sequentially. Threading on 0.1 CPU adds overhead without speed gains.
        process_band(item, "B04", red_canvas)
        process_band(item, "B08", nir_canvas)
        process_band(item, "B03", green_canvas)
        process_band(item, "B02", blue_canvas)
            
        if np.sum(red_canvas > 0) / red_canvas.size > 0.98: break

    valid_mask = (red_canvas > 0) | (nir_canvas > 0) | (green_canvas > 0) | (blue_canvas > 0)
    rgb_arr = np.clip(np.dstack((red_canvas, green_canvas, blue_canvas)) / 3000.0, 0, 1)

    np.seterr(divide='ignore', invalid='ignore')
    ndvi = np.where(valid_mask, (nir_canvas - red_canvas) / (nir_canvas + red_canvas + 1e-5), 0.0)
    ndvi = np.clip(np.nan_to_num(ndvi), -1.0, 1.0)
    ndwi = np.where(valid_mask, (green_canvas - nir_canvas) / (green_canvas + nir_canvas + 1e-5), 0.0)
    ndwi = np.clip(np.nan_to_num(ndwi), -1.0, 1.0)
    L = 0.5
    savi = np.where(valid_mask, ((nir_canvas - red_canvas) / (nir_canvas + red_canvas + L)) * (1 + L), 0.0)
    savi = np.clip(np.nan_to_num(savi), -1.0, 1.0)

    return ndvi, ndwi, savi, rgb_arr, image_date

# Job store for async processing
jobs = {}

def get_season():
    month = datetime.datetime.now().month
    if 6 <= month <= 10:
        return "Kharif (Monsoon)"
    elif 11 <= month <= 12 or 1 <= month <= 3:
        return "Rabi (Winter)"
    else:
        return "Zaid (Summer)"

def get_area_hectares(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    # Approximate Haversine calculation for bounding box area
    R = 6371.0 # Earth radius in km
    lat_dist = math.radians(max_lat - min_lat) * R
    lon_dist = math.radians(max_lon - min_lon) * R * math.cos(math.radians((min_lat + max_lat) / 2))
    area_km2 = lat_dist * lon_dist
    return area_km2 * 100 # 1 km2 = 100 hectares

def get_location_context(lat, lon):
    try:
        # Nominatim Reverse Geocoding with explicit User-Agent
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {'User-Agent': 'SmartAgroApp/1.0 (contact@example.com)'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            state = data.get("address", {}).get("state", "Unknown")
            region_data = INDIAN_STATES_AGRI_DATA.get(state, None)
            return {"state": state, "agri_data": region_data, "display_name": data.get("display_name", "")}
    except:
        pass
    return {"state": "Unknown", "agri_data": None, "display_name": ""}

def get_weather_context(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get('current', {})
    except:
        pass
    return None

def process_area_job(job_id: str, bbox: list[float]):
    """Background worker that does the heavy lifting."""
    try:
        jobs[job_id]["status"] = "processing"
        
        # 1. Environmental Context Extraction
        center_lon = (bbox[0] + bbox[2]) / 2
        center_lat = (bbox[1] + bbox[3]) / 2
        area_ha = get_area_hectares(bbox)
        season = get_season()
        location_ctx = get_location_context(center_lat, center_lon)
        weather_ctx = get_weather_context(center_lat, center_lon)
        
        context_data = {
            "area_hectares": round(area_ha, 2),
            "season": season,
            "location": location_ctx,
            "weather": weather_ctx
        }
        
        # 2. Satellite Data Fetching
        ndvi, ndwi, savi, rgb, img_date = get_planetary_data(bbox)
        stats = analyze_crop_health(ndvi)
        mean_ndwi = np.nanmean(ndwi)
        
        y_text, y_emoji, yield_color = estimate_yield(stats['healthy_pct'], mean_ndwi, temp=None, rain=None)
        
        # 3. Context-Aware Recommendations
        suggestion = get_agricultural_recommendation(
            healthy_pct=stats['healthy_pct'], 
            moderate_pct=stats['moderate_pct'], 
            stressed_pct=stats['stressed_pct'],
            context=context_data
        )
        
        if mean_ndwi < -0.1:
            suggestion += " Satellite moisture index indicates Drought Warning."
        elif mean_ndwi > 0.3:
            suggestion += " Satellite moisture index indicates Waterlogging Warning."
            
        maps = generate_maps(ndvi, stats['class_matrix'], rgb, ndwi, savi)
        stats.pop('class_matrix')
        
        jobs[job_id]["data"] = {
            "stats": stats,
            "yield": {"text": y_text, "emoji": y_emoji, "color": yield_color},
            "recommendation": suggestion,
            "maps": maps,
            "image_date": img_date,
            "mean_ndwi": float(mean_ndwi),
            "context": context_data
        }
        jobs[job_id]["status"] = "completed"
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

@app.post("/api/analyze-async")
def analyze_area_async(req: AreaRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued"}
    background_tasks.add_task(process_area_job, job_id, req.bbox)
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] == "completed":
        # Optionally delete job after fetching to free memory
        data = job["data"]
        del jobs[job_id]
        return {"status": "completed", "data": data}
    elif job["status"] == "error":
        err = job["error"]
        del jobs[job_id]
        return {"status": "error", "detail": err}
    
    return {"status": job["status"]}

@app.get("/api/weather")
def get_weather(lat: float, lng: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json().get('current', {})
    except:
        pass
    return {}

@app.get("/api/region-info")
def get_region_info_api(state: str = None):
    if state and state in INDIAN_STATES_AGRI_DATA:
        return INDIAN_STATES_AGRI_DATA[state]
    return INDIAN_STATES_AGRI_DATA

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
