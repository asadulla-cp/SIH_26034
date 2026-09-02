import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  MapPin,
  Flame,
  ShieldCheck,
  ShieldAlert,
  Filter,
  Search,
  RefreshCw
} from 'lucide-react';
import { getGeoInspections } from '../api';
import type { GeoInspection } from '../types';

// Custom Pin Markers using Leaflet DivIcon
const createCustomMarker = (status: string) => {
  const color = status === 'COMPLIANT' ? '#10b981' : (status === 'NON_COMPLIANT' ? '#ef4444' : '#eab308');
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="
        background: ${color};
        width: 26px;
        height: 26px;
        border-radius: 50%;
        border: 3px solid #ffffff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="background:#fff; width:6px; height:6px; border-radius:50%;"></div>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -14]
  });
};

export const ComplianceMap: React.FC = () => {
  const navigate = useNavigate();
  const [inspections, setInspections] = useState<GeoInspection[]>([]);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadMapData();
  }, [statusFilter]);

  const loadMapData = async () => {
    try {
      const data = await getGeoInspections(statusFilter);
      setInspections(data);
    } catch (e) {
      console.error(e);
    }
  };

  const filtered = inspections.filter((i) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      i.product_name.toLowerCase().includes(term) ||
      i.inspection_id.toLowerCase().includes(term) ||
      (i.location_name && i.location_name.toLowerCase().includes(term))
    );
  });

  const compliantCount = filtered.filter((i) => i.overall_status === 'COMPLIANT').length;
  const nonCompliantCount = filtered.filter((i) => i.overall_status === 'NON_COMPLIANT').length;
  const compliantPct = filtered.length > 0 ? Math.round((compliantCount / filtered.length) * 100) : 0;

  return (
    <div className="animate-in">
      {/* Header */}
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <MapPin size={20} color="var(--accent-primary)" />
            <span style={{ fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-primary)', letterSpacing: '0.5px' }}>
              Geographic Intelligence Portal
            </span>
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 800 }}>Geo-Tagged Compliance & Violation Map</h2>
        </div>

        <button className="btn btn-secondary btn-sm" onClick={loadMapData}>
          <RefreshCw size={14} /> Refresh Map Data
        </button>
      </div>

      {/* Stats & Hotspot Summary Strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '20px' }}>
        <div className="card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'rgba(99,102,241,0.15)', padding: '10px', borderRadius: 'var(--radius-md)', color: '#6366f1' }}>
            <MapPin size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Total Plotted</div>
            <div style={{ fontSize: '20px', fontWeight: 800 }}>{filtered.length} Locations</div>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'rgba(16,185,129,0.15)', padding: '10px', borderRadius: 'var(--radius-md)', color: '#10b981' }}>
            <ShieldCheck size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Compliant Ratio</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#10b981' }}>{compliantCount} ({compliantPct}%)</div>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ background: 'rgba(239,68,68,0.15)', padding: '10px', borderRadius: 'var(--radius-md)', color: '#ef4444' }}>
            <ShieldAlert size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>Non-Compliant Violations</div>
            <div style={{ fontSize: '20px', fontWeight: 800, color: '#ef4444' }}>{nonCompliantCount}</div>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: '14px', borderLeft: '4px solid #f97316' }}>
          <div style={{ background: 'rgba(249,115,22,0.15)', padding: '10px', borderRadius: 'var(--radius-md)', color: '#f97316' }}>
            <Flame size={22} />
          </div>
          <div>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', color: '#f97316', fontWeight: 700 }}>Hotspot Alert</div>
            <div style={{ fontSize: '13px', fontWeight: 700, marginTop: '2px' }}>Sector 18 Market (2 Violations)</div>
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="card" style={{ padding: '14px 20px', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Filter size={16} color="var(--text-muted)" />
          <span style={{ fontSize: '12px', fontWeight: 700 }}>Status Filter:</span>
          {['ALL', 'COMPLIANT', 'NON_COMPLIANT', 'NEEDS_REVIEW'].map((st) => (
            <button
              key={st}
              className={`btn btn-sm ${statusFilter === st ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '11px', padding: '4px 10px' }}
              onClick={() => setStatusFilter(st)}
            >
              {st.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', width: '240px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search product or city..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 10px 6px 30px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-default)',
              background: 'var(--bg-elevated)',
              color: 'var(--text-primary)',
              fontSize: '12px'
            }}
          />
        </div>
      </div>

      {/* Interactive Leaflet Map Container */}
      <div className="card" style={{ padding: '4px', overflow: 'hidden', height: '580px', borderRadius: 'var(--radius-lg)' }}>
        <MapContainer
          center={[22.5937, 78.9629]}
          zoom={5}
          style={{ height: '100%', width: '100%', borderRadius: 'var(--radius-md)' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {filtered.map((item) => (
            <Marker
              key={item.id}
              position={[item.latitude, item.longitude]}
              icon={createCustomMarker(item.overall_status)}
            >
              <Popup>
                <div style={{ padding: '6px 4px', minWidth: '200px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: item.overall_status === 'COMPLIANT' ? '#10b981' : '#ef4444' }}>
                    {item.overall_status.replace('_', ' ')}
                  </div>
                  <h4 style={{ fontSize: '14px', fontWeight: 800, margin: '4px 0 2px' }}>{item.product_name}</h4>
                  <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '8px' }}>
                    {item.location_name ? item.location_name + ' &middot; ' : ''}
                    {item.latitude.toFixed(4)}°N, {item.longitude.toFixed(4)}°E
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', background: '#f1f5f9', padding: '6px 8px', borderRadius: '4px', marginBottom: '8px' }}>
                    <span>Score: <strong>{item.compliance_score}/100</strong></span>
                    <span>Risk: <strong style={{ color: item.risk_level === 'critical' ? '#ef4444' : '#10b981' }}>{item.risk_level.toUpperCase()}</strong></span>
                  </div>
                  <button
                    onClick={() => navigate(`/inspections/${item.id}`)}
                    style={{
                      width: '100%',
                      background: '#1e3a8a',
                      color: '#fff',
                      border: 'none',
                      padding: '6px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    View Inspection Record
                  </button>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
};
