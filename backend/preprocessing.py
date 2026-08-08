import rasterio
import numpy as np

def load_band_data(filepath):
    """
    Reads a GeoTIFF image using Rasterio, converts to float32,
    and returns the numpy array along with the metadata.
    """
    with rasterio.open(filepath) as src:
        # Read the first band
        data = src.read(1)
        meta = src.meta
        
        # Convert pixel values to float to avoid division errors
        data_float = data.astype(np.float32)
        
        return data_float, meta
