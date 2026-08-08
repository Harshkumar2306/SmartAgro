def run_deep_analysis(context, stats, mean_ndwi):
    """
    Synthesizes Location, Land Type, Season, Atmosphere, and Satellite parameters
    into a comprehensive mathematical Agronomic Suitability Engine.
    """
    analysis = {
        "suitability_score": 100,
        "limiting_factors": [],
        "positive_factors": [],
        "soil_impact": "",
        "atmospheric_impact": ""
    }

    veg_coverage = stats.get('vegetation_coverage', 0)
    if veg_coverage < 2.0:
        analysis["suitability_score"] = 0
        analysis["limiting_factors"].append("Extremely low vegetation coverage (Barren/Harvested/Water).")
        analysis["soil_impact"] = "Unable to assess soil synergy without active canopy."
        analysis["atmospheric_impact"] = "Atmospheric conditions irrelevant for barren land."
        return analysis

    # 1. Location & Land Type Extraction
    loc = context.get("location") or {}
    state = loc.get("state", "Unknown")
    agri_data = loc.get("agri_data", {})
    soil_type = agri_data.get("soil_type", "Unknown") if agri_data else "Unknown"

    # 2. Atmospheric & Seasonal Extraction
    weather = context.get("weather") or {}
    temp = weather.get("temperature_2m", 25)
    rain = weather.get("precipitation", 0)
    hum = weather.get("relative_humidity_2m", 50)
    season = context.get("season", "Unknown")
    
    # --- SCORING HEURISTICS ---
    
    # A. Temperature vs Season Synergy
    if season == "Kharif (Monsoon)":
        if temp > 38:
            analysis["suitability_score"] -= 15
            analysis["limiting_factors"].append(f"Heat Stress: Kharif season optimal max is ~35°C, current is {temp}°C.")
        elif temp < 20:
            analysis["suitability_score"] -= 10
            analysis["limiting_factors"].append(f"Cold Stress: Kharif crops require higher base temperatures.")
        else:
            analysis["positive_factors"].append("Temperature is highly optimal for Kharif growth phase.")
    elif season == "Rabi (Winter)":
        if temp > 30:
            analysis["suitability_score"] -= 20
            analysis["limiting_factors"].append(f"Heat Stress: Rabi crops (like Wheat) require cool temperatures. {temp}°C is detrimental.")
        elif temp < 5:
            analysis["suitability_score"] -= 15
            analysis["limiting_factors"].append("Frost Risk: Temperatures dropping too low for optimal physiological development.")
        else:
            analysis["positive_factors"].append("Temperature perfectly aligns with Rabi chilling requirements.")

    # B. Soil Type vs Moisture Synergy (Atmospheric + Satellite)
    if "Black" in soil_type or "Regur" in soil_type:
        analysis["soil_impact"] = "Black Soil (Regur) has high water retention."
        if rain > 50 or mean_ndwi > 0.3:
            analysis["suitability_score"] -= 25
            analysis["limiting_factors"].append("Waterlogging Risk: Heavy moisture on high-retention Black soil leads to root rot.")
        elif mean_ndwi < -0.1:
            analysis["positive_factors"].append("Black soil's deep moisture reserve is mitigating surface drought symptoms.")
    elif "Sandy" in soil_type or "Red" in soil_type or "Laterite" in soil_type:
        analysis["soil_impact"] = f"{soil_type} drains rapidly and requires frequent irrigation."
        if mean_ndwi < 0 and rain == 0:
            analysis["suitability_score"] -= 30
            analysis["limiting_factors"].append(f"Severe Drought Risk: Fast-draining {soil_type} combined with negative NDWI requires immediate massive irrigation.")
        elif rain > 10:
            analysis["positive_factors"].append("Recent rainfall is highly beneficial for fast-draining porous soil.")
    else:
        analysis["soil_impact"] = "Standard Loam/Alluvial properties assumed."
        if mean_ndwi < -0.2:
            analysis["suitability_score"] -= 20
            analysis["limiting_factors"].append("Drought Stress: Canopy moisture is critically low.")

    # C. Atmospheric Impact
    if hum > 85 and temp > 25:
        analysis["atmospheric_impact"] = "Oppressive humidity and heat creating prime fungal/pest breeding grounds."
        analysis["suitability_score"] -= 10
        analysis["limiting_factors"].append("High atmospheric humidity increases blight/pathogen risk.")
    elif hum < 20 and temp > 35:
        analysis["atmospheric_impact"] = "Extremely arid. Rapid transpiration is stressing the canopy."
        analysis["suitability_score"] -= 15
        analysis["limiting_factors"].append("Vapor Pressure Deficit is too high. Plants will close stomata, halting growth.")
    else:
        analysis["atmospheric_impact"] = "Atmospheric conditions are stable and conducive to transpiration."

    # D. Satellite Health Validation
    healthy = stats.get('healthy_pct', 0)
    stressed = stats.get('stressed_pct', 0)
    if healthy > 70:
        analysis["positive_factors"].append(f"Satellite confirms excellent biomass vigor ({healthy:.1f}%).")
        analysis["suitability_score"] = min(100, analysis["suitability_score"] + 10)
    elif stressed > 40:
        analysis["limiting_factors"].append(f"Satellite confirms widespread tissue stress ({stressed:.1f}%).")
        analysis["suitability_score"] -= 20

    # Ensure bounds
    analysis["suitability_score"] = max(0, min(100, int(analysis["suitability_score"])))
    
    # If perfect score, ensure positive feedback exists
    if len(analysis["limiting_factors"]) == 0:
        analysis["limiting_factors"].append("None detected. Growth conditions are optimal.")

    return analysis
