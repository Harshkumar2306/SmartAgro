import sys
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds
import pystac_client
import planetary_computer
import datetime

bbox_4326 = [78.9629, 20.5937, 78.9829, 20.6137]

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)
end_date = datetime.datetime.now()
start_date = end_date - datetime.timedelta(days=120)
time_range = f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"

search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox_4326,
    datetime=time_range,
    query={"eo:cloud_cover": {"lt": 20}},
    sortby=[{"field": "eo:cloud_cover", "direction": "asc"}],
    max_items=1,
)
items = list(search.items())
print("Items found:", len(items))

if items:
    href = items[0].assets["B04"].href
    print("href:", href)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff"):
        with rasterio.open(href) as src:
            print("src.crs:", src.crs)
            print("src.bounds:", src.bounds)
            src_bounds = transform_bounds("EPSG:4326", src.crs, *bbox_4326)
            print("transformed bounds:", src_bounds)
            window = from_bounds(*src_bounds, transform=src.transform)
            print("window:", window)
            data = src.read(1, window=window, boundless=True, fill_value=0, out_shape=(128, 128)).astype(np.float32)
            print("data min:", data.min(), "max:", data.max())

