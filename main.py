import argparse
from preprocessing import load_band_data
from ndvi import calculate_ndvi
from stress_detection import analyze_crop_health
from yield_prediction import estimate_yield
from visualization import plot_ndvi, plot_stress_map, print_summary

def main():
    parser = argparse.ArgumentParser(description="NDVI-Based Precision Agriculture System")
    parser.add_argument("--b04", required=True, help="Path to Sentinel-2 B04 (Red band) GeoTIFF")
    parser.add_argument("--b08", required=True, help="Path to Sentinel-2 B08 (NIR band) GeoTIFF")
    args = parser.parse_args()
    
    # 1. Preprocessing
    print(f"Loading Red Band: {args.b04}")
    red_band, _ = load_band_data(args.b04)
    
    print(f"Loading NIR Band: {args.b08}")
    nir_band, _ = load_band_data(args.b08)
    
    # Check that shapes match
    if red_band.shape != nir_band.shape:
        raise ValueError("Band images must have the same dimensions.")
    
    # 2. NDVI Calculation
    print("Calculating NDVI matrix...")
    ndvi_matrix = calculate_ndvi(red_band, nir_band)
    
    # 3. Crop Monitoring & Stress Detection
    print("Classifying crop stress and calculating crop monitoring statistics...")
    stats = analyze_crop_health(ndvi_matrix)
    
    # 4. Yield Estimation
    print("Estimating yield...")
    yield_est = estimate_yield(stats['healthy_pct'])
    
    # 5. Output / Visualization
    print("Generating NDVI and Stress maps...")
    plot_ndvi(ndvi_matrix, "ndvi_output.png")
    plot_stress_map(stats['class_matrix'], "stress_output.png")
    print("Outputs saved to ndvi_output.png and stress_output.png.")
    
    # Print the output in console
    print_summary(stats, yield_est)

if __name__ == "__main__":
    main()
