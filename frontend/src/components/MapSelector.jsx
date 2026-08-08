import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import { GeoSearchControl, OpenStreetMapProvider } from 'leaflet-geosearch';
import 'leaflet/dist/leaflet.css';
import 'leaflet-geosearch/dist/geosearch.css';
import { CheckCircle2, Loader2, MapPinned, Ruler, Square } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_AOI_HA = 25000;

import turfArea from '@turf/area';

function MapTools({ onShape }) {
  const map = useMap();
  useEffect(() => {
    const search = new GeoSearchControl({ provider: new OpenStreetMapProvider(), style: 'bar', showMarker: false, autoClose: true, searchLabel: 'Search a farm or place' });
    map.addControl(search);
    map.pm.addControls({ position: 'topleft', drawMarker: false, drawCircleMarker: false, drawPolyline: false, drawPolygon: true, drawRectangle: true, drawCircle: false, drawText: false, editMode: true, dragMode: false, cutPolygon: false, removalMode: true });
    const update = (layer) => { 
      const b = layer.getBounds(); 
      const geojson = layer.toGeoJSON();
      onShape({
        bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
        geometry: geojson.geometry
      }); 
    };
    const create = (event) => {
      map.eachLayer((layer) => { if (layer.pm && layer !== event.layer && layer._path) layer.remove(); });
      update(event.layer);
      event.layer.on('pm:edit', () => update(event.layer));
    };
    const remove = () => onShape(null);
    map.on('pm:create', create); map.on('pm:remove', remove);
    return () => { map.off('pm:create', create); map.off('pm:remove', remove); map.removeControl(search); map.pm.removeControls(); };
  }, [map, onShape]);
  return null;
}



export default function MapSelector({ setResults, setLoading, loading, setError }) {
  const [shape, setShape] = useState(null);
  const [map, setMap] = useState(null);
  const [progress, setProgress] = useState('');
  const pollTimer = useRef(null);
  const areaHa = shape ? turfArea(shape.geometry) / 10000 : null;
  const selectShape = useCallback((next) => setShape(next), []);
  useEffect(() => () => window.clearTimeout(pollTimer.current), []);

  const autoBox = () => {
    if (!map) return;
    const centre = map.getCenter(); const offset = 0.01;
    map.eachLayer((layer) => { if (layer.pm && layer._path) layer.remove(); });
    const rectangle = L.rectangle([[centre.lat - offset, centre.lng - offset], [centre.lat + offset, centre.lng + offset]], { color: '#157a52', weight: 2 });
    rectangle.addTo(map); rectangle.pm.enable();
    const update = () => { 
      const b = rectangle.getBounds(); 
      setShape({
        bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
        geometry: rectangle.toGeoJSON().geometry
      }); 
    };
    update(); rectangle.on('pm:edit', update);
  };

  const analyse = async () => {
    if (!shape || areaHa > MAX_AOI_HA) return;
    setError(''); setLoading(true); setProgress('Submitting your polygon analysis…');
    try {
      const start = await axios.post(`${API_URL}/api/analyze-async`, { bbox: shape.bbox, geometry: shape.geometry, field_area_ha: areaHa }, { timeout: 120000 });
      const jobId = start.data.job_id; let attempts = 0;
      const poll = async () => {
        try {
          const response = await axios.get(`${API_URL}/api/status/${jobId}`, { timeout: 20000 });
          if (response.data.status === 'completed') { setResults(response.data.data); setLoading(false); return; }
          if (response.data.status === 'error') { setError(response.data.detail || 'The analysis could not be completed.'); setLoading(false); return; }
          attempts += 1;
          setProgress(['Finding a Sentinel-2 scene…', 'Reading reflectance and quality layers…', 'Masking unusable observations…', 'Summarising vigour and preparing maps…'][Math.min(Math.floor(attempts / 2), 3)]);
          pollTimer.current = window.setTimeout(poll, 3000);
        } catch (error) {
          if (attempts < 8) { attempts += 1; setProgress(`Reconnecting to the analysis service (${attempts}/8)…`); pollTimer.current = window.setTimeout(poll, 4000); }
          else { setError(error.response?.data?.detail || 'The analysis service did not respond. Please try again.'); setLoading(false); }
        }
      };
      pollTimer.current = window.setTimeout(poll, 2000);
    } catch (error) { setError(error.response?.data?.detail || 'Unable to start the satellite analysis.'); setLoading(false); }
  };

  return <section className="selection-layout" aria-label="Satellite area selection">
    <div className="map-stage">
      <MapContainer ref={setMap} center={[20.5937, 78.9629]} zoom={5} className="leaflet-map">
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" attribution="Tiles © Esri and contributors" />
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}" attribution="" />
        <MapTools onShape={selectShape} />
      </MapContainer>
      {loading && <div className="map-progress" role="status"><Loader2 className="spin" size={22} /><div><strong>Analysis in progress</strong><span>{progress}</span></div></div>}
    </div>
    <aside className="selection-panel">
      <div className="step-heading"><span>1</span><div><p className="eyebrow">Select area</p><h2>Draw a field extent</h2></div></div>
      <p>Use the map controls to draw a rectangle or polygon. <strong>Your exact drawn polygon boundaries will be analyzed</strong>, masking out any surrounding noise.</p>
      <button type="button" className="secondary-button" onClick={autoBox}><Square size={16} /> Add a small box at map centre</button>
      <div className={`aoi-summary ${shape ? 'selected' : ''}`} aria-live="polite">
        {shape ? <><CheckCircle2 size={19} /><div><strong>Polygon selected</strong><span><Ruler size={14} /> {areaHa.toLocaleString(undefined, { maximumFractionDigits: 2 })} ha exact area</span><small>Bounds: W {shape.bbox[0].toFixed(5)} · S {shape.bbox[1].toFixed(5)} · E {shape.bbox[2].toFixed(5)} · N {shape.bbox[3].toFixed(5)}</small></div></> : <><MapPinned size={19} /><div><strong>No area selected</strong><span>Draw on the map to continue.</span></div></>}
      </div>
      {areaHa > MAX_AOI_HA && <div className="status-message error" role="alert">This area is above the {MAX_AOI_HA.toLocaleString()} ha analysis limit. Draw a smaller polygon.</div>}

      <button className="primary-button" type="button" onClick={analyse} disabled={!shape || loading || areaHa > MAX_AOI_HA}>{loading ? <><Loader2 className="spin" size={18} /> Analysing satellite data</> : 'Run field screening'}</button>
    </aside>
  </section>;
}
