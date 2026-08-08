import { useState } from 'react';
import axios from 'axios';
import { FileImage, Info, Loader2, Upload } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function FileInput({ id, label, file, onChange }) {
  return <label className={`upload-card ${file ? 'ready' : ''}`} htmlFor={id}>
    <input id={id} type="file" accept=".tif,.tiff,image/tiff" onChange={(event) => onChange(event.target.files?.[0] || null)} />
    <FileImage size={28} aria-hidden="true" />
    <strong>{label}</strong>
    <span>{file ? file.name : 'Choose a GeoTIFF file'}</span>
    <em>{file ? 'Ready to analyse' : 'Required'}</em>
  </label>;
}

export default function LocalUploader({ setResults, setLoading, loading, setError }) {
  const [red, setRed] = useState(null); const [nir, setNir] = useState(null);
  const analyse = async () => {
    if (!red || !nir) return;
    setError(''); setLoading(true);
    const body = new FormData(); body.append('b04', red); body.append('b08', nir);
    try { const response = await axios.post(`${API_URL}/api/analyze-local`, body, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 }); setResults(response.data); }
    catch (error) { setError(error.response?.data?.detail || 'The files could not be analysed. Check that they are matching Red and NIR GeoTIFFs.'); }
    finally { setLoading(false); }
  };
  return <section className="upload-workflow" aria-label="Local GeoTIFF analysis">
    <div className="workflow-copy"><p className="eyebrow">Local imagery</p><h2>Upload calibrated bands</h2><p>Provide matching Sentinel-style Red (B04) and near-infrared (B08) GeoTIFFs. The service checks dimensions but cannot independently confirm acquisition, calibration or cloud masking.</p></div>
    <div className="upload-grid"><FileInput id="red-band" label="Red band · B04" file={red} onChange={setRed} /><FileInput id="nir-band" label="Near infrared · B08" file={nir} onChange={setNir} /></div>
    <div className="notice"><Info size={17} /><span>Only finite, positive pixels are used for local-file screening. Supply your own QA mask and field checks where possible.</span></div>
    <button className="primary-button upload-button" type="button" disabled={!red || !nir || loading} onClick={analyse}>{loading ? <><Loader2 className="spin" size={18} /> Analysing files</> : <><Upload size={18} /> Analyse local imagery</>}</button>
  </section>;
}
