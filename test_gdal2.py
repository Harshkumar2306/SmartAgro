import rasterio

env = rasterio.Env(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", 
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS="tif,tiff", 
    VSI_CACHE=True, 
    VSI_CACHE_SIZE=500000000,
    GDAL_CACHEMAX=1024,
    GDAL_HTTP_MULTIMAC="YES", 
    GDAL_HTTP_MERGE_CONSECUTIVE_READS="YES"
)
with env:
    print("Env opened successfully!")
