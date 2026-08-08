INDIAN_STATES_AGRI_DATA = {
    "Punjab": {"soil_type": "Loam, Sandy Loam", "major_crops": "Wheat, Rice, Cotton", "suitable_crops": "Sugarcane, Maize", "requirements": "Temp: 15-30°C, Rainfall: 50-100cm"},
    "Maharashtra": {"soil_type": "Black Soil (Regur)", "major_crops": "Cotton, Sugarcane, Soyabean", "suitable_crops": "Jowar, Bajra", "requirements": "Temp: 20-35°C, Rainfall: 60-150cm"},
    "Uttar Pradesh": {"soil_type": "Alluvial Soil", "major_crops": "Wheat, Sugarcane, Rice", "suitable_crops": "Potato, Mustard", "requirements": "Temp: 15-35°C, Rainfall: 100-200cm"},
    "West Bengal": {"soil_type": "Alluvial, Deltaic", "major_crops": "Rice, Jute, Tea", "suitable_crops": "Potato, Oilseeds", "requirements": "Temp: 20-35°C, Rainfall: 150-250cm"},
    "Gujarat": {"soil_type": "Black, Sandy", "major_crops": "Cotton, Groundnut, Tobacco", "suitable_crops": "Wheat, Bajra", "requirements": "Temp: 25-35°C, Rainfall: 50-100cm"},
    "Karnataka": {"soil_type": "Red, Laterite, Black", "major_crops": "Coffee, Silk, Sunflower", "suitable_crops": "Ragi, Maize", "requirements": "Temp: 20-30°C, Rainfall: 70-150cm"},
}


def get_agricultural_recommendation(healthy_pct, moderate_pct, stressed_pct, context=None):
    """Give inspection priorities, rather than input prescriptions."""
    lines = ["Use these satellite observations to prioritise field checks; they do not diagnose nutrient, water, pest, or disease causes."]
    if stressed_pct > 30:
        lines.append(f"Prioritise a ground walk in the lower-vigour zones ({stressed_pct:.1f}% of vegetation pixels). Check emergence, irrigation distribution, pests, compaction and representative soil conditions.")
    elif moderate_pct > 50:
        lines.append(f"Most observed vegetation is in the mixed-vigour class ({moderate_pct:.1f}%). Compare field notes and crop stage before changing management.")
    elif healthy_pct > 60:
        lines.append(f"A large share of observed vegetation falls in the higher-vigour screening class ({healthy_pct:.1f}%). Continue routine scouting; satellite vigour alone is not a yield forecast.")
    else:
        lines.append("Canopy cover is limited or mixed. Confirm crop stage and field conditions before interpreting the vigour classes.")
    return lines
