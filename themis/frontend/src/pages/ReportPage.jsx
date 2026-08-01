import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Table, Modal, Collapse, Tag, Progress, Badge, Button, Skeleton, message } from 'antd';
import { DownloadOutlined, ReloadOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, CopyOutlined } from '@ant-design/icons';
import { BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import Layout from '../components/Layout';
import { complianceAPI, reportsAPI } from '../services/api';

const { Panel } = Collapse;

const getSeverityColor = (score) => {
  if (score >= 70) return 'var(--success)';
  if (score >= 40) return 'var(--warning)';
  return 'var(--error)';
};

const getSeverityIcon = (severity) => {
  const map = {
    CRITICAL: { icon: <CloseCircleOutlined />, color: 'var(--risk-critical)' },
    HIGH: { icon: <WarningOutlined />, color: 'var(--risk-high)' },
    MEDIUM: { icon: <WarningOutlined />, color: 'var(--risk-medium)' },
    LOW: { icon: <CheckCircleOutlined />, color: 'var(--risk-low)' },
  };
  return map[severity] || map.LOW;
};

const ReportPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rescanning, setRescanning] = useState(false);
  const [fixModal, setFixModal] = useState({ visible: false, issue: null });

  useEffect(() => {
    fetchReport();
  }, [id]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const { data } = await complianceAPI.getReport(id);
      setReport(data);
    } catch (error) {
      message.error('Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  const handleRescan = async () => {
    setRescanning(true);
    try {
      const { data } = await complianceAPI.triggerScan(report.policy_id);
      message.success('Scan initiated');
      navigate(`/reports/${data.report_id}`);
    } catch (error) {
      message.error('Failed to trigger rescan');
      setRescanning(false);
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const { data } = await reportsAPI.downloadPdf(id);
      const url = window.URL.createObjectURL(new Blob([data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      message.success('Report downloaded');
    } catch (error) {
      message.error('Failed to download PDF');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    message.success('Copied to clipboard');
  };

  if (loading) {
    return (
      <Layout title="Compliance Report">
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <Skeleton active paragraph={{ rows: 8 }} />
        </div>
      </Layout>
    );
  }

  if (!report) {
    return (
      <Layout title="Report Not Found">
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <h2>Report not found</h2>
          <Link to="/dashboard">Back to Dashboard</Link>
        </div>
      </Layout>
    );
  }

  const columns = [
    {
      title: 'Severity',
      key: 'severity',
      width: 100,
      render: (_, record) => {
        let label = 'LOW';
        if (record.severity_score >= 70) label = 'CRITICAL';
        else if (record.severity_score >= 50) label = 'HIGH';
        else if (record.severity_score >= 30) label = 'MEDIUM';
        
        const { color } = getSeverityIcon(label);
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: color }} title={label} />
          </div>
        );
      },
    },
    {
      title: 'Clause',
      dataIndex: 'clause_text',
      key: 'clause_text',
      width: 450,
      render: (text, record) => (
        <div style={{
          color: 'var(--text-primary)',
          fontWeight: 500,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'normal',
        }}>
          {record.clause_index ? `[Clause ${record.clause_index}] ` : ''}
          {text}
        </div>
      ),
    },
    {
      title: 'Law Violated',
      dataIndex: 'law',
      key: 'law',
      width: 200,
      render: (_, record) => {
        const lawName = record.legal_rule?.law_name || record.law_name || record.law;
        const section = record.legal_rule?.section || record.section;
        return (
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{lawName}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {section ? `Section: ${section}` : ''}
            </div>
          </div>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status) => {
        const colorMap = {
          MISSING: 'error',
          CONFLICT: 'warning',
          GAP: 'default',
        };
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: 'Severity Score',
      dataIndex: 'severity_score',
      key: 'severity_score',
      width: 150,
      render: (score) => (
        <div>
          <Progress
            percent={score}
            strokeColor={getSeverityColor(score)}
            size="small"
            showInfo={false}
          />
          <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
            {score}/100
          </span>
        </div>
      ),
    },

  ];

  const categoryData = report.category_scores?.map((cat) => ({
    category: cat.name,
    score: cat.score,
    flags: cat.flag_count,
  })) || [];



  const radarData = report.category_scores?.map((cat) => ({
    category: cat.name.substring(0, 10),
    score: cat.score,
  })) || [];

  return (
    <Layout title="Compliance Report">
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header Section */}
        <div className="card" style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
            <div style={{ textAlign: 'left' }}>
              <h2 style={{ margin: 0 }}>{report.policy_title}</h2>
              <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem', margin: '0.25rem 0 0 0' }}>
                Scanned: {new Date(report.scanned_at).toLocaleString()} • Duration: {report.scan_duration_seconds || report.scan_duration}s
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ textAlign: 'center' }}>
                <Progress
                  type="circle"
                  percent={report.overall_score || report.compliance_score}
                  strokeColor={getSeverityColor(report.overall_score || report.compliance_score)}
                  width={120}
                  format={(percent) => (
                    <div>
                      <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{percent}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>Score</div>
                    </div>
                  )}
                />
              </div>
              <Badge
                count={report.risk_level}
                style={{
                  background: getSeverityColor(report.overall_score || report.compliance_score),
                  fontSize: '0.875rem',
                  padding: '0.5rem 1rem',
                }}
              />
            </div>
          </div>
        </div>

        {/* Category Score Breakdown */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Breakdown</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
            {categoryData.map((cat) => (
              <div key={cat.category} className="card" style={{ padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                  {cat.category}
                </div>
                <Progress
                  percent={cat.score}
                  strokeColor={getSeverityColor(cat.score)}
                  showInfo={false}
                  style={{ marginBottom: '0.5rem' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                  <span>Score: {cat.score}</span>
                  <span>Flags: {cat.flags}</span>
                </div>
              </div>
            ))}
          </div>
        </div>


        {/* Radar Chart */}
        {radarData.length > 0 && (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ marginBottom: '1rem' }}>Category Score Radar</h3>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--border-color)" />
                <PolarAngleAxis dataKey="category" stroke="var(--text-secondary)" />
                <PolarRadiusAxis stroke="var(--text-secondary)" />
                <Radar name="Score" dataKey="score" stroke="var(--accent-primary)" fill="var(--accent-primary)" fillOpacity={0.3} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Flagged Issues Table */}
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>Flagged Issues ({report.flagged_issues?.length || 0})</h3>
          <Table
            columns={columns}
            dataSource={report.flagged_issues || []}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 1000 }}
            onRow={(record) => ({
              onClick: () => setFixModal({ visible: true, issue: record }),
              style: { cursor: 'pointer' },
            })}
          />
        </div>

        {/* Compliant Clauses */}
        {report.compliant_clauses?.length > 0 && (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <Collapse ghost>
              <Panel
                header={
                  <span style={{ fontSize: '1.125rem', fontWeight: 500 }}>
                    <div style={{ width: '16px', height: '16px', borderRadius: '50%', backgroundColor: 'var(--success)', marginRight: '0.5rem' }} />
                    Compliant Clauses ({report.compliant_clauses.length})
                  </span>
                }
                key="1"
              >
                {report.compliant_clauses.map((clause, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '0.75rem',
                      background: 'var(--bg-tertiary)',
                      borderRadius: '6px',
                      marginBottom: '0.5rem',
                      fontSize: '0.875rem',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)' }}>
                      <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'var(--success)', flexShrink: 0 }} />
                      <span>{clause.text}</span>
                    </div>
                  </div>
                ))}
              </Panel>
            </Collapse>
          </div>
        )}

        {/* Footer Actions */}
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '2rem' }}>
          <Button
            size="large"
            icon={<DownloadOutlined />}
            onClick={handleDownloadPdf}
          >
            Download PDF
          </Button>
          <Button
            size="large"
            icon={<ReloadOutlined />}
            loading={rescanning}
            onClick={handleRescan}
          >
            Re-scan
          </Button>
          <Button size="large" type="link">
            <Link to="/dashboard">Back to Dashboard</Link>
          </Button>
        </div>
      </div>

      {/* Fix Modal */}
      <Modal
        title="Suggested Fix"
        open={fixModal.visible}
        onCancel={() => setFixModal({ visible: false, issue: null })}
        width={700}
        footer={[
          <Button key="close" onClick={() => setFixModal({ visible: false, issue: null })}>
            Close
          </Button>,
          <Button key="resolve" type="primary">
            Mark as Resolved
          </Button>,
        ]}
      >
        {fixModal.issue && (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <h4 style={{ color: 'var(--error)' }}>Problematic Clause:</h4>
              <div
                style={{
                  padding: '1rem',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid var(--error)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                }}
              >
                {fixModal.issue.clause_text}
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <h4>Issue Description:</h4>
              <div
                style={{
                  padding: '1rem',
                  background: 'var(--bg-tertiary)',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  color: 'var(--text-secondary)',
                }}
              >
                {fixModal.issue.description || 'No specific requirement text available.'}
              </div>
            </div>

            <div>
              <h4 style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                Suggested Template:
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard(fixModal.issue.suggested_fix || 'No fix available')}
                >
                  Copy
                </Button>
              </h4>
              <div
                style={{
                  padding: '1rem',
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  color: 'var(--text-primary)',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {fixModal.issue.suggested_fix || fixModal.issue.template_fix || 'No suggested fix available. Please consult legal counsel.'}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </Layout>
  );
};

export default ReportPage;
