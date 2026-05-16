INDIAN_STATES_AGRI_DATA = {
    "Punjab": {
        "soil_type": "Loam, Sandy Loam",
        "major_crops": "Wheat, Rice, Cotton",
        "suitable_crops": "Sugarcane, Maize",
        "requirements": "Temp: 15-30°C, Rainfall: 50-100cm"
    },
    "Maharashtra": {
        "soil_type": "Black Soil (Regur)",
        "major_crops": "Cotton, Sugarcane, Soyabean",
        "suitable_crops": "Jowar, Bajra",
        "requirements": "Temp: 20-35°C, Rainfall: 60-150cm"
    },
    "Uttar Pradesh": {
        "soil_type": "Alluvial Soil",
        "major_crops": "Wheat, Sugarcane, Rice",
        "suitable_crops": "Potato, Mustard",
        "requirements": "Temp: 15-35°C, Rainfall: 100-200cm"
    },
    "West Bengal": {
        "soil_type": "Alluvial, Deltaic",
        "major_crops": "Rice, Jute, Tea",
        "suitable_crops": "Potato, Oilseeds",
        "requirements": "Temp: 20-35°C, Rainfall: 150-250cm"
    },
    "Gujarat": {
        "soil_type": "Black, Sandy",
        "major_crops": "Cotton, Groundnut, Tobacco",
        "suitable_crops": "Wheat, Bajra",
        "requirements": "Temp: 25-35°C, Rainfall: 50-100cm"
    },
    "Karnataka": {
        "soil_type": "Red, Laterite, Black",
        "major_crops": "Coffee, Silk, Sunflower",
        "suitable_crops": "Ragi, Maize",
        "requirements": "Temp: 20-30°C, Rainfall: 70-150cm"
    }
}

def get_agricultural_recommendation(healthy_pct, moderate_pct, stressed_pct):
    if healthy_pct > 70 and stressed_pct < 10:
        return "Excellent vegetation health detected. Maintain current irrigation and nutrient management schedules because the crop canopy is highly vigorous."
    elif stressed_pct > 30:
        return f"CRITICAL ALERT: Over {stressed_pct:.1f}% of the selected area shows severe stress. Immediate intervention is highly recommended to investigate irrigation failure, pest outbreaks, or severe drought conditions in the red zones!"
    elif moderate_pct > 50:
        return f"High proportion of moderate vegetation ({moderate_pct:.1f}%) detected. The crop is surviving but not thriving. Recommend checking soil nutrient profiles, applying targeted fertilizers, or optimizing irrigation to transition these zones into high yield."
    elif healthy_pct > 40:
        return f"Moderate crop vitality detected with {stressed_pct:.1f}% stressed pixels. Consider conducting targeted drone/ground surveys in the yellow and red zones to check for localized water stress or nitrogen deficiency."
    else:
        return f"Low overall vegetation health detected. While severe stress is limited to {stressed_pct:.1f}%, the lack of dense canopy suggests early growth stages, recent harvest, or systemic underperformance. Monitor closely."
