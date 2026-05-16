import numpy as np

def calculate_ndvi(red_band, nir_band):
    """
    Calculates the NDVI from Red and NIR bands.
    NDVI = (NIR - Red) / (NIR + Red)
    """
    # Disable division by zero warnings to handle it manually
    np.seterr(divide='ignore', invalid='ignore')
    
    # Calculate NDVI
    ndvi = (nir_band - red_band) / (nir_band + red_band)
    
    # Handle division by zero or invalid values (like completely black pixels)
    # Replace NaN or Info values with 0
    ndvi = np.nan_to_num(ndvi, nan=0.0, posinf=0.0, neginf=0.0)
    
    # Clip values to ensure they are strictly between -1 and 1
    ndvi = np.clip(ndvi, -1.0, 1.0)
    
    return ndvi
