import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, MapPin, Loader2, Wind, Droplets, Gauge, CloudRain,
  Thermometer, Sprout, AlertTriangle, CheckCircle2, Navigation, Sunrise, Sunset,
} from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Area, Bar, XAxis, YAxis,
  Tooltip as RechartsTooltip, Legend, CartesianGrid,
} from 'recharts';
import { searchLocations, fetchWeather, interpretWeatherCode, generateAdvisories, next24Hours } from '../lib/weather';
import WeatherIcon from './WeatherIcon';

const DEFAULT_LOCATION = { name: 'New Delhi', admin: 'Delhi, India', lat: 28.6139, lon: 77.209 };

const LEVEL_STYLES = {
  good: { border: 'rgba(16, 185, 129, 0.35)', bg: 'rgba(16, 185, 129, 0.08)', color: '#10b981', Icon: CheckCircle2 },
  warn: { border: 'rgba(245, 158, 11, 0.35)', bg: 'rgba(245, 158, 11, 0.08)', color: '#f59e0b', Icon: AlertTriangle },
  danger: { border: 'rgba(239, 68, 68, 0.35)', bg: 'rgba(239, 68, 68, 0.08)', color: '#ef4444', Icon: AlertTriangle },
};

const LiveWeather = () => {
  const [location, setLocation] = useState(DEFAULT_LOCATION);
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef(null);

  const loadWeather = useCallback(async (loc) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchWeather(loc.lat, loc.lon);
      setWeather(data);
    } catch (err) {
      console.error('Weather fetch failed', err);
      setError('Could not load live weather. Please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWeather(location);
    const interval = setInterval(() => loadWeather(location), 10 * 60 * 1000); // refresh every 10 min
    return () => clearInterval(interval);
  }, [location, loadWeather]);

  // Debounced location search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        setSuggestions(await searchLocations(query));
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          name: 'My Location',
          admin: `${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)}`,
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        });
        setQuery('');
        setSuggestions([]);
      },
      () => setError('Location access denied. Search for your farm location instead.')
    );
  };

  const selectSuggestion = (s) => {
    setLocation(s);
    setQuery('');
    setSuggestions([]);
  };

  const current = weather?.current;
  const daily = weather?.daily;
  const condition = current ? interpretWeatherCode(current.weather_code) : null;
  const advisories = weather ? generateAdvisories(weather) : [];
  const hourly = weather ? next24Hours(weather) : [];

  return (
    <div>
      {/* Search bar */}
      <div style={{ position: 'relative', display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 280px' }}>
          <Search size={18} color="#64748b" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search farm location (city, village, district)..."
            aria-label="Search location"
            style={{
              width: '100%', padding: '0.85rem 1rem 0.85rem 2.75rem', borderRadius: '10px',
              background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
              color: '#f8fafc', fontSize: '1rem', outline: 'none',
            }}
          />
          {(suggestions.length > 0 || searching) && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 50,
              background: '#1e293b', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px',
              overflow: 'hidden', boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
            }}>
              {searching && <div style={{ padding: '0.85rem 1rem', color: '#94a3b8', fontSize: '0.9rem' }}>Searching...</div>}
              {suggestions.map((s, i) => (
                <button
                  key={`${s.lat}-${s.lon}-${i}`}
                  onClick={() => selectSuggestion(s)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.6rem', width: '100%', textAlign: 'left',
                    padding: '0.85rem 1rem', background: 'none', border: 'none', cursor: 'pointer',
                    color: '#e2e8f0', fontSize: '0.95rem', borderBottom: '1px solid rgba(255,255,255,0.06)',
                  }}
                  onMouseOver={(e) => { e.currentTarget.style.background = 'rgba(59,130,246,0.15)'; }}
                  onMouseOut={(e) => { e.currentTarget.style.background = 'none'; }}
                >
                  <MapPin size={15} color="#3b82f6" />
                  <span><strong>{s.name}</strong>{s.admin ? <span style={{ color: '#94a3b8' }}> — {s.admin}</span> : null}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={handleUseMyLocation}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.85rem 1.25rem',
            borderRadius: '10px', background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.4)',
            color: '#60a5fa', fontWeight: 600, cursor: 'pointer', fontSize: '0.95rem',
          }}
        >
          <Navigation size={16} /> Use My Location
        </button>
      </div>

      {error && (
        <div style={{ padding: '1rem 1.25rem', borderRadius: '10px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {loading && !weather ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4rem 0', gap: '1rem' }}>
          <Loader2 className="spinner" size={48} color="#10b981" />
          <p style={{ color: '#94a3b8' }}>Fetching live weather data...</p>
        </div>
      ) : weather && current && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Current conditions hero */}
          <div className="metric-card" style={{ textAlign: 'left', padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1.5rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                  <MapPin size={16} color="#3b82f6" />
                  <span style={{ fontWeight: 600 }}>{location.name}</span>
                  {location.admin && <span style={{ fontSize: '0.85rem' }}>{location.admin}</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <WeatherIcon icon={condition.icon} size={56} />
                  <div>
                    <div style={{ fontSize: '3rem', fontWeight: 800, color: '#f8fafc', lineHeight: 1 }}>
                      {Math.round(current.temperature_2m)}°C
                    </div>
                    <div style={{ color: '#94a3b8', marginTop: '0.35rem' }}>
                      {condition.label} · Feels like {Math.round(current.apparent_temperature)}°C
                    </div>
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(130px, 1fr))', gap: '1rem', alignContent: 'center' }}>
                <MiniStat icon={<Droplets size={16} color="#3b82f6" />} label="Humidity" value={`${current.relative_humidity_2m}%`} />
                <MiniStat icon={<Wind size={16} color="#38bdf8" />} label="Wind" value={`${Math.round(current.wind_speed_10m)} km/h`} />
                <MiniStat icon={<CloudRain size={16} color="#60a5fa" />} label="Precipitation" value={`${current.precipitation ?? 0} mm`} />
                <MiniStat icon={<Gauge size={16} color="#f59e0b" />} label="Pressure" value={`${Math.round(current.surface_pressure)} hPa`} />
                {daily?.sunrise?.[0] && (
                  <MiniStat icon={<Sunrise size={16} color="#f59e0b" />} label="Sunrise" value={formatTime(daily.sunrise[0])} />
                )}
                {daily?.sunset?.[0] && (
                  <MiniStat icon={<Sunset size={16} color="#f97316" />} label="Sunset" value={formatTime(daily.sunset[0])} />
                )}
              </div>
            </div>
          </div>

          {/* Farm advisories */}
          {advisories.length > 0 && (
            <div>
              <h3 style={{ color: '#f8fafc', fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sprout size={20} color="#10b981" /> Smart Farming Advisories
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                {advisories.map((a, i) => {
                  const s = LEVEL_STYLES[a.level];
                  return (
                    <div key={i} style={{ padding: '1.25rem', borderRadius: '12px', background: s.bg, border: `1px solid ${s.border}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <s.Icon size={18} color={s.color} />
                        <span style={{ color: s.color, fontWeight: 700, fontSize: '0.95rem' }}>{a.title}</span>
                      </div>
                      <p style={{ color: '#cbd5e1', fontSize: '0.88rem', lineHeight: 1.55 }}>{a.detail}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 24-hour chart */}
          {hourly.length > 0 && (
            <div className="metric-card" style={{ textAlign: 'left', padding: '1.5rem' }}>
              <h3 style={{ color: '#f8fafc', fontSize: '1.15rem', fontWeight: 600, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Thermometer size={20} color="#f59e0b" /> Next 24 Hours
              </h3>
              <div style={{ height: '280px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={hourly}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={12} interval={3} />
                    <YAxis yAxisId="temp" stroke="#f59e0b" fontSize={12} unit="°" width={40} />
                    <YAxis yAxisId="rain" orientation="right" stroke="#3b82f6" fontSize={12} unit="%" width={40} domain={[0, 100]} />
                    <RechartsTooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                      itemStyle={{ color: '#fff' }}
                      labelStyle={{ color: '#94a3b8' }}
                    />
                    <Legend />
                    <Bar yAxisId="rain" dataKey="rainChance" name="Rain Chance (%)" fill="rgba(59,130,246,0.45)" radius={[3, 3, 0, 0]} />
                    <Area yAxisId="temp" type="monotone" dataKey="temp" name="Temperature (°C)" stroke="#f59e0b" fill="rgba(245,158,11,0.15)" strokeWidth={2} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Soil conditions */}
          {hourly.length > 0 && (hourly[0].soilTemp != null || hourly[0].soilMoisture != null) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
              {hourly[0].soilTemp != null && (
                <div className="metric-card">
                  <div className="metric-title">Soil Temp (6 cm)</div>
                  <div className="metric-value" style={{ color: '#f59e0b' }}>{hourly[0].soilTemp.toFixed(1)}°C</div>
                </div>
              )}
              {hourly[0].soilMoisture != null && (
                <div className="metric-card">
                  <div className="metric-title">Soil Moisture (3–9 cm)</div>
                  <div className="metric-value" style={{ color: '#38bdf8' }}>{(hourly[0].soilMoisture * 100).toFixed(0)}%</div>
                </div>
              )}
              {daily?.uv_index_max?.[0] != null && (
                <div className="metric-card">
                  <div className="metric-title">UV Index (Today Max)</div>
                  <div className="metric-value" style={{ color: daily.uv_index_max[0] >= 8 ? '#ef4444' : '#10b981' }}>{daily.uv_index_max[0].toFixed(1)}</div>
                </div>
              )}
              {daily?.et0_fao_evapotranspiration?.[0] != null && (
                <div className="metric-card">
                  <div className="metric-title">Evapotranspiration (Today)</div>
                  <div className="metric-value" style={{ color: '#3b82f6' }}>{daily.et0_fao_evapotranspiration[0].toFixed(1)} mm</div>
                </div>
              )}
            </div>
          )}

          {/* 7-day forecast */}
          {daily && (
            <div>
              <h3 style={{ color: '#f8fafc', fontSize: '1.15rem', fontWeight: 600, marginBottom: '1rem' }}>7-Day Forecast</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                {daily.time.map((day, i) => {
                  const cond = interpretWeatherCode(daily.weather_code[i]);
                  return (
                    <div key={day} className="metric-card" style={{ padding: '1.1rem 0.75rem' }}>
                      <div style={{ color: '#94a3b8', fontSize: '0.82rem', fontWeight: 600, marginBottom: '0.6rem' }}>
                        {i === 0 ? 'Today' : new Date(day).toLocaleDateString([], { weekday: 'short' })}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.6rem' }}>
                        <WeatherIcon icon={cond.icon} size={30} />
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginBottom: '0.5rem', minHeight: '2em' }}>{cond.label}</div>
                      <div style={{ fontWeight: 700, color: '#f8fafc' }}>
                        {Math.round(daily.temperature_2m_max[i])}° <span style={{ color: '#64748b', fontWeight: 500 }}>{Math.round(daily.temperature_2m_min[i])}°</span>
                      </div>
                      {daily.precipitation_probability_max?.[i] > 20 && (
                        <div style={{ marginTop: '0.4rem', fontSize: '0.78rem', color: '#60a5fa', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
                          <Droplets size={12} /> {daily.precipitation_probability_max[i]}%
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <p style={{ color: '#475569', fontSize: '0.8rem', textAlign: 'center' }}>
            Live data from Open-Meteo · Auto-refreshes every 10 minutes
          </p>
        </div>
      )}
    </div>
  );
};

const MiniStat = ({ icon, label, value }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
    <span style={{ color: '#94a3b8', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
      {icon} {label}
    </span>
    <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '1.05rem' }}>{value}</span>
  </div>
);

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default LiveWeather;
