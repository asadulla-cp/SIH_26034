import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Database, ArrowRight, Download, Trash2, MapPin } from 'lucide-react';
import { getInspections, getReportDownloadUrl, clearAllInspections } from '../api';
import type { Inspection } from '../types';

export const InspectionHistory: React.FC = () => {
  const navigate = useNavigate();
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [isClearing, setIsClearing] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    fetchList();
  }, [statusFilter]);

  const fetchList = async () => {
    try {
      setLoading(true);
      const res = await getInspections({
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setInspections(res.inspections);
      setTotal(res.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all inspection history and associated evidence records?')) {
      return;
    }
    try {
      setIsClearing(true);
      await clearAllInspections();
      await fetchList();
    } catch (err: any) {
      alert('Failed to clear history: ' + err.message);
    } finally {
      setIsClearing(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchList();
  };

  return (
    <div className="animate-in">
      <div className="page-header" style={{ background: 'transparent', padding: '0 0 20px 0', borderBottom: 'none', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2>Inspection Audit History</h2>
          <p>Complete historical log of all package compliance assessments & legal evidence records.</p>
        </div>

        {total > 0 && (
          <button
            className="btn btn-danger btn-sm"
            onClick={handleClearAll}
            disabled={isClearing}
          >
            <Trash2 size={14} /> Clear All History
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: '20px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ flex: 1, minWidth: '220px', position: 'relative' }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              className="input-field"
              placeholder="Search by product name or Inspection ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '36px' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className={`filter-chip ${statusFilter === '' ? 'active' : ''}`}
              onClick={() => setStatusFilter('')}
            >
              All ({total})
            </button>
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'COMPLIANT' ? 'active' : ''}`}
              onClick={() => setStatusFilter('COMPLIANT')}
            >
              Compliant
            </button>
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'NON_COMPLIANT' ? 'active' : ''}`}
              onClick={() => setStatusFilter('NON_COMPLIANT')}
            >
              Non-Compliant
            </button>
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'NEEDS_REVIEW' ? 'active' : ''}`}
              onClick={() => setStatusFilter('NEEDS_REVIEW')}
            >
              Needs Review
            </button>
          </div>

          <button type="submit" className="btn btn-primary btn-sm">
            Filter
          </button>
        </form>
      </div>

      {/* History Table */}
      <div className="card">
        {loading ? (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Loading historical records...</p>
          </div>
        ) : inspections.length === 0 ? (
          <div className="empty-state">
            <Database />
            <h3>No Records Found</h3>
            <p>Try clearing your search filters or scan a new package to generate data.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Inspection ID</th>
                <th>Product</th>
                <th>Status</th>
                <th>Compliance Score</th>
                <th>Violations</th>
                <th>Date & Time</th>
                <th>Report</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((item) => (
                <tr key={item.id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    {item.inspection_id}
                    {item.is_demo && (
                      <span style={{
                        marginLeft: '6px',
                        fontSize: '9px',
                        padding: '1px 4px',
                        background: 'rgba(245, 158, 11, 0.15)',
                        color: 'var(--status-review)',
                        borderRadius: '3px',
                        fontWeight: 700
                      }}>DEMO</span>
                    )}
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {item.product_name}
                  </td>
                  <td>
                    <span className={`status-badge ${item.overall_status.toLowerCase().replace('_', '-')}`}>
                      {item.overall_status.replace('_', ' ')}
                    </span>
                  </td>
                  <td>
                    <strong style={{
                      color: item.compliance_score >= 80 ? 'var(--status-pass)' : (item.compliance_score >= 50 ? 'var(--status-review)' : 'var(--status-fail)')
                    }}>
                      {item.compliance_score}%
                    </strong>
                  </td>
                  <td>
                    {item.failed_fields > 0 ? (
                      <span style={{ color: 'var(--status-fail)', fontWeight: 600 }}>
                        {item.failed_fields} Violation{item.failed_fields > 1 ? 's' : ''}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--status-pass)' }}>0 Violations</span>
                    )}
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                  </td>
                  <td>
                    <a
                      href={getReportDownloadUrl(item.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                    >
                      <Download size={12} /> PDF
                    </a>
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => navigate(`/inspections/${item.id}`)}
                        style={{ padding: '4px 10px', fontSize: '12px' }}
                      >
                        View <ArrowRight size={12} />
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/map?focus=${item.id}`)}
                        title="View on Compliance Map"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                      >
                        <MapPin size={12} color="#6366f1" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
