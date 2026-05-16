import numpy as np
from sklearn.cluster import KMeans

def analyze_crop_health(ndvi_matrix):
    """
    Analyzes crop health using Unsupervised K-Means Machine Learning clustering 
    instead of rigid, static thresholds. This allows the system to build distinct
    Management Zones tailored precisely to the local field context.
    """
    total_pixels = ndvi_matrix.size
    
    # Isolate vegetation (exclude extreme lows like roads, clouds, and water)
    veg_mask = ndvi_matrix > 0.1
    vegetation_pixels = np.sum(veg_mask)
    vegetation_coverage = (vegetation_pixels / total_pixels) * 100 if total_pixels > 0 else 0
    
    classification = np.zeros_like(ndvi_matrix, dtype=np.uint8)
    
    if vegetation_pixels > 10:
        # Extract 1D array of only the relevant vegetation pixels
        veg_values = ndvi_matrix[veg_mask].reshape(-1, 1)
        
        # Run Mathematical KMeans Clustering to partition into 3 Zones
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(veg_values)
        centroids = kmeans.cluster_centers_.flatten()
        
        # AI assigns arbitrary IDs (0, 1, 2) to clusters. We must sort them mathematically.
        # Highest Mathematical Center -> Healthy (Label 3)
        # Middle Mathematical Center -> Moderate (Label 2)
        # Lowest Mathematical Center -> Stressed (Label 1)
        sorted_indices = np.argsort(centroids)
        stressed_cluster = sorted_indices[0]
        moderate_cluster = sorted_indices[1]
        healthy_cluster = sorted_indices[2]
        
        # Re-map ML variables into our standard bucket identifiers
        remapped_labels = np.zeros_like(labels, dtype=np.uint8)
        remapped_labels[labels == stressed_cluster] = 1
        remapped_labels[labels == moderate_cluster] = 2
        remapped_labels[labels == healthy_cluster] = 3
        
        # Morph the 1D ML outputs back into the 2D original physical array
        classification[veg_mask] = remapped_labels
        
        healthy_pct = (np.sum(remapped_labels == 3) / vegetation_pixels) * 100
        moderate_pct = (np.sum(remapped_labels == 2) / vegetation_pixels) * 100
        stressed_pct = (np.sum(remapped_labels == 1) / vegetation_pixels) * 100
    else:
        healthy_pct = moderate_pct = stressed_pct = 0.0

    stats = {
        'vegetation_coverage': vegetation_coverage,
        'vegetation_pixels': vegetation_pixels,
        'healthy_pct': healthy_pct,
        'moderate_pct': moderate_pct,
        'stressed_pct': stressed_pct,
        'class_matrix': classification
    }
    
    return stats
