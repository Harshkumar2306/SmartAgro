import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { ArrowLeft, Info, Droplets, ThermometerSun, MapPin, Calendar, Sprout, Wind, Map, Download } from 'lucide-react';
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";

const Dashboard = ({ results, onReset }) => {
  const { stats, yield: yieldData, recommendation, maps, image_date, mean_ndwi, context } = results;
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadPDF = async () => {
    setIsDownloading(true);
    try {
      const element = document.getElementById('dashboard-content');
      if (!element) return;
      
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        backgroundColor: '#0f172a' // match dark theme
      });
      
      const imgData = canvas.toDataURL('image/jpeg', 1.0);
      const pdf = new jsPDF('p', 'mm', 'a4');
      
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const imgHeight = (canvas.height * pdfWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;
      
      pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeight);
      heightLeft -= pageHeight;
      
      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 0, position, pdfWidth, imgHeight);
        heightLeft -= pageHeight;
      }
      
      pdf.save(`SmartAgro_Report_${image_date || 'latest'}.pdf`);
    } catch (err) {
      console.error("Failed to generate PDF", err);
    } finally {
      setIsDownloading(false);
    }
  };

  const pieData = [
    { name: 'Healthy', value: stats.healthy_pct, color: '#10b981' },
    { name: 'Moderate', value: stats.moderate_pct, color: '#f59e0b' },
    { name: 'Stressed', value: stats.stressed_pct, color: '#ef4444' },
  ];

  return (
    <div className="glass-panel" style={{ animation: 'fadeIn 0.5s ease-out' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <button 
          onClick={onReset} 
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}
        >
          <ArrowLeft size={18} /> Back to Selection
        </button>

        <button 
          onClick={handleDownloadPDF}
          disabled={isDownloading}
          style={{ 
            background: isDownloading ? '#64748b' : '#3b82f6', 
            border: 'none', 
            color: 'white', 
            cursor: isDownloading ? 'wait' : 'pointer', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem', 
            fontSize: '0.9rem', 
            padding: '0.6rem 1.2rem', 
            borderRadius: '8px', 
            fontWeight: '600',
            transition: 'background 0.2s'
          }}
        >
          <Download size={16} /> {isDownloading ? 'Generating PDF...' : 'Download Report'}
        </button>
      </div>

      <div id="dashboard-content" style={{ padding: '1rem', background: 'transparent' }}>
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <h2 style={{ color: '#fff', fontSize: '1.8rem', marginBottom: '0.5rem' }}>SmartAgro Dashboard</h2>
          <p style={{ color: '#94a3b8' }}>Comprehensive satellite insights and AI yield prediction</p>
        </div>

        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-title">Healthy Canopy</div>
            <div className="metric-value" style={{ color: '#10b981' }}>{stats.healthy_pct.toFixed(1)}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-title">Moderate Zone</div>
            <div className="metric-value" style={{ color: '#f59e0b' }}>{stats.moderate_pct.toFixed(1)}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-title">Stressed Zone</div>
            <div className="metric-value" style={{ color: '#ef4444' }}>{stats.stressed_pct.toFixed(1)}%</div>
          </div>
          <div className="metric-card" style={{ borderLeft: `4px solid ${yieldData.color}`, background: 'rgba(255,255,255,0.05)' }}>
            <div className="metric-title">Est. Yield Predictor</div>
            <div className="metric-value">{yieldData.text} {yieldData.emoji}</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
          
          {/* Left Column: Charts and Context */}
          <div>
            <div className="metric-card" style={{ height: '300px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc', textAlign: 'left' }}>Health Distribution</h3>
              <div style={{ flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip 
                      contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Legend verticalAlign="bottom" height={36} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="recommendation-box">
              <Info className="recommendation-icon" size={24} />
              <div>
                <h4 style={{ color: '#fff', marginBottom: '0.5rem', fontWeight: '600' }}>AI Action Plan</h4>
                <p style={{ lineHeight: '1.6', color: '#e2e8f0', fontSize: '0.95rem', whiteSpace: 'pre-wrap' }}>{recommendation}</p>
              </div>
            </div>
            
            {image_date && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '0.5rem' }}>Satellite Image Date</div>
                <div style={{ color: '#f8fafc', fontWeight: 'bold' }}>{image_date}</div>
              </div>
            )}

            {context && (
              <div className="metric-card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <MapPin size={18} color="#3b82f6" /> Environmental Context
                </h3>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Map size={14}/> Farm Size</span>
                    <span style={{ color: '#e2e8f0', fontWeight: '500' }}>{context.area_hectares} Hectares</span>
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    <span style={{ color: '#94a3b8', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Calendar size={14}/> Season</span>
                    <span style={{ color: '#e2e8f0', fontWeight: '500' }}>{context.season}</span>
                  </div>

                  {context.weather && (
                    <>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                        <span style={{ color: '#94a3b8', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><ThermometerSun size={14} color="#f59e0b"/> Temp</span>
                        <span style={{ color: '#e2e8f0', fontWeight: '500' }}>{context.weather.temperature_2m}°C</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                        <span style={{ color: '#94a3b8', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Droplets size={14} color="#3b82f6"/> Humidity</span>
                        <span style={{ color: '#e2e8f0', fontWeight: '500' }}>{context.weather.relative_humidity_2m}%</span>
                      </div>
                    </>
                  )}
                </div>

                {context.location?.state !== "Unknown" && (
                  <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                      <span style={{ color: '#94a3b8', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Sprout size={14} color="#10b981"/> Region: {context.location.state}</span>
                      {context.location.agri_data ? (
                        <span style={{ color: '#e2e8f0', fontSize: '0.9rem', lineHeight: '1.4' }}>
                          <strong>Soil:</strong> {context.location.agri_data.soil_type} <br/>
                          <strong>Best For:</strong> {context.location.agri_data.suitable_crops}
                        </span>
                      ) : (
                        <span style={{ color: '#e2e8f0', fontSize: '0.9rem' }}>Regional data not available for this state.</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Maps */}
          <div className="maps-grid" style={{ marginTop: 0 }}>
            {maps.rgb_map && (
              <div className="map-card">
                <h3>True Color Composite</h3>
                <img src={`data:image/png;base64,${maps.rgb_map}`} alt="RGB Map" className="map-image" />
              </div>
            )}
            
            {maps.ndvi_map && (
              <div className="map-card">
                <h3>NDVI (Vegetation Vigor)</h3>
                <img src={`data:image/png;base64,${maps.ndvi_map}`} alt="NDVI Map" className="map-image" />
              </div>
            )}

            {maps.stress_map && (
              <div className="map-card">
                <h3>ML Stress Management Zones</h3>
                <img src={`data:image/png;base64,${maps.stress_map}`} alt="Stress Map" className="map-image" />
              </div>
            )}

            {maps.ndwi_map && (
              <div className="map-card">
                <h3>NDWI (Moisture Index)</h3>
                <img src={`data:image/png;base64,${maps.ndwi_map}`} alt="NDWI Map" className="map-image" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
