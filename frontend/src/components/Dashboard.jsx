import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { AlertTriangle, ArrowLeft, CheckCircle2, Eye, Info, Map, Satellite, Sprout, Download } from 'lucide-react';

const number = (value, digits = 1) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
const pct = (value) => `${number(value)}%`;

function Card({ title, icon, children, className = '' }) { return <section className={`data-card ${className}`}><h3>{icon}{title}</h3>{children}</section>; }
function Value({ label, value, detail, tone }) { return <div className="metric"><span>{label}</span><strong className={tone || ''}>{value}</strong>{detail && <small>{detail}</small>}</div>; }

export default function Dashboard({ results, onReset }) {
  const stats = results.stats || {}; const quality = results.quality || {}; const measurement = results.measurement || {};
  const maps = results.maps || {}; const yieldData = results.yield || {};
  const pie = [{ name: 'Higher vigour', value: Number(stats.healthy_pct) || 0, color: '#16794f' }, { name: 'Mixed vigour', value: Number(stats.moderate_pct) || 0, color: '#c58019' }, { name: 'Lower vigour', value: Number(stats.stressed_pct) || 0, color: '#c44736' }];
  const summary = stats.ndvi_summary || {};
  const mapItems = [
    ['rgb_map', 'True-colour composite', 'A visual reference only; colours are stretched for display.'],
    ['ndvi_map', 'NDVI vigour', 'Relative greenness and canopy response.'],
    ['stress_map', 'Vigour screening classes', 'Dynamic K-Means machine learning clustering.'],
    ['ndwi_map', 'NDWI context', 'Canopy/water-index context, not an irrigation volume.'],
  ];
  return <div className="dashboard">
    <div className="dashboard-top">
      <button className="back-button" onClick={onReset}><ArrowLeft size={17} /> New analysis</button>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span className="report-label">Field screening report</span>
        <button className="primary-button" onClick={() => window.print()} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', fontSize: '13px' }}><Download size={15} /> Download PDF</button>
      </div>
    </div>
    <header className="report-heading" style={{ justifyContent: 'flex-end', marginBottom: '16px' }}><div className="confidence-badge"><Eye size={20} /><span>Usable observations<strong>{quality.valid_observation_pct ?? '—'}%</strong></span></div></header>
    <section className="metric-grid" aria-label="Screening summary">
      <Value label="Higher vigour" value={pct(stats.healthy_pct)} detail="of vegetation pixels" tone="success" />
      <Value label="Mixed vigour" value={pct(stats.moderate_pct)} detail="of vegetation pixels" tone="warning" />
      <Value label="Lower vigour" value={pct(stats.stressed_pct)} detail="of vegetation pixels" tone="danger" />
      <Value label="Yield view" value={yieldData.text || 'Not available'} detail="Uncalibrated screening indicator" />
    </section>
    <div className="dashboard-layout">
      <div className="main-column">
        <Card title="Evidence & measurement" icon={<Satellite size={18} />}>
          <dl className="details-grid">
            <div><dt>Source</dt><dd>{measurement.sensor || 'Not recorded'}</dd></div>
            <div><dt>Imagery date</dt><dd>{measurement.imagery_date || results.image_date || 'Not recorded'}</dd></div>
            <div><dt>Analysis geometry</dt><dd>{measurement.geometry_type === 'bounding_box' ? 'Bounding box' : measurement.geometry_type || 'Not recorded'}</dd></div>
            <div><dt>Measured area</dt><dd>{measurement.area_hectares ? `${number(measurement.area_hectares, 2)} ha` : 'Not available'}</dd></div>
            <div><dt>Pixel scale</dt><dd>{measurement.analysis_resolution_m ? `~${number(measurement.analysis_resolution_m, 1)} m` : 'Not recorded'}</dd></div>
            <div><dt>Valid observations</dt><dd>{quality.valid_observation_pct != null ? `${number(quality.valid_observation_pct)}%` : 'Not recorded'}</dd></div>
          </dl>
          <div className="quality-callout"><CheckCircle2 size={18} /><div><strong>{quality.scl_available ? 'Scene-classification QA applied' : 'Limited QA available'}</strong><p>{quality.qa_method || 'Quality method was not recorded.'}</p></div></div>
        </Card>
        <Card title="NDVI summary" icon={<Map size={18} />}>
          <div className="ndvi-grid"><Value label="Mean" value={number(summary.mean, 3)} /><Value label="Median" value={number(summary.median, 3)} /><Value label="10th percentile" value={number(summary.p10, 3)} /><Value label="90th percentile" value={number(summary.p90, 3)} /></div>
          <p className="muted">Dynamic machine learning thresholds: stressed ≤ {stats.thresholds?.stressed ?? '0.30'}, mixed ≤ {stats.thresholds?.healthy ?? '0.60'}, higher &gt; {stats.thresholds?.healthy ?? '0.60'} (vegetation NDVI &gt; {stats.thresholds?.vegetation ?? '0.10'}).</p>
        </Card>
        <section className="map-section" style={{ marginTop: '0', paddingTop: '0', borderTop: 'none' }}><div><p className="eyebrow">Visual evidence</p><h2>Maps for locating field checks</h2></div><div className="map-grid">{mapItems.filter(([key]) => maps[key]).map(([key, title, description]) => <figure className="map-card" key={key}><img src={`data:image/jpeg;base64,${maps[key]}`} alt={title} /><figcaption><strong>{title}</strong><span>{description}</span></figcaption></figure>)}</div>{!mapItems.some(([key]) => maps[key]) && <p className="empty-state">Maps were not available for this analysis.</p>}</section>
      </div>
      <aside className="side-column">
        <Card title="Vigour distribution" icon={<Sprout size={18} />}>
          <div className="chart-wrap"><ResponsiveContainer width="100%" height={250}><PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={62} outerRadius={88} paddingAngle={3}>{pie.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip formatter={(value) => `${number(value)}%`} /><Legend /></PieChart></ResponsiveContainer></div>
          <div className="stat-strip"><span>Valid pixels <strong>{(stats.valid_pixels ?? 0).toLocaleString()}</strong></span><span>Vegetation pixels <strong>{(stats.vegetation_pixels ?? 0).toLocaleString()}</strong></span><span>Vegetation cover <strong>{pct(stats.vegetation_coverage)}</strong></span></div>
          <p className="muted">{stats.classification_note || 'Classes use transparent NDVI defaults.'}</p>
        </Card>

        <Card title="Recommended next check" icon={<Info size={18} />}>
          {Array.isArray(results.recommendation) && results.recommendation.length > 0 ? (
            <div className="recommendation-list">
              <p className="recommendation-text" style={{ marginBottom: '12px' }}><strong>{results.recommendation[0]}</strong></p>
              <ul className="limitations">
                {results.recommendation.slice(1).map((rec, i) => <li key={i}>{rec}</li>)}
              </ul>
            </div>
          ) : (
            <p className="recommendation-text">{results.recommendation || 'No recommendation was generated.'}</p>
          )}
        </Card>
        <Card title="Limitations" icon={<AlertTriangle size={18} />}><ul className="limitations">{(measurement.limitations || ['Interpret results alongside ground observations.']).map((item) => <li key={item}>{item}</li>)}</ul></Card>
      </aside>
    </div>
  </div>;
}
