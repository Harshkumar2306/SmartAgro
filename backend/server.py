import base64
import datetime
import gc
import io
import json
import logging
import math
import threading
import traceback
import uuid

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure
import numpy as np
import requests
from fastapi import BackgroundTasks, File, Form, HTTPException, UploadFile, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from backend.deep_analysis import run_deep_analysis
from backend.recommendations import INDIAN_STATES_AGRI_DATA, get_agricultural_recommendation
from backend.stress_detection import analyze_crop_health
from backend.yield_prediction import estimate_yield

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartagro")

EARTH_RADIUS_M = 6_371_008.8
MAX_AOI_HECTARES = 25_000

app = FastAPI(title="AgroSight decision-support API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
jobs, jobs_lock = {}, threading.Lock()


def set_job(job_id, data):
    with jobs_lock:
        jobs[job_id] = data


def get_job(job_id):
    with jobs_lock:
        return jobs.get(job_id)


def delete_job(job_id):
    with jobs_lock:
        jobs.pop(job_id, None)


def fig_to_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="jpeg", bbox_inches="tight", dpi=70, pil_kwargs={"quality": 80})
    buffer.seek(0)
    result = base64.b64encode(buffer.getvalue()).decode("utf-8")
    buffer.close()
    fig.clear()
    return result


def generate_maps(ndvi, classification, rgb=None, ndwi=None, savi=None):
    maps = {}
    definitions = [
        ("ndvi_map", ndvi, "RdYlGn", -0.2, 1.0, "NDVI"),
        ("stress_map", classification, ListedColormap(["#64748b", "#dc2626", "#f59e0b", "#15803d"]), -0.5, 3.5, "Vigour class"),
        ("ndwi_map", ndwi, "BrBG", -1.0, 1.0, "NDWI"),
        ("savi_map", savi, "YlGn", -0.2, 1.0, "SAVI"),
    ]
    try:
        if rgb is not None:
            fig = Figure(figsize=(4, 3)); FigureCanvas(fig)
            ax = fig.add_subplot(111); ax.imshow(rgb); ax.axis("off")
            maps["rgb_map"] = fig_to_base64(fig)
        for name, matrix, cmap, low, high, label in definitions:
            if matrix is None:
                continue
            fig = Figure(figsize=(4, 3)); FigureCanvas(fig)
            ax = fig.add_subplot(111)
            image = ax.imshow(matrix, cmap=cmap, vmin=low, vmax=high)
            fig.colorbar(image, ax=ax, label=label)
            ax.axis("off")
            maps[name] = fig_to_base64(fig)
    except Exception as exc:
        logger.warning("Map generation failed: %s", exc)
    return maps


def load_data_from_bytes(file_bytes):
    import rasterio
    from rasterio.io import MemoryFile
    with MemoryFile(file_bytes) as memory_file:
        with memory_file.open() as source:
            return source.read(1).astype(np.float32)


class CropContext(BaseModel):
    crop_type: str | None = Field(default=None, max_length=80)
    growth_stage: str | None = Field(default=None, max_length=80)
    target_yield: float | None = Field(default=None, ge=0, le=1000, description="User target only; not a calibration")
    field_area_ha: float | None = Field(default=None, gt=0, le=MAX_AOI_HECTARES)
    parcel_area_ha: float | None = Field(default=None, gt=0, le=MAX_AOI_HECTARES)


class AreaRequest(BaseModel):
    bbox: list[float]
    geometry: dict | None = None
    field_area_ha: float | None = None
    crop_context: CropContext | None = None

    @validator("bbox")
    def validate_bbox(cls, bbox):
        if len(bbox) != 4 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in bbox):
            raise ValueError("bbox must contain four finite coordinates: [west, south, east, north].")
        west, south, east, north = bbox
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("bbox must be within WGS84 bounds with west < east and south < north; anti-meridian AOIs are not supported.")
        if geodesic_bbox_area_hectares(bbox) > MAX_AOI_HECTARES:
            raise ValueError(f"AOI exceeds the {MAX_AOI_HECTARES:,} ha analysis limit.")
        return [float(value) for value in bbox]


def geodesic_bbox_area_hectares(bbox):
    """Spherical geodesic area of a latitude/longitude bounding box."""
    west, south, east, north = bbox
    delta_lon = math.radians(east - west)
    area_m2 = EARTH_RADIUS_M ** 2 * abs(math.sin(math.radians(north)) - math.sin(math.radians(south))) * delta_lon
    return area_m2 / 10_000


def bbox_dimensions_m(bbox):
    west, south, east, north = bbox
    mid_lat = math.radians((south + north) / 2)
    width = EARTH_RADIUS_M * math.radians(east - west) * max(math.cos(mid_lat), 0.01)
    height = EARTH_RADIUS_M * math.radians(north - south)
    return width, height


def target_shape(bbox, nominal_resolution_m=20):
    """Approximate 20 m analysis grid, capped to control remote reads and memory."""
    width, height = bbox_dimensions_m(bbox)
    scale = max(width / nominal_resolution_m, height / nominal_resolution_m, 1)
    factor = min(384 / scale, 1)
    columns = max(96, min(384, int(math.ceil(width / nominal_resolution_m * factor))))
    rows = max(96, min(384, int(math.ceil(height / nominal_resolution_m * factor))))
    return rows, columns, max(width / columns, height / rows)


def get_season():
    month = datetime.datetime.now().month
    return "Kharif (Monsoon)" if 6 <= month <= 10 else "Rabi (Winter)" if month in (11, 12, 1, 2, 3) else "Zaid (Summer)"


def get_location_context(lat, lon):
    try:
        response = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={"User-Agent": "AgroSight/1.0"}, timeout=5)
        if response.ok:
            data = response.json(); state = data.get("address", {}).get("state", "Unknown")
            return {"state": state, "agri_data": INDIAN_STATES_AGRI_DATA.get(state), "display_name": data.get("display_name", "")}
    except requests.RequestException as exc:
        logger.info("Location context unavailable: %s", exc)
    return {"state": "Unknown", "agri_data": None, "display_name": ""}


def get_weather_context(lat, lon):
    try:
        response = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m", timeout=5)
        return response.json().get("current", {}) if response.ok else None
    except requests.RequestException:
        return None


def run_satellite_analysis(bbox, geometry=None):
    import planetary_computer
    import pystac_client
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    west, south, east, north = bbox
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    end_date = datetime.datetime.now(); start_date = end_date - datetime.timedelta(days=120)
    search = catalog.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{start_date:%Y-%m-%d}/{end_date:%Y-%m-%d}", query={"eo:cloud_cover": {"lt": 35}}, sortby=[{"field": "eo:cloud_cover", "direction": "asc"}], max_items=1)
    item = next(iter(search.items()), None)
    if item is None:
        raise ValueError("No Sentinel-2 scene was found for this AOI in the last 120 days.")

    rows, columns, pixel_scale_m = target_shape(bbox)

    def read_asset(name, resampling):
        asset = item.assets.get(name)
        if asset is None:
            return None
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff"):
            with rasterio.open(asset.href) as source:
                source_bounds = transform_bounds("EPSG:4326", source.crs, west, south, east, north, densify_pts=21)
                window = from_bounds(*source_bounds, transform=source.transform)
                return source.read(1, window=window, boundless=True, fill_value=0, out_shape=(rows, columns), resampling=resampling).astype(np.float32)

    # Sentinel reflectance is continuous: bilinear resampling avoids block artefacts.
    red, nir, green, blue = (read_asset(name, Resampling.bilinear) for name in ("B04", "B08", "B03", "B02"))
    if any(band is None for band in (red, nir, green, blue)):
        raise ValueError("The selected Sentinel-2 scene is missing one or more required reflectance bands.")
    scl = read_asset("SCL", Resampling.nearest)
    base_valid = (red > 0) & (nir > 0) & (green > 0) & (blue > 0)
    scl_available = scl is not None
    # SCL classes: 0/1 no data or saturated, 2/3 shadow, 8-10 cloud/cirrus, 11 snow. Classes 4-7 are usable surface observations.
    valid_mask = base_valid & np.isin(scl.astype(np.uint8), [4, 5, 6, 7]) if scl_available else base_valid
    
    geom_type = "bounding_box"
    limitations = ["The selected map shape is analysed as its bounding box; drawn polygon boundaries are not used as a mask.", "Satellite vigour cannot identify the cause of stress or prescribe fertiliser, water, or yield.", "Cloud screening and 10–40 m satellite pixels can still miss sub-pixel and rapidly changing conditions."]
    if geometry:
        try:
            from rasterio.features import geometry_mask
            from rasterio.transform import from_bounds as transform_from_bounds
            out_transform = transform_from_bounds(west, south, east, north, columns, rows)
            polygon_mask = geometry_mask([geometry], out_shape=(rows, columns), transform=out_transform, invert=True)
            valid_mask = valid_mask & polygon_mask
            geom_type = "polygon"
            limitations = ["The selected map shape is analysed using true polygon masking; pixels outside your lines are excluded.", "Satellite vigour cannot identify the cause of stress or prescribe fertiliser, water, or yield.", "Cloud screening and 10–40 m satellite pixels can still miss sub-pixel and rapidly changing conditions."]
        except Exception as e:
            logger.warning(f"Failed to apply polygon mask: {e}")

    valid_fraction = float(np.count_nonzero(valid_mask) / valid_mask.size) if valid_mask.size else 0.0

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(valid_mask, (nir - red) / (nir + red + 1e-6), np.nan)
        ndwi = np.where(valid_mask, (green - nir) / (green + nir + 1e-6), np.nan)
        savi = np.where(valid_mask, 1.5 * (nir - red) / (nir + red + 0.5), np.nan)
    ndvi, ndwi, savi = (np.clip(array, -1, 1) for array in (ndvi, ndwi, savi))
    stats = analyze_crop_health(ndvi, valid_mask=valid_mask)
    mean_ndwi = float(np.nanmean(ndwi)) if np.any(np.isfinite(ndwi)) else None
    rgb = np.clip(np.dstack((red, green, blue)) / 3000.0, 0, 1)
    maps = generate_maps(ndvi, stats.pop("class_matrix"), rgb, ndwi, savi)
    image_date = item.datetime.strftime("%Y-%m-%d") if item.datetime else "Unknown"
    quality = {
        "valid_observation_fraction": round(valid_fraction, 4),
        "valid_observation_pct": round(valid_fraction * 100, 1),
        "scl_available": scl_available,
        "qa_method": "Sentinel-2 Scene Classification Layer mask (classes 4–7 retained)." if scl_available else "SCL asset unavailable; validity is based on non-zero reflectance only.",
        "scene_cloud_cover_pct": item.properties.get("eo:cloud_cover"),
    }
    measurement = {
        "imagery_date": image_date,
        "sensor": "Sentinel-2 L2A MSI",
        "analysis_resolution_m": round(pixel_scale_m, 1),
        "analysis_shape_pixels": [rows, columns],
        "geometry_type": geom_type,
        "methods": ["Bilinear resampling for continuous reflectance", "NDVI = (NIR − Red) / (NIR + Red)", "Default NDVI vigour thresholds"],
        "limitations": limitations,
    }
    return {"stats": stats, "image_date": image_date, "mean_ndwi": mean_ndwi, "maps": maps, "quality": quality, "measurement": measurement}


def context_dict(crop_context):
    return crop_context.dict(exclude_none=True) if crop_context else {}


def process_area_job(job_id, req: AreaRequest):
    try:
        set_job(job_id, {"status": "processing"})
        area_ha = req.field_area_ha if req.field_area_ha is not None else geodesic_bbox_area_hectares(req.bbox)
        centre_lat, centre_lon = (req.bbox[1] + req.bbox[3]) / 2, (req.bbox[0] + req.bbox[2]) / 2
        context = {"area_hectares": round(area_ha, 2), "season": get_season(), "location": get_location_context(centre_lat, centre_lon), "weather": get_weather_context(centre_lat, centre_lon), "crop_context": context_dict(req.crop_context)}
        payload = run_satellite_analysis(req.bbox, req.geometry)
        stats, mean_ndwi = payload["stats"], payload["mean_ndwi"]
        yield_text, yield_emoji, yield_colour, indicator_score = estimate_yield(stats["healthy_pct"], mean_ndwi, veg_coverage=stats.get("vegetation_coverage"))
        measurement = payload["measurement"] | {"area_hectares": round(area_ha, 2), "area_method": "Exact polygon area." if req.geometry else "Spherical geodesic bounding-box area (WGS84 coordinates)."}
        result = {
            "stats": stats, "yield": {"text": yield_text, "emoji": yield_emoji, "color": yield_colour, "score": indicator_score, "calibrated": False},
            "recommendation": get_agricultural_recommendation(stats["healthy_pct"], stats["moderate_pct"], stats["stressed_pct"], context),
            "maps": payload["maps"], "image_date": payload["image_date"], "mean_ndwi": mean_ndwi, "context": context,
            "quality": payload["quality"], "measurement": measurement,
            "resource_needs": {"status": "not_estimated", "intervention_area_ha": round(area_ha * (stats["moderate_pct"] + stats["stressed_pct"]) / 100, 2), "message": "No nutrient or irrigation volume is estimated. Verify causes with scouting, soil testing and irrigation-system measurements."},
            "disease_risk": {"risk_score": None, "label": "Not modelled", "warning": "Weather and satellite indices are not a calibrated disease-risk model."},
            "deep_analysis": None,
        }
        set_job(job_id, {"status": "completed", "data": result})
    except Exception as exc:
        logger.error("[%s] failed: %s\n%s", job_id, exc, traceback.format_exc())
        set_job(job_id, {"status": "error", "error": str(exc)})


@app.get("/")
def health_check():
    return {"status": "running", "service": "AgroSight decision-support API", "version": "3.0"}


@app.post("/api/analyze-async")
def analyze_area_async(req: AreaRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    set_job(job_id, {"status": "queued"})
    background_tasks.add_task(process_area_job, job_id, req)
    return {"job_id": job_id}


@app.post("/api/analyze-local")
async def analyze_local(b04: UploadFile = File(...), b08: UploadFile = File(...), crop_context: str | None = Form(default=None)):
    try:
        red, nir = load_data_from_bytes(await b04.read()), load_data_from_bytes(await b08.read())
        if red.shape != nir.shape:
            raise HTTPException(status_code=400, detail="Red and NIR GeoTIFFs must have identical dimensions.")
        valid = np.isfinite(red) & np.isfinite(nir) & (red > 0) & (nir > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = np.where(valid, (nir - red) / (nir + red + 1e-6), np.nan)
        stats = analyze_crop_health(np.clip(ndvi, -1, 1), valid_mask=valid)
        maps = generate_maps(ndvi, stats.pop("class_matrix"))
        parsed_context = CropContext.parse_obj(json.loads(crop_context)).dict(exclude_none=True) if crop_context else {}
        yield_text, yield_emoji, yield_colour, score = estimate_yield(stats["healthy_pct"], veg_coverage=stats.get("vegetation_coverage"))
        return {"stats": stats, "yield": {"text": yield_text, "emoji": yield_emoji, "color": yield_colour, "score": score, "calibrated": False}, "recommendation": get_agricultural_recommendation(stats["healthy_pct"], stats["moderate_pct"], stats["stressed_pct"], {"crop_context": parsed_context}), "maps": maps, "context": {"crop_context": parsed_context}, "quality": {"valid_observation_fraction": round(float(valid.mean()), 4), "valid_observation_pct": round(float(valid.mean() * 100), 1), "scl_available": False, "qa_method": "Finite, positive Red and NIR values retained; no SCL is available for local files."}, "measurement": {"geometry_type": "local_raster", "sensor": "User-supplied GeoTIFF", "methods": ["NDVI from supplied Red and NIR bands", "Default NDVI vigour thresholds"], "limitations": ["Band calibration, acquisition date, cloud masking and spatial metadata were not independently verified."]}, "resource_needs": {"status": "not_estimated", "message": "No nutrient or irrigation volume is estimated from uncalibrated local files."}, "disease_risk": {"risk_score": None, "label": "Not modelled", "warning": "No calibrated disease model was run."}, "deep_analysis": None}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not analyse local files: {exc}")


@app.get("/api/status/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job.get("status", "unknown")
    if status in ("completed", "error"):
        delete_job(job_id)
    return {"status": status, **({"data": job["data"]} if status == "completed" else {"detail": job.get("error")} if status == "error" else {})}


@app.get("/api/weather")
def get_weather(lat: float, lng: float):
    return get_weather_context(lat, lng) or {}


@app.get("/api/region-info")
def get_region_info_api(state: str = None):
    return INDIAN_STATES_AGRI_DATA.get(state) if state else INDIAN_STATES_AGRI_DATA


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
