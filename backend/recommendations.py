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
    rec = "🌱 AI Crop Intelligence Report\n\n"
    
    # 1. Health Assessment
    rec += "🎯 Canopy Health Assessment:\n"
    if healthy_pct > 70 and stressed_pct < 10:
        rec += "The crop canopy is exhibiting excellent vigor. Photosynthetic activity is high, indicating that current irrigation and nutrient management schedules are optimal. Keep up the good work!\n"
    elif stressed_pct > 30:
        rec += f"⚠️ Critical Alert: We've detected severe stress across {stressed_pct:.1f}% of the field. Immediate on-ground intervention is highly recommended. Please investigate the red zones on the map for potential irrigation failures, pest outbreaks, or severe drought conditions.\n"
    elif moderate_pct > 50:
        rec += f"A significant portion of the field ({moderate_pct:.1f}%) is in a moderate state. The crop is surviving but not thriving. We recommend evaluating soil nutrient profiles and applying targeted fertilizers to transition these yellow zones into high yield.\n"
    elif healthy_pct > 40:
        rec += f"The field shows moderate vitality, but {stressed_pct:.1f}% of the area is stressed. Consider conducting targeted drone or ground surveys in the red zones to check for localized water stress or nitrogen deficiency.\n"
    else:
        rec += f"Overall vegetation health is quite low. While severe stress is limited to {stressed_pct:.1f}%, the lack of a dense canopy suggests early growth stages, a recent harvest, or systemic underperformance. Please monitor the situation closely.\n"

    if not context:
        return rec
        
    # 2. Environmental Context
    rec += "\n🌍 Environmental Insights:\n"
    
    area = context.get("area_hectares", 0)
    if area > 0:
        rec += f"• Farm Size: A vast {area} hectares are currently under analysis.\n"
        
    season = context.get("season", "Unknown")
    rec += f"• Seasonality: We are in the {season} season. Make sure your crop selection aligns with the expected seasonal rainfall patterns.\n"
    
    loc = context.get("location", {})
    state = loc.get("state", "Unknown")
    agri_data = loc.get("agri_data", None)
    if agri_data:
        rec += f"• Regional Profile ({state}): The identified soil type here is typically {agri_data['soil_type']}, which is highly suitable for {agri_data['suitable_crops']}.\n"
    elif state != "Unknown":
        rec += f"• Region: {state}.\n"
        
    weather = context.get("weather", None)
    if weather:
        temp = weather.get("temperature_2m", "N/A")
        hum = weather.get("relative_humidity_2m", "N/A")
        rain = weather.get("precipitation", 0)
        rec += f"• Live Weather: The current temperature is {temp}°C with {hum}% humidity. "
        if rain > 0:
            rec += f"We detected recent rainfall of {rain}mm; please adjust your irrigation schedule accordingly to avoid waterlogging."
        elif hum != "N/A" and hum > 80:
            rec += "High humidity has been detected. Please monitor the canopy closely for early signs of fungal diseases."
            
    return rec

