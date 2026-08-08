"""Yield-facing output deliberately limited to an uncalibrated vigour indicator."""


def estimate_yield(healthy_percentage, ndwi_mean=None, temp=None, rain=None, veg_coverage=None):
    """Return a screening indicator, never a yield quantity.

    A yield prediction requires crop-, cultivar-, management-, soil- and
    field-calibrated observations. Those inputs are not available in this API,
    so the legacy return shape is retained while its content is scientifically
    honest.
    """
    if veg_coverage is not None and veg_coverage < 2.0:
        return "Vigour indicator: insufficient canopy", "◌", "#64748b", None

    score = float(healthy_percentage or 0)
    if ndwi_mean is not None:
        if ndwi_mean < -0.1:
            score -= 12
        elif ndwi_mean > 0.35:
            score -= 8

    if score >= 65:
        return "Vigour indicator: higher", "↑", "#15803d", round(score, 1)
    if score >= 35:
        return "Vigour indicator: mixed", "↔", "#b45309", round(score, 1)
    return "Vigour indicator: lower", "↓", "#b91c1c", round(score, 1)
