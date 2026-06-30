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

def get_agricultural_recommendation(healthy_pct, moderate_pct, stressed_pct, context=None):
    base_rec = ""
    if healthy_pct > 70 and stressed_pct < 10:
        base_rec = "Excellent vegetation health detected. Maintain current irrigation and nutrient management schedules because the crop canopy is highly vigorous."
    elif stressed_pct > 30:
        base_rec = f"CRITICAL ALERT: Over {stressed_pct:.1f}% of the selected area shows severe stress. Immediate intervention is highly recommended to investigate irrigation failure, pest outbreaks, or severe drought conditions in the red zones!"
    elif moderate_pct > 50:
        base_rec = f"High proportion of moderate vegetation ({moderate_pct:.1f}%) detected. The crop is surviving but not thriving. Recommend checking soil nutrient profiles, applying targeted fertilizers, or optimizing irrigation to transition these zones into high yield."
    elif healthy_pct > 40:
        base_rec = f"Moderate crop vitality detected with {stressed_pct:.1f}% stressed pixels. Consider conducting targeted drone/ground surveys in the yellow and red zones to check for localized water stress or nitrogen deficiency."
    else:
        base_rec = f"Low overall vegetation health detected. While severe stress is limited to {stressed_pct:.1f}%, the lack of dense canopy suggests early growth stages, recent harvest, or systemic underperformance. Monitor closely."

    if not context:
        return base_rec
        
    # Append Environmental Context
    env_rec = f"\n\n🌍 ENVIRONMENTAL CONTEXT & INSIGHTS:\n"
    
    # Area
    area = context.get("area_hectares", 0)
    if area > 0:
        env_rec += f"- Farm Size: {area} Hectares.\n"
        
    # Season
    season = context.get("season", "Unknown")
    env_rec += f"- Current Season: {season}. Ensure your crop selection matches the seasonal rainfall patterns.\n"
    
    # Soil & Region
    loc = context.get("location", {})
    state = loc.get("state", "Unknown")
    agri_data = loc.get("agri_data", None)
    if agri_data:
        env_rec += f"- Region ({state}): Identified soil type is {agri_data['soil_type']}. "
        env_rec += f"Highly suitable for {agri_data['suitable_crops']}.\n"
    elif state != "Unknown":
        env_rec += f"- Region: {state}.\n"
        
    # Weather
    weather = context.get("weather", None)
    if weather:
        temp = weather.get("temperature_2m", "N/A")
        hum = weather.get("relative_humidity_2m", "N/A")
        rain = weather.get("precipitation", 0)
        env_rec += f"- Live Weather: Temp {temp}°C, Humidity {hum}%. "
        if rain > 0:
            env_rec += f"Recent rainfall of {rain}mm detected. Adjust irrigation accordingly."
        elif hum != "N/A" and hum > 80:
            env_rec += "High humidity detected. Monitor closely for fungal diseases."
            
    return base_rec + env_rec
