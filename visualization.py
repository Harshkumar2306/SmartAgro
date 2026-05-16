import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np

def plot_ndvi(ndvi_matrix, output_path="ndvi_map.png"):
    """
    Plots the NDVI map and saves it to a file.
    Uses RdYlGn colormap where:
    Red -> Low NDVI (Stressed/Soil)
    Yellow -> Moderate NDVI
    Green -> High NDVI (Healthy)
    """
    plt.figure(figsize=(10, 8))
    
    # We use RdYlGn colormap which is standard for NDVI
    # Values below 0 are often water/clouds, we can set vmin=0 to focus on land
    plt.imshow(ndvi_matrix, cmap='RdYlGn', vmin=-0.2, vmax=1.0)
    
    plt.colorbar(label='NDVI Value')
    plt.title('NDVI Map (Normalized Difference Vegetation Index)')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def plot_stress_map(classification_matrix, output_path="stress_map.png"):
    """
    Plots the categorical crop stress map.
    0: Non-vegetation (Gray)
    1: Stressed (Red)
    2: Moderate (Yellow)
    3: Healthy (Green)
    """
    plt.figure(figsize=(10, 8))
    
    # Custom colormap
    colors = ['#808080', '#FF0000', '#FFFF00', '#008000']
    cmap_custom = ListedColormap(colors)
    
    # Create the plot
    plt.imshow(classification_matrix, cmap=cmap_custom, vmin=-0.5, vmax=3.5)
    
    # Custom colorbar
    cbar = plt.colorbar(ticks=[0, 1, 2, 3])
    cbar.ax.set_yticklabels(['Non-Vegetation', 'Stressed', 'Moderate', 'Healthy'])
    
    plt.title('Crop Stress Detection Map')
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def print_summary(stats, yield_estimation):
    """
    Prints the summary of the NDVI analysis.
    """
    print("=" * 50)
    print("NDVI CROP MONITORING & YIELD PREDICTION SUMMARY")
    print("=" * 50)
    print(f"Total Vegetation Coverage: {stats['vegetation_coverage']:.2f}%")
    print("-" * 50)
    print("Vegetation Health Breakdown:")
    print(f"  - Healthy (>0.6)  : {stats['healthy_pct']:.2f}%")
    print(f"  - Moderate (0.3-0.6): {stats['moderate_pct']:.2f}%")
    print(f"  - Stressed (<0.3) : {stats['stressed_pct']:.2f}%")
    print("-" * 50)
    
    if isinstance(yield_estimation, tuple):
        y_text, y_emoji, y_color = yield_estimation
        result_text = f"{y_text} {y_emoji}"
    else:
        result_text = str(yield_estimation)
        
    print(f"Yield Estimation Result  : {result_text.upper()}")
    print("=" * 50)
