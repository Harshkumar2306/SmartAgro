import React from 'react';
import { Sun, Cloud, CloudSun, CloudFog, CloudDrizzle, CloudRain, CloudLightning, Snowflake } from 'lucide-react';

const ICONS = {
  'sun': Sun,
  'cloud': Cloud,
  'cloud-sun': CloudSun,
  'cloud-fog': CloudFog,
  'cloud-drizzle': CloudDrizzle,
  'cloud-rain': CloudRain,
  'cloud-lightning': CloudLightning,
  'snowflake': Snowflake,
};

const COLORS = {
  'sun': '#f59e0b',
  'cloud': '#94a3b8',
  'cloud-sun': '#f59e0b',
  'cloud-fog': '#94a3b8',
  'cloud-drizzle': '#38bdf8',
  'cloud-rain': '#3b82f6',
  'cloud-lightning': '#f59e0b',
  'snowflake': '#93c5fd',
};

const WeatherIcon = ({ icon, size = 24 }) => {
  const Icon = ICONS[icon] || Cloud;
  return <Icon size={size} color={COLORS[icon] || '#94a3b8'} aria-hidden="true" />;
};

export default WeatherIcon;
