import axios from 'axios';

// ---------- Open-Meteo API helpers (free, no API key required) ----------

const FORECAST_URL = 'https://api.open-meteo.com/v1/forecast';
const GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search';

/**
 * Search for a location by name (Open-Meteo geocoding).
 */
export async function searchLocations(query) {
  if (!query || query.trim().length < 2) return [];
  const res = await axios.get(GEOCODE_URL, {
    params: { name: query.trim(), count: 6, language: 'en', format: 'json' },
    timeout: 10000,
  });
  return (res.data.results || []).map((r) => ({
    name: r.name,
    admin: [r.admin1, r.country].filter(Boolean).join(', '),
    lat: r.latitude,
    lon: r.longitude,
  }));
}

/**
 * Fetch full live weather data for a coordinate:
 * current conditions, 24h hourly detail, and 7-day daily forecast.
 */
export async function fetchWeather(lat, lon) {
  const res = await axios.get(FORECAST_URL, {
    params: {
      latitude: lat,
      longitude: lon,
      current: [
        'temperature_2m',
        'relative_humidity_2m',
        'apparent_temperature',
        'precipitation',
        'weather_code',
        'wind_speed_10m',
        'wind_direction_10m',
        'wind_gusts_10m',
        'surface_pressure',
        'cloud_cover',
        'is_day',
      ].join(','),
      hourly: [
        'temperature_2m',
        'relative_humidity_2m',
        'precipitation_probability',
        'precipitation',
        'wind_speed_10m',
        'soil_temperature_6cm',
        'soil_moisture_3_to_9cm',
        'et0_fao_evapotranspiration',
        'uv_index',
      ].join(','),
      daily: [
        'weather_code',
        'temperature_2m_max',
        'temperature_2m_min',
        'precipitation_sum',
        'precipitation_probability_max',
        'wind_speed_10m_max',
        'uv_index_max',
        'et0_fao_evapotranspiration',
        'sunrise',
        'sunset',
      ].join(','),
      timezone: 'auto',
      forecast_days: 7,
    },
    timeout: 15000,
  });
  return res.data;
}

// ---------- WMO weather code interpretation ----------

const WMO_CODES = {
  0: { label: 'Clear Sky', icon: 'sun' },
  1: { label: 'Mainly Clear', icon: 'sun' },
  2: { label: 'Partly Cloudy', icon: 'cloud-sun' },
  3: { label: 'Overcast', icon: 'cloud' },
  45: { label: 'Fog', icon: 'cloud-fog' },
  48: { label: 'Rime Fog', icon: 'cloud-fog' },
  51: { label: 'Light Drizzle', icon: 'cloud-drizzle' },
  53: { label: 'Drizzle', icon: 'cloud-drizzle' },
  55: { label: 'Heavy Drizzle', icon: 'cloud-drizzle' },
  61: { label: 'Light Rain', icon: 'cloud-rain' },
  63: { label: 'Rain', icon: 'cloud-rain' },
  65: { label: 'Heavy Rain', icon: 'cloud-rain' },
  66: { label: 'Freezing Rain', icon: 'cloud-rain' },
  67: { label: 'Freezing Rain', icon: 'cloud-rain' },
  71: { label: 'Light Snow', icon: 'snowflake' },
  73: { label: 'Snow', icon: 'snowflake' },
  75: { label: 'Heavy Snow', icon: 'snowflake' },
  77: { label: 'Snow Grains', icon: 'snowflake' },
  80: { label: 'Light Showers', icon: 'cloud-rain' },
  81: { label: 'Showers', icon: 'cloud-rain' },
  82: { label: 'Violent Showers', icon: 'cloud-rain' },
  85: { label: 'Snow Showers', icon: 'snowflake' },
  86: { label: 'Snow Showers', icon: 'snowflake' },
  95: { label: 'Thunderstorm', icon: 'cloud-lightning' },
  96: { label: 'Storm + Hail', icon: 'cloud-lightning' },
  99: { label: 'Storm + Hail', icon: 'cloud-lightning' },
};

export function interpretWeatherCode(code) {
  return WMO_CODES[code] || { label: 'Unknown', icon: 'cloud' };
}

// ---------- Agronomic advisory engine ----------

/**
 * Generate smart farming advisories from live weather data.
 * Returns an array of { level: 'good'|'warn'|'danger', title, detail }.
 */
export function generateAdvisories(weather) {
  if (!weather?.current || !weather?.daily) return [];

  const advisories = [];
  const c = weather.current;
  const d = weather.daily;

  // --- Spray window (wind + rain) ---
  const rainNext24 = sumNext24(weather, 'precipitation');
  if (c.wind_speed_10m <= 15 && rainNext24 < 1 && c.temperature_2m > 5 && c.temperature_2m < 32) {
    advisories.push({
      level: 'good',
      title: 'Good Spraying Window',
      detail: `Wind is ${Math.round(c.wind_speed_10m)} km/h with minimal rain expected in the next 24h. Ideal conditions for pesticide or foliar application.`,
    });
  } else if (c.wind_speed_10m > 20) {
    advisories.push({
      level: 'warn',
      title: 'Avoid Spraying — High Wind',
      detail: `Wind speed is ${Math.round(c.wind_speed_10m)} km/h. Spray drift risk is high; postpone chemical application until winds drop below 15 km/h.`,
    });
  } else if (rainNext24 >= 5) {
    advisories.push({
      level: 'warn',
      title: 'Rain Will Wash Off Sprays',
      detail: `About ${rainNext24.toFixed(1)} mm of rain is expected in the next 24h. Delay foliar sprays to avoid wash-off and runoff losses.`,
    });
  }

  // --- Irrigation guidance (rain + ET0) ---
  const rain7d = d.precipitation_sum.reduce((a, b) => a + (b || 0), 0);
  const et7d = (d.et0_fao_evapotranspiration || []).reduce((a, b) => a + (b || 0), 0);
  const deficit = et7d - rain7d;
  if (deficit > 15) {
    advisories.push({
      level: 'danger',
      title: 'Irrigation Needed',
      detail: `7-day evapotranspiration (${et7d.toFixed(0)} mm) will exceed rainfall (${rain7d.toFixed(0)} mm) by ~${deficit.toFixed(0)} mm. Schedule irrigation to prevent moisture stress.`,
    });
  } else if (rain7d > 60) {
    advisories.push({
      level: 'warn',
      title: 'Waterlogging Risk',
      detail: `${rain7d.toFixed(0)} mm of rain is forecast this week. Check field drainage and delay irrigation to avoid waterlogging and root rot.`,
    });
  } else {
    advisories.push({
      level: 'good',
      title: 'Water Balance OK',
      detail: `Forecast rainfall (${rain7d.toFixed(0)} mm) roughly matches crop water demand (${et7d.toFixed(0)} mm ET) this week.`,
    });
  }

  // --- Frost alert ---
  const minTemp = Math.min(...d.temperature_2m_min);
  if (minTemp <= 2) {
    advisories.push({
      level: 'danger',
      title: 'Frost Alert',
      detail: `Minimum temperature will drop to ${minTemp.toFixed(1)}°C this week. Protect sensitive crops with irrigation, mulch, or row covers.`,
    });
  }

  // --- Heat stress ---
  const maxTemp = Math.max(...d.temperature_2m_max);
  if (maxTemp >= 40) {
    advisories.push({
      level: 'danger',
      title: 'Extreme Heat Stress',
      detail: `Temperatures will reach ${maxTemp.toFixed(0)}°C. Increase irrigation frequency and avoid midday field operations. Flowering crops may abort.`,
    });
  } else if (maxTemp >= 35) {
    advisories.push({
      level: 'warn',
      title: 'Heat Stress Watch',
      detail: `Peak temperature of ${maxTemp.toFixed(0)}°C expected. Consider light evening irrigation to cool the canopy.`,
    });
  }

  // --- Fungal disease pressure (humidity + temp) ---
  if (c.relative_humidity_2m >= 80 && c.temperature_2m >= 20 && c.temperature_2m <= 32) {
    advisories.push({
      level: 'danger',
      title: 'High Fungal Disease Pressure',
      detail: `Humidity at ${c.relative_humidity_2m}% with warm temperatures creates ideal conditions for blight, rust, and mildew. Scout fields and consider preventive fungicide.`,
    });
  }

  // --- Storm warning ---
  const stormCode = d.weather_code.some((wc) => wc >= 95);
  if (stormCode) {
    advisories.push({
      level: 'danger',
      title: 'Thunderstorm / Hail Risk',
      detail: 'Thunderstorms are forecast this week. Secure equipment, harvest mature crops early if possible, and check hail insurance coverage.',
    });
  }

  return advisories;
}

function sumNext24(weather, key) {
  const values = weather.hourly?.[key];
  const times = weather.hourly?.time;
  if (!values || !times) return 0;
  const now = Date.now();
  let sum = 0;
  for (let i = 0; i < times.length; i++) {
    const t = new Date(times[i]).getTime();
    if (t >= now && t <= now + 24 * 3600 * 1000) sum += values[i] || 0;
  }
  return sum;
}

/**
 * Extract the next 24 hours of hourly data for charting.
 */
export function next24Hours(weather) {
  const h = weather?.hourly;
  if (!h?.time) return [];
  const now = Date.now();
  const rows = [];
  for (let i = 0; i < h.time.length && rows.length < 24; i++) {
    const t = new Date(h.time[i]).getTime();
    if (t < now - 3600 * 1000) continue;
    rows.push({
      time: new Date(h.time[i]).toLocaleTimeString([], { hour: 'numeric' }),
      temp: h.temperature_2m?.[i],
      humidity: h.relative_humidity_2m?.[i],
      rainChance: h.precipitation_probability?.[i],
      rain: h.precipitation?.[i],
      wind: h.wind_speed_10m?.[i],
      soilTemp: h.soil_temperature_6cm?.[i],
      soilMoisture: h.soil_moisture_3_to_9cm?.[i],
    });
  }
  return rows;
}
