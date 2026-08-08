"""NDVI vigour classification with explicit, documented default thresholds."""

import numpy as np
from sklearn.cluster import KMeans

DEFAULT_THRESHOLDS = {
    "vegetation": 0.10,
    "stressed": 0.30,
    "healthy": 0.60,
}


def analyze_crop_health(ndvi_matrix, valid_mask=None, thresholds=None):
    """Summarise valid NDVI observations and classify vegetation vigour.

    Thresholds are transparent defaults for broad screening, not a crop-specific
    diagnosis. Percentages are calculated only across vegetation pixels.
    """
    values = np.asarray(ndvi_matrix, dtype=np.float32)
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    finite = np.isfinite(values)
    valid = finite if valid_mask is None else (finite & np.asarray(valid_mask, dtype=bool))
    valid_pixels = int(np.count_nonzero(valid))
    total_pixels = int(values.size)

    classification = np.zeros(values.shape, dtype=np.uint8)
    if not valid_pixels:
        return {
            "vegetation_coverage": 0.0,
            "vegetation_pixels": 0,
            "valid_pixels": 0,
            "total_pixels": total_pixels,
            "healthy_pct": 0.0,
            "moderate_pct": 0.0,
            "stressed_pct": 0.0,
            "ndvi_summary": {"mean": None, "median": None, "p10": None, "p90": None, "min": None, "max": None},
            "thresholds": limits,
            "classification_note": "No valid observations were available for classification.",
            "class_matrix": classification,
        }

    valid_values = values[valid]
    vegetation = valid & (values > limits["vegetation"])
    vegetation_pixels = int(np.count_nonzero(vegetation))
    vegetation_coverage = (vegetation_pixels / valid_pixels) * 100

    if vegetation_pixels < 3:
        stressed = vegetation & (values <= limits["stressed"])
        moderate = vegetation & (values > limits["stressed"]) & (values <= limits["healthy"])
        healthy = vegetation & (values > limits["healthy"])
        classification[stressed] = 1
        classification[moderate] = 2
        classification[healthy] = 3
        note = "Not enough vegetation pixels for machine learning. Static defaults used."
    else:
        veg_values = values[vegetation].reshape(-1, 1)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10).fit(veg_values)
        
        centers = kmeans.cluster_centers_.flatten()
        sorted_indices = np.argsort(centers)
        
        low_center = centers[sorted_indices[0]]
        med_center = centers[sorted_indices[1]]
        high_center = centers[sorted_indices[2]]
        
        limits["stressed"] = round(float((low_center + med_center) / 2), 3)
        limits["healthy"] = round(float((med_center + high_center) / 2), 3)
        
        stressed = vegetation & (values <= limits["stressed"])
        moderate = vegetation & (values > limits["stressed"]) & (values <= limits["healthy"])
        healthy = vegetation & (values > limits["healthy"])
        
        classification[stressed] = 1
        classification[moderate] = 2
        classification[healthy] = 3
        note = "Dynamic K-Means machine learning clustering applied."

    denominator = max(vegetation_pixels, 1)
    return {
        "vegetation_coverage": round(vegetation_coverage, 2),
        "vegetation_pixels": vegetation_pixels,
        "valid_pixels": valid_pixels,
        "total_pixels": total_pixels,
        "healthy_pct": round(float(np.count_nonzero(healthy) / denominator * 100), 2) if vegetation_pixels else 0.0,
        "moderate_pct": round(float(np.count_nonzero(moderate) / denominator * 100), 2) if vegetation_pixels else 0.0,
        "stressed_pct": round(float(np.count_nonzero(stressed) / denominator * 100), 2) if vegetation_pixels else 0.0,
        "ndvi_summary": {
            "mean": round(float(np.mean(valid_values)), 3),
            "median": round(float(np.median(valid_values)), 3),
            "p10": round(float(np.percentile(valid_values, 10)), 3),
            "p90": round(float(np.percentile(valid_values, 90)), 3),
            "min": round(float(np.min(valid_values)), 3),
            "max": round(float(np.max(valid_values)), 3),
        },
        "thresholds": limits,
        "classification_note": note,
        "class_matrix": classification,
    }
