import React, { useState, useEffect } from 'react';
import { CloudSun, Droplets, Loader2 } from 'lucide-react';
import { fetchWeather, interpretWeatherCode, generateAdvisories } from '../lib/weather';
import WeatherIcon from './WeatherIcon';

/**
 * Compact 7-day live forecast for the analyzed farm area (Dashboard view).
 * Receives the farm bbox [W, S, E, N] and fetches forecast for its center.
 */
const ForecastStrip = ({ bbox }) => {
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!bbox) return;
    const lat = (bbox[1] + bbox[3]) / 2;
    const lon = (bbox[0] + bbox[2]) / 2;
    let cancelled = false;
    fetchWeather(lat, lon)
      .then((data) => { if (!cancelled) setWeather(data); })
      .catch((err) => console.error('Forecast fetch failed', err))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [bbox]);

  if (!bbox) return null;

  const daily = weather?.daily;
  const advisories = weather ? generateAdvisories(weather).filter((a) => a.level !== 'good').slice(0, 2) : [];

  return (
    <div className="metric-card" style={{ textAlign: 'left', padding: '1.5rem' }}>
      <h3 style={{ fontSize: '1.15rem', marginBottom: '1.25rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
        <CloudSun size={20} color="#f59e0b" /> Live 7-Day Farm Forecast
      </h3>

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#94a3b8', padding: '1rem 0' }}>
          <Loader2 className="spinner" size={20} /> Loading live forecast...
        </div>
      ) : daily ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '0.5rem' }}>
            {daily.time.map((day, i) => {
              const cond = interpretWeatherCode(daily.weather_code[i]);
              return (
                <div key={day} style={{ textAlign: 'center', padding: '0.6rem 0.25rem', borderRadius: '10px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ color: '#94a3b8', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                    {i === 0 ? 'Today' : new Date(day).toLocaleDateString([], { weekday: 'short' })}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.4rem' }}>
                    <WeatherIcon icon={cond.icon} size={22} />
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f8fafc' }}>
                    {Math.round(daily.temperature_2m_max[i])}°
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{Math.round(daily.temperature_2m_min[i])}°</div>
                  {daily.precipitation_probability_max?.[i] > 20 && (
                    <div style={{ marginTop: '0.25rem', fontSize: '0.7rem', color: '#60a5fa', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.15rem' }}>
                      <Droplets size={10} /> {daily.precipitation_probability_max[i]}%
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {advisories.length > 0 && (
            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {advisories.map((a, i) => (
                <div key={i} style={{
                  padding: '0.65rem 0.9rem', borderRadius: '8px', fontSize: '0.85rem', lineHeight: 1.5,
                  background: a.level === 'danger' ? 'rgba(239,68,68,0.08)' : 'rgba(245,158,11,0.08)',
                  border: `1px solid ${a.level === 'danger' ? 'rgba(239,68,68,0.3)' : 'rgba(245,158,11,0.3)'}`,
                  color: '#cbd5e1',
                }}>
                  <strong style={{ color: a.level === 'danger' ? '#ef4444' : '#f59e0b' }}>{a.title}:</strong> {a.detail}
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Live forecast unavailable for this location.</p>
      )}
    </div>
  );
};

export default ForecastStrip;
