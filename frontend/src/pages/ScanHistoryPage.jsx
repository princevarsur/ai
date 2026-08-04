import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Input, Select, Tag, Progress, message, Space, Empty } from 'antd';
import { complianceAPI } from '../services/api';
import ThemisMark from '../components/ThemisMark';

function getScoreColor(score) {
  if (score < 40) return '#A33F3F';   // danger / red
  if (score < 70) return '#A67C3D';   // warning / amber
  return '#4A7856';                   // success / green
}

function getRiskBadge(level = '') {
  const upper = level.toUpperCase();
  switch (upper) {
    case 'LOW':
      return <Tag color="#4A7856" style={{ fontWeight: 600, margin: 0 }}>LOW RISK</Tag>;
    case 'MEDIUM':
      return <Tag color="#A67C3D" style={{ fontWeight: 600, margin: 0 }}>MEDIUM RISK</Tag>;
    case 'HIGH':
      return <Tag color="#A33F3F" style={{ fontWeight: 600, margin: 0 }}>HIGH RISK</Tag>;
    case 'CRITICAL':
      return <Tag color="#801C1C" style={{ fontWeight: 700, margin: 0, background: '#801C1C', color: '#fff' }}>CRITICAL</Tag>;
    default:
      return <Tag>{upper || 'EVALUATED'}</Tag>;
  }
}

function getRiskWeight(level = '') {
  const upper = level.toUpperCase();
  if (upper === 'CRITICAL') return 4;
  if (upper === 'HIGH') return 3;
  if (upper === 'MEDIUM') return 2;
  if (upper === 'LOW') return 1;
  return 0;
}

export default function ScanHistoryPage() {
  const [reports, setReports]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchHistory() {
      setLoading(true);
      try {
        const res = await complianceAPI.getReports();
        const data = (res.data && res.data.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
        setReports(data);
      } catch (err) {
        message.error('Failed to load scan history reports.');
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, []);

  const filteredReports = reports.filter(item => {
    const matchesSearch = !searchTerm || (item.policy_title || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRisk = riskFilter === 'ALL' || (item.risk_level || '').toUpperCase() === riskFilter;
    return matchesSearch && matchesRisk;
  });

  const columns = [
    {
      title: 'Policy Document Name',
      dataIndex: 'policy_title',
      key: 'policy_title',
      sorter: (a, b) => (a.policy_title || '').localeCompare(b.policy_title || ''),
      render: (val, record) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '15px' }}>
            {val || 'Unnamed Employment Document'}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>
            Report ID: #{record.id}
          </div>
        </div>
      ),
      width: '35%',
    },
    {
      title: 'Compliance Score',
      dataIndex: 'overall_score',
      key: 'score',
      sorter: (a, b) => (a.overall_score || 0) - (b.overall_score || 0),
      render: (val) => {
        const score = Math.round(val || 0);
        const color = getScoreColor(score);
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '150px' }}>
            <span style={{ fontSize: '16px', fontWeight: 600, color, fontFamily: "'IBM Plex Mono', monospace", width: '45px' }}>
              {score}%
            </span>
            <Progress percent={score} showInfo={false} strokeColor={color} size="small" />
          </div>
        );
      },
      width: '18%',
    },
    {
      title: 'Risk Posture',
      dataIndex: 'risk_level',
      key: 'risk_level',
      sorter: (a, b) => getRiskWeight(a.risk_level) - getRiskWeight(b.risk_level),
      render: (val) => getRiskBadge(val),
      width: '15%',
    },
    {
      title: 'Clauses Tested',
      dataIndex: 'total_clauses',
      key: 'total_clauses',
      sorter: (a, b) => (a.total_clauses || 0) - (b.total_clauses || 0),
      render: (val) => (
        <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--ink-2)' }}>
          {val ?? '—'}
        </span>
      ),
      width: '12%',
    },
    {
      title: 'Flagged Issues',
      dataIndex: 'flagged_clauses',
      key: 'flagged_clauses',
      sorter: (a, b) => (a.flagged_clauses || 0) - (b.flagged_clauses || 0),
      render: (val) => {
        if (!val || val === 0) {
          return <Tag color="#4A7856" style={{ fontWeight: 600 }}>0 Flags</Tag>;
        }
        return <Tag color="#A33F3F" style={{ fontWeight: 600 }}>{val} Flag{val > 1 ? 's' : ''}</Tag>;
      },
      width: '12%',
    },
    {
      title: 'Date Scanned',
      dataIndex: 'scanned_at',
      key: 'date',
      defaultSortOrder: 'descend',
      sorter: (a, b) => new Date(a.scanned_at || 0) - new Date(b.scanned_at || 0),
      render: (val) => {
        if (!val) return '—';
        const d = new Date(val);
        return (
          <div style={{ fontSize: '13px', color: 'var(--muted)' }}>
            <div>{d.toLocaleDateString()}</div>
            <div style={{ fontSize: '11px', color: 'var(--muted-2)' }}>{d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
        );
      },
      width: '15%',
    },
  ];

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontFamily: "'Newsreader', serif", fontSize: '32px', color: 'var(--ink)', fontWeight: 500 }}>
          Scan History & Audit Ledger
        </h1>
        <p style={{ fontSize: '15px', color: 'var(--muted)', marginTop: '4px' }}>
          Chronological record of all statutory policy evaluations, compliance scores, and risk remediations across your organization.
        </p>
      </div>

      {/* Controls */}
      <div style={{ background: 'var(--surface)', padding: '20px 24px', borderRadius: '8px', border: '1px solid var(--hairline)', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <Input.Search
          placeholder="Filter by policy document name..."
          allowClear
          size="large"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ maxWidth: '450px' }}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Risk Level:
          </span>
          <Select
            size="large"
            value={riskFilter}
            onChange={setRiskFilter}
            style={{ width: 170 }}
            options={[
              { value: 'ALL', label: 'All Risk Levels' },
              { value: 'LOW', label: 'Low Risk' },
              { value: 'MEDIUM', label: 'Medium Risk' },
              { value: 'HIGH', label: 'High Risk' },
              { value: 'CRITICAL', label: 'Critical Risk' },
            ]}
          />
        </div>
      </div>

      {/* History Table */}
      <div style={{ background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--hairline)', padding: '12px 20px' }}>
        <Table
          columns={columns}
          dataSource={filteredReports}
          rowKey="id"
          loading={loading}
          onRow={(record) => ({
            onClick: () => navigate(`/reports/${record.id}`),
            style: { cursor: 'pointer', transition: 'background 0.15s' },
          })}
          pagination={{ pageSize: 15, showSizeChanger: true, pageSizeOptions: ['10', '15', '25', '50'], showTotal: (total) => `Total ${total} scan reports` }}
          locale={{
            emptyText: <Empty description="No compliance scan reports found" />
          }}
          style={{ background: 'transparent' }}
        />
      </div>
    </div>
  );
}
