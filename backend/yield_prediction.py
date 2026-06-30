import numpy as np

def estimate_yield(healthy_percentage, ndwi_mean=None, temp=None, rain=None):
    """
    Simulated Machine Learning Yield Predictor (Random Forest behavior)
    Estimates crop yield dynamically based on health, moisture, and local weather.
    """
    # Base yield based on healthy percentage
    base_yield = 2.5 + (healthy_percentage / 100.0) * 4.0 # Range: ~2.5 to 6.5 MT/ha
    
    # Adjust for water stress using NDWI (normal is >0, drought is <0)
    if ndwi_mean is not None:
        if ndwi_mean < -0.1:
            base_yield *= 0.6  # 40% penalty for drought stress
        elif ndwi_mean > 0.3:
            base_yield *= 0.9  # 10% penalty for waterlogging/flooding
        else:
            base_yield *= 1.1  # Optimal moisture boost

    # Adjust for weather extremes (Temperature and Rainfall)
    if temp is not None:
        if temp > 38:
            base_yield -= 1.0  # Heat stress penalty
        elif temp < 10:
            base_yield -= 0.5  # Cold stress penalty

    if rain is not None and rain > 100:
        base_yield -= 0.8  # Heavy flooding penalty
        
    # Cap between realistic boundaries
    base_yield = max(0.5, min(base_yield, 8.5))
    
    if base_yield > 6.0:
        return f"{base_yield:.1f} MT/ha (High)", "🟢", "#4CAF50", base_yield
    elif base_yield >= 3.5:
        return f"{base_yield:.1f} MT/ha (Avg)", "🟡", "#FFC107", base_yield
    else:
        return f"{base_yield:.1f} MT/ha (Low)", "🔴", "#F44336", base_yield
