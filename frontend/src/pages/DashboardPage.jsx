import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, Statistic, Table, Button, Skeleton, Tag, Empty } from 'antd';
import {
  LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer,
  ReferenceArea, PieChart, Pie, Cell, Legend
} from 'recharts';
import { complianceAPI } from '../services/api';

// Helper for score colors: 0-39 = red, 40-69 = amber, 70-100 = green
function getScoreColor(score) {
  if (score < 40) return 'var(--danger)';   // #A33F3F
  if (score < 70) return 'var(--warning)';  // #A67C3D
  return 'var(--success)';                  // #4A7856
}

// Helper for risk level tag formatting
function getRiskTag(level = '') {
  const upper = (level || '').toUpperCase();
  switch (upper) {
    case 'LOW':
      return <Tag color="#4A7856" style={{ fontWeight: 600, margin: 0 }}>LOW</Tag>;
    case 'MEDIUM':
      return <Tag color="#A67C3D" style={{ fontWeight: 600, margin: 0 }}>MEDIUM</Tag>;
    case 'HIGH':
      return <Tag color="#A33F3F" style={{ fontWeight: 600, margin: 0 }}>HIGH</Tag>;
    case 'CRITICAL':
      return <Tag color="#801C1C" style={{ fontWeight: 700, margin: 0, background: '#801C1C', color: '#fff' }}>CRITICAL</Tag>;
    default:
      return <Tag>{upper || 'PENDING'}</Tag>;
  }
}

// Desaturated palette for domain category charts
const CATEGORY_COLORS = ['#334155', '#4A7856', '#A67C3D', '#A33F3F', '#5F6C7B', '#8C7A6B', '#4C586F'];

export default function DashboardPage() {
  const navigate = useNavigate();

  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    async function fetchDashboardData() {
      setLoading(true);
      try {
        const res = await complianceAPI.getDashboard();
        setStats(res.data);
      } catch (err) {
        const msg = err.response?.data?.detail || 'Failed to retrieve compliance metrics.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    }
    fetchDashboardData();
  }, []);

  // ── SKELETON LOADING STATE ──────────────────────────────────────
  if (loading) {
    return (
      <div style={{ maxWidth: 1140, margin: '0 auto', padding: '16px 0' }}>
        <Skeleton active paragraph={{ rows: 1 }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, margin: '24px 0' }}>
          {[1, 2, 3, 4].map(i => <Skeleton.Button key={i} active style={{ width: '100%', height: 110 }} />)}
        </div>
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    );
  }

  // ── EMPTY STATE (No Scans Yet) ──────────────────────────────────
  const isZeroState = !stats || (stats.total_policies_scanned === 0 && (!stats.recent_scans || stats.recent_scans.length === 0));
  if (isZeroState) {
    return (
      <div style={{ maxWidth: 840, margin: '48px auto', textAlign: 'center', animation: 'fadeIn 300ms ease-out' }}>
        <div className="panel" style={{ padding: '64px 32px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%', background: 'var(--surface)',
              border: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--accent)', fontSize: 28
            }}>
              ⚖️
            </div>
          </div>
          <h1 style={{ fontFamily: "'Newsreader', serif", fontSize: 28, color: 'var(--ink)', marginBottom: 8 }}>
            Welcome to THEMIS Compliance Workspace
          </h1>
          <p style={{ maxWidth: 440, margin: '0 auto 28px', color: 'var(--muted)', fontSize: 15 }}>
            You haven't scanned any policy handbooks or legal contracts yet. Upload your first document to begin automated regulatory evaluation.
          </p>
          <Link to="/upload">
            <Button type="primary" size="large" style={{ background: 'var(--accent)', height: 44, padding: '0 28px', fontWeight: 500 }}>
              &uarr; Upload Your First Policy
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // ── DATA PREPARATION FOR CHARTS ────────────────────────────────
  // 1. Line chart trend data from recent scans (sorted earliest to newest)
  const trendData = (stats.recent_scans || [])
    .slice()
    .reverse()
    .map((report, i) => ({
      name: report.scanned_at ? new Date(report.scanned_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : `Scan #${i + 1}`,
      score: Math.round(report.overall_score || 0),
      title: report.policy_title || `Policy #${report.id}`,
    }));

  // If only 1 scan exists, duplicate point so line renders properly
  if (trendData.length === 1) {
    trendData.unshift({ ...trendData[0], name: 'Start' });
  }

  // 2. Pie chart category distribution
  const rawCat = stats.issues_by_category || {};
  const labelMap = {
    labour: 'Labour Law',
    data_privacy: 'Data Privacy',
    workplace_safety: 'POSH & Safety',
    employee_benefits: 'Gratuity / Benefits',
    corporate_governance: 'Governance',
    cyber_security: 'Cyber Security',
    general: 'General Handbooks',
  };

  const categoryData = Object.keys(rawCat).map(key => ({
    name: labelMap[key] || key,
    value: rawCat[key] || 1,
  }));

  // Ensure baseline fallback if no flags detected in specific categories yet
  if (categoryData.length === 0) {
    ['Labour Law', 'Data Privacy', 'POSH & Safety', 'Governance'].forEach(cat => {
      categoryData.push({ name: cat, value: 0 });
    });
  }

  // 3. Estimate critical issues count from high/critical reports or unresolved pool
  const criticalCount = (stats.recent_scans || []).filter(
    r => ['CRITICAL', 'HIGH'].includes((r.risk_level || '').toUpperCase())
  ).length || Math.round((stats.unresolved_issues || 0) * 0.25);

  // 4. Table column config
  const tableColumns = [
    {
      title: 'POLICY NAME',
      dataIndex: 'policy_title',
      key: 'title',
      render: (text, record) => (
        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{text || `Document #${record.id}`}</span>
      )
    },
    {
      title: 'SCORE',
      dataIndex: 'overall_score',
      key: 'score',
      width: 100,
      render: val => (
        <span className="mono" style={{ fontWeight: 600, color: getScoreColor(val || 0) }}>
          {Math.round(val || 0)}%
        </span>
      )
    },
    {
      title: 'RISK LEVEL',
      dataIndex: 'risk_level',
      key: 'risk',
      width: 120,
      render: val => getRiskTag(val)
    },
    {
      title: 'FLAGS',
      dataIndex: 'flagged_clauses',
      key: 'flags',
      width: 90,
      render: val => <span className="mono" style={{ color: 'var(--muted)' }}>{val || 0}</span>
    },
    {
      title: 'DATE',
      dataIndex: 'scanned_at',
      key: 'date',
      width: 130,
      render: val => (
        <span className="mono" style={{ fontSize: 12, color: 'var(--muted-2)' }}>
          {val ? new Date(val).toLocaleDateString() : 'Recent'}
        </span>
      )
    }
  ];

  return (
    <div style={{ maxWidth: 1140, margin: '0 auto', paddingBottom: 48, animation: 'fadeIn 200ms ease-out' }}>
      {/* ── Page Title ────────────────────────────────────────────── */}
      <div className="page-header" style={{ marginBottom: 28, borderBottom: 'none', paddingBottom: 0 }}>
        <h1>Executive Compliance Dashboard</h1>
        <p>Real-time regulatory posture and multi-domain legal audit telemetry</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 24 }}>{error}</div>}

      {/* ── 1. TOP STATS ROW (4 CARDS) ──────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: 16,
        marginBottom: 28,
      }}>
        {/* Card 1: Total Policies */}
        <Card
          bordered={false}
          style={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 4 }}
          styles={{ body: { padding: '18px 22px' } }}
        >
          <Statistic
            title={<span className="label-sm">TOTAL POLICIES SCANNED</span>}
            value={stats?.total_policies_scanned || 0}
            valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 600, color: 'var(--ink)' }}
            prefix={<span style={{ marginRight: 8, fontSize: 24 }}>📁</span>}
          />
        </Card>

        {/* Card 2: Average Score */}
        <Card
          bordered={false}
          style={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 4 }}
          styles={{ body: { padding: '18px 22px' } }}
        >
          <Statistic
            title={<span className="label-sm">AVG COMPLIANCE SCORE</span>}
            value={stats?.average_compliance_score || 0}
            suffix="%"
            valueStyle={{
              fontFamily: 'var(--font-mono)',
              fontSize: 32,
              fontWeight: 600,
              color: getScoreColor(stats?.average_compliance_score || 0)
            }}
          />
        </Card>

        {/* Card 3: Total Flagged Issues Breakdown */}
        <Card
          bordered={false}
          style={{ background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 4 }}
          styles={{ body: { padding: '18px 22px' } }}
        >
          <div className="label-sm" style={{ marginBottom: 4 }}>TOTAL FLAGGED ISSUES</div>
          <div className="mono" style={{ fontSize: 32, fontWeight: 600, color: 'var(--ink)' }}>
            {stats?.total_flagged_issues || 0}
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4, display: 'flex', gap: 12 }}>
            <span style={{ color: 'var(--danger)' }}>⚠️ {stats?.unresolved_issues || 0} Unresolved</span>
            <span style={{ color: 'var(--success)' }}>✓ {stats?.resolved_issues || 0} Resolved</span>
          </div>
        </Card>

        {/* Card 4: Critical Issues */}
        <Card
          bordered={false}
          style={{ background: '#FDF3F3', border: '1px solid #F0C4C4', borderRadius: 4 }}
          styles={{ body: { padding: '18px 22px' } }}
        >
          <Statistic
            title={<span className="label-sm" style={{ color: '#801C1C' }}>CRITICAL / HIGH RISKS</span>}
            value={criticalCount}
            valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700, color: '#801C1C' }}
            prefix={<span style={{ marginRight: 8, fontSize: 24 }}>🚨</span>}
          />
          <div style={{ fontSize: 11, color: '#A33F3F', marginTop: 4 }}>Requires prompt remediation</div>
        </Card>
      </div>

      {/* ── 2. MIDDLE ROW (TRENDS & DISTRIBUTION) ──────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 20, marginBottom: 28 }}>
        {/* Left (60%): Compliance Score Trend */}
        <div className="panel" style={{ padding: '24px' }}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>Compliance Score Trend</h2>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Historical posture evaluation over recent audit cycles</div>
          </div>
          <div style={{ height: 260, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                {/* Color Zones via ReferenceArea */}
                <ReferenceArea y1={70} y2={100} fill="#4A7856" fillOpacity={0.06} />
                <ReferenceArea y1={40} y2={70} fill="#A67C3D" fillOpacity={0.06} />
                <ReferenceArea y1={0} y2={40} fill="#A33F3F" fillOpacity={0.06} />

                <XAxis dataKey="name" stroke="var(--muted-2)" fontSize={11} tickLine={false} axisLine={{ stroke: 'var(--hairline)' }} />
                <YAxis domain={[0, 100]} stroke="var(--muted-2)" fontSize={11} tickLine={false} axisLine={{ stroke: 'var(--hairline)' }} />
                
                <RechartsTooltip
                  contentStyle={{ background: 'var(--bg)', border: '1px solid var(--hairline-2)', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                  formatter={(val, _, props) => [`${val}%`, props.payload.title]}
                />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="var(--accent)"
                  strokeWidth={2.5}
                  dot={{ r: 5, fill: 'var(--accent)', stroke: 'var(--bg)', strokeWidth: 2 }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Right (40%): Category Breakdown PieChart */}
        <div className="panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>Flag Distribution by Domain</h2>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>Proportion of detected issues across statutory frameworks</div>
          </div>
          <div style={{ height: 260, width: '100%', flex: 1 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="45%"
                  innerRadius={54}
                  outerRadius={84}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <RechartsTooltip
                  contentStyle={{ background: 'var(--bg)', border: '1px solid var(--hairline-2)', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                  formatter={(val) => [`${val} flags`, 'Volume']}
                />
                <Legend
                  layout="horizontal"
                  verticalAlign="bottom"
                  align="center"
                  wrapperStyle={{ fontSize: 11, fontFamily: 'var(--font-sans)', color: 'var(--ink)', paddingTop: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── 3. BOTTOM ROW (RECENT SCANS TABLE & QUICK ACTIONS) ──────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 20 }}>
        {/* Left: Recent Scans Table */}
        <div className="panel">
          <div className="panel-section" style={{ padding: '18px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>Recent Policy Audits</h2>
            <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>LAST {stats?.recent_scans?.length || 0} SCANS</span>
          </div>
          
          <Table
            dataSource={stats?.recent_scans || []}
            columns={tableColumns}
            rowKey="id"
            pagination={false}
            locale={{ emptyText: 'No scan reports recorded yet.' }}
            onRow={(record) => ({
              onClick: () => navigate(`/reports/${record.id}`),
              style: { cursor: 'pointer', transition: 'background var(--t)' }
            })}
            style={{ background: 'var(--bg)', borderTop: '1px solid var(--hairline)' }}
          />
        </div>

        {/* Right: Quick Actions Card */}
        <div className="panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>Operations & Telemetry</h2>
            <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 24 }}>
              Instantly ingest new employee handbooks, test ad-hoc legal phrasing against Indian law, or consult reference statutes.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <Link to="/upload" style={{ width: '100%' }}>
                <Button type="primary" size="large" block style={{ background: 'var(--accent)', height: 44, fontWeight: 500, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 16 }}>⬆️</span> Upload New Policy
                </Button>
              </Link>

              <Link to="/what-if" style={{ width: '100%' }}>
                <Button size="large" block style={{ height: 44, fontWeight: 500, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 12, borderColor: 'var(--hairline-2)' }}>
                  <span style={{ fontSize: 16 }}>⚖️</span> What-If Clause Checker
                </Button>
              </Link>

              <Link to="/laws" style={{ width: '100%' }}>
                <Button size="large" block style={{ height: 44, fontWeight: 500, textAlign: 'left', display: 'flex', alignItems: 'center', gap: 12, borderColor: 'var(--hairline-2)' }}>
                  <span style={{ fontSize: 16 }}>📚</span> View Statute Database
                </Button>
              </Link>
            </div>
          </div>

          <div style={{ marginTop: 28, paddingTop: 16, borderTop: '1px solid var(--hairline)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="mono" style={{ fontSize: 11, color: 'var(--muted-2)' }}>ENGINE STATUS</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--success)' }}></span>
              ML Multi-Signal Pipeline Ready
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
