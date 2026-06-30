import os
import io
import base64
import datetime
import traceback
import logging
import json
import subprocess
import sys
import tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.colors import ListedColormap
import rasterio
from rasterio.io import MemoryFile
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uuid
from pydantic import BaseModel
import math
import gc
import threading

from backend.ndvi import calculate_ndvi
from backend.stress_detection import analyze_crop_health
from backend.yield_prediction import estimate_yield
from backend.recommendations import get_agricultural_recommendation, INDIAN_STATES_AGRI_DATA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartagro")

app = FastAPI(title="Smart Agri API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread-safe job store
jobs = {}
jobs_lock = threading.Lock()

def set_job(job_id, data):
    with jobs_lock:
        jobs[job_id] = data

def get_job(job_id):
    with jobs_lock:
        return jobs.get(job_id, None)

def delete_job(job_id):
    with jobs_lock:
        jobs.pop(job_id, None)


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight', transparent=True, dpi=80)
    buf.seek(0)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    buf.close()
    return b64

def generate_maps(ndvi_matrix, class_matrix, rgb_matrix=None, ndwi_matrix=None, savi_matrix=None):
    maps = {}
    try:
        fig = Figure(figsize=(5, 4))
        FigureCanvas(fig)
        ax = fig.add_subplot(111)
        im = ax.imshow(ndvi_matrix, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
        fig.colorbar(im, ax=ax, label='NDVI Value')
        ax.axis('off')
        maps['ndvi_map'] = fig_to_base64(fig)
        
        fig2 = Figure(figsize=(5, 4))
        FigureCanvas(fig2)
        ax2 = fig2.add_subplot(111)
        colors = ['#808080', '#FF0000', '#FFFF00', '#008000']
        cmap_custom = ListedColormap(colors)
        im2 = ax2.imshow(class_matrix, cmap=cmap_custom, vmin=-0.5, vmax=3.5)
        cbar = fig2.colorbar(im2, ax=ax2, ticks=[0, 1, 2, 3])
        cbar.ax.set_yticklabels(['Non-Vegetation', 'Stressed', 'Moderate', 'Healthy'])
        ax2.axis('off')
        maps['stress_map'] = fig_to_base64(fig2)
        
        if rgb_matrix is not None:
            fig3 = Figure(figsize=(5, 4))
            FigureCanvas(fig3)
            ax3 = fig3.add_subplot(111)
            ax3.imshow(rgb_matrix)
            ax3.axis('off')
            maps['rgb_map'] = fig_to_base64(fig3)
            
        if ndwi_matrix is not None:
            fig4 = Figure(figsize=(5, 4))
            FigureCanvas(fig4)
            ax4 = fig4.add_subplot(111)
            im4 = ax4.imshow(ndwi_matrix, cmap='BrBG', vmin=-1.0, vmax=1.0)
            fig4.colorbar(im4, ax=ax4, label='NDWI Value')
            ax4.axis('off')
            maps['ndwi_map'] = fig_to_base64(fig4)
            
        if savi_matrix is not None:
            fig5 = Figure(figsize=(5, 4))
            FigureCanvas(fig5)
            ax5 = fig5.add_subplot(111)
            im5 = ax5.imshow(savi_matrix, cmap='YlGn', vmin=-0.2, vmax=1.0)
            fig5.colorbar(im5, ax=ax5, label='SAVI Value')
            ax5.axis('off')
            maps['savi_map'] = fig_to_base64(fig5)
    except Exception as e:
        logger.error(f"Error generating maps: {e}")
    finally:
        gc.collect()
    return maps

def load_data_from_bytes(file_bytes):
    with MemoryFile(file_bytes) as memfile:
        with memfile.open() as src:
            data = src.read(1)
            return data.astype(np.float32)

@app.get("/")
def health_check():
    return {"status": "running", "service": "SmartAgro API", "version": "2.1"}

@app.post("/api/analyze-local")
async def analyze_local(b04: UploadFile = File(...), b08: UploadFile = File(...)):
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
    bbox: list[float]


# ====================================================================
# SATELLITE WORKER SCRIPT
# This runs in a SEPARATE PROCESS to protect the main server from
# GDAL/rasterio segfaults. If rasterio crashes, only this subprocess
# dies - the main uvicorn server stays alive.
# ====================================================================
SATELLITE_WORKER_SCRIPT = '''
import sys
import json
import datetime
import numpy as np
import gc

def main():
    bbox = json.loads(sys.argv[1])
    output_file = sys.argv[2]
    
    import pystac_client
    import planetary_computer
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    from rasterio.enums import Resampling
    
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
        max_items=1,
    )

    all_items = list(search.items())
    if not all_items:
        raise ValueError("No cloud-free Sentinel-2 imagery found for this area in the last 120 days.")

    item = all_items[0]
    image_date = item.datetime.strftime("%Y-%m-%d") if item.datetime else "Unknown"
    
    target_size = 256
    bbox_4326 = [min_lon, min_lat, max_lon, max_lat]
    
    def read_band(band_name):
        if band_name not in item.assets:
            return np.zeros((target_size, target_size), dtype=np.float32)
        href = item.assets[band_name].href
        try:
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff"):
                with rasterio.open(href) as src:
                    src_bounds = transform_bounds("EPSG:4326", src.crs, *bbox_4326)
                    window = from_bounds(*src_bounds, transform=src.transform)
                    data = src.read(1, window=window, boundless=True, fill_value=0, 
                                   out_shape=(target_size, target_size),
                                   resampling=Resampling.nearest).astype(np.float32)
                    return data
        except Exception as e:
            print(f"Error reading band {band_name}: {e}", file=sys.stderr)
            return np.zeros((target_size, target_size), dtype=np.float32)
        finally:
            gc.collect()

    red = read_band("B04")
    nir = read_band("B08")
    green = read_band("B03")
    blue = read_band("B02")

    valid_mask = (red > 0) | (nir > 0) | (green > 0) | (blue > 0)
    rgb_arr = np.clip(np.dstack((red, green, blue)) / 3000.0, 0, 1)

    np.seterr(divide='ignore', invalid='ignore')
    ndvi = np.where(valid_mask, (nir - red) / (nir + red + 1e-5), 0.0)
    ndvi = np.clip(np.nan_to_num(ndvi), -1.0, 1.0)
    ndwi = np.where(valid_mask, (green - nir) / (green + nir + 1e-5), 0.0)
    ndwi = np.clip(np.nan_to_num(ndwi), -1.0, 1.0)
    L = 0.5
    savi = np.where(valid_mask, ((nir - red) / (nir + red + L)) * (1 + L), 0.0)
    savi = np.clip(np.nan_to_num(savi), -1.0, 1.0)

    # Save arrays to a compressed npz file
    np.savez_compressed(output_file, ndvi=ndvi, ndwi=ndwi, savi=savi, rgb=rgb_arr)
    
    # Print image_date to stdout for the parent process to read
    print(json.dumps({"image_date": image_date, "status": "ok"}))

if __name__ == "__main__":
    main()
'''


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
    R = 6371.0
    lat_dist = math.radians(max_lat - min_lat) * R
    lon_dist = math.radians(max_lon - min_lon) * R * math.cos(math.radians((min_lat + max_lat) / 2))
    area_km2 = lat_dist * lon_dist
    return area_km2 * 100

def get_location_context(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {'User-Agent': 'SmartAgroApp/1.0 (contact@example.com)'}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            state = data.get("address", {}).get("state", "Unknown")
            region_data = INDIAN_STATES_AGRI_DATA.get(state, None)
            return {"state": state, "agri_data": region_data, "display_name": data.get("display_name", "")}
    except Exception as e:
        logger.warning(f"Location context failed: {e}")
    return {"state": "Unknown", "agri_data": None, "display_name": ""}

def get_weather_context(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json().get('current', {})
    except Exception as e:
        logger.warning(f"Weather context failed: {e}")
    return None


def run_satellite_subprocess(bbox):
    """
    Runs the satellite data fetching in a SEPARATE PROCESS.
    If GDAL/rasterio segfaults, only the subprocess dies.
    Returns (ndvi, ndwi, savi, rgb, image_date) numpy arrays.
    """
    # Write the worker script to a temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir='/tmp') as f:
        f.write(SATELLITE_WORKER_SCRIPT)
        script_path = f.name
    
    # Create temp file for numpy output
    output_path = tempfile.mktemp(suffix='.npz', dir='/tmp')
    
    try:
        bbox_json = json.dumps(bbox)
        logger.info(f"Launching satellite subprocess for bbox: {bbox}")
        
        result = subprocess.run(
            [sys.executable, script_path, bbox_json, output_path],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Satellite subprocess crashed"
            logger.error(f"Subprocess failed (exit {result.returncode}): {error_msg}")
            raise RuntimeError(f"Satellite data fetch failed: {error_msg}")
        
        # Parse the JSON output from stdout
        stdout_lines = result.stdout.strip().split('\n')
        metadata = json.loads(stdout_lines[-1])
        image_date = metadata["image_date"]
        
        # Load the numpy arrays
        data = np.load(output_path)
        ndvi = data['ndvi']
        ndwi = data['ndwi']
        savi = data['savi']
        rgb = data['rgb']
        
        logger.info(f"Subprocess completed successfully. Image date: {image_date}")
        return ndvi, ndwi, savi, rgb, image_date
        
    finally:
        # Clean up temp files
        try:
            os.unlink(script_path)
        except:
            pass
        try:
            os.unlink(output_path)
        except:
            pass


def process_area_job(job_id: str, bbox: list[float]):
    """Background worker. Uses subprocess for satellite data to survive segfaults."""
    try:
        logger.info(f"[{job_id}] Starting job")
        set_job(job_id, {"status": "processing"})
        
        center_lon = (bbox[0] + bbox[2]) / 2
        center_lat = (bbox[1] + bbox[3]) / 2
        area_ha = get_area_hectares(bbox)
        season = get_season()
        
        logger.info(f"[{job_id}] Area: {area_ha:.0f} ha, Season: {season}")
        
        location_ctx = get_location_context(center_lat, center_lon)
        weather_ctx = get_weather_context(center_lat, center_lon)
        
        context_data = {
            "area_hectares": round(area_ha, 2),
            "season": season,
            "location": location_ctx,
            "weather": weather_ctx
        }
        
        # Run satellite fetch in ISOLATED subprocess
        ndvi, ndwi, savi, rgb, img_date = run_satellite_subprocess(bbox)
        
        logger.info(f"[{job_id}] Running ML analysis...")
        stats = analyze_crop_health(ndvi)
        mean_ndwi = float(np.nanmean(ndwi))
        
        y_text, y_emoji, yield_color = estimate_yield(stats['healthy_pct'], mean_ndwi, temp=None, rain=None)
        
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
            
        logger.info(f"[{job_id}] Generating maps...")
        maps = generate_maps(ndvi, stats['class_matrix'], rgb, ndwi, savi)
        
        del ndvi, ndwi, savi, rgb
        stats.pop('class_matrix')
        gc.collect()
        
        result = {
            "stats": stats,
            "yield": {"text": y_text, "emoji": y_emoji, "color": yield_color},
            "recommendation": suggestion,
            "maps": maps,
            "image_date": img_date,
            "mean_ndwi": mean_ndwi,
            "context": context_data
        }
        
        set_job(job_id, {"status": "completed", "data": result})
        logger.info(f"[{job_id}] COMPLETED!")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{job_id}] FAILED: {error_msg}")
        logger.error(traceback.format_exc())
        set_job(job_id, {"status": "error", "error": error_msg})
    finally:
        gc.collect()


@app.post("/api/analyze-async")
def analyze_area_async(req: AreaRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    set_job(job_id, {"status": "queued"})
    background_tasks.add_task(process_area_job, job_id, req.bbox)
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        status = job.get("status", "unknown")
        if status == "completed":
            data = job.get("data", {})
            delete_job(job_id)
            return {"status": "completed", "data": data}
        elif status == "error":
            err = job.get("error", "Unknown error")
            delete_job(job_id)
            return {"status": "error", "detail": err}
        return {"status": status}
    except Exception as e:
        logger.error(f"Error reading job {job_id}: {e}")
        delete_job(job_id)
        return {"status": "error", "detail": f"Internal error: {str(e)}"}

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
