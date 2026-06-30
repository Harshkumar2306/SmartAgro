import datetime
import pystac_client
import planetary_computer
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
import numpy as np
import gc

bbox = [77.0468, 22.3505, 77.0568, 22.3605]
catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=120)
time_range = f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime=time_range,
    query={"eo:cloud_cover": {"lt": 20}},
    sortby=[{"field": "eo:cloud_cover", "direction": "asc"}],
    max_items=3,
)

all_items = list(search.items())
print("Found items:", len(all_items))
target_size = 512

for item in all_items:
    print("Processing item:", item.datetime)
    href = item.assets["B04"].href
    env = rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", 
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff", 
        VSI_CACHE=True, 
        VSI_CACHE_SIZE="500000000",
        GDAL_CACHEMAX="1024",
        GDAL_HTTP_MULTIMAC="YES", 
        GDAL_HTTP_MERGE_CONSECUTIVE_READS="YES"
    )
    with env, rasterio.open(href) as src:
        print("Opened file.")
        src_bounds = transform_bounds("EPSG:4326", src.crs, *bbox)
        window = from_bounds(*src_bounds, transform=src.transform)
        print("Reading window...")
        data = src.read(1, window=window, boundless=True, fill_value=0, out_shape=(target_size, target_size)).astype(np.float32)
        print("Data shape:", data.shape)
        
print("Success!")
