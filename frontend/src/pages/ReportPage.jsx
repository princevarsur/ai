import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Table, Modal, Collapse, Tag, Progress, Badge, Skeleton, message } from 'antd';
import { BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell } from 'recharts';
import { complianceAPI, reportsAPI } from '../services/api';
import ThemisMark from '../components/ThemisMark';

// Helper for score colors: 0-39 = red, 40-69 = amber, 70-100 = green
function getScoreColor(score) {
  if (score < 40) return 'var(--danger)';   // #A33F3F
  if (score < 70) return 'var(--warning)';  // #A67C3D
  return 'var(--success)';                  // #4A7856
}

// Helper for risk level badge formatting
function getRiskTag(level = '') {
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
      return <Tag>{upper || 'EVALUATING'}</Tag>;
  }
}

// Helper for status tag styling
function getStatusTag(status = '') {
  const upper = status.toUpperCase();
  switch (upper) {
    case 'MISSING':
      return <Tag color="error" style={{ margin: 0 }}>MISSING</Tag>;
    case 'CONFLICT':
      return <Tag color="warning" style={{ margin: 0 }}>CONFLICT</Tag>;
    case 'GAP':
      return <Tag color="gold" style={{ margin: 0 }}>GAP</Tag>;
    case 'COMPLIANT':
    case 'RESOLVED':
      return <Tag color="success" style={{ margin: 0 }}>RESOLVED</Tag>;
    default:
      return <Tag>{upper}</Tag>;
  }
}

export default function ReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [report, setReport]       = useState(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');
  const [rescanning, setRescanning] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // Modal inspection state
  const [activeIssue, setActiveIssue] = useState(null);
  const [modalOpen, setModalOpen]     = useState(false);
  const [copied, setCopied]           = useState(false);

  // Expanded clause texts in table
  const [expandedRowKeys, setExpandedRowKeys] = useState({});

  // ── Fetch Report Details ────────────────────────────────────────
  useEffect(() => {
    async function loadReport() {
      setLoading(true);
      setError('');
      try {
        const res = await complianceAPI.getReport(id);
        setReport(res.data);
      } catch (err) {
        const msg = err.response?.data?.detail || 'Failed to retrieve compliance scan report.';
        setError(msg);
        message.error(msg);
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [id]);

  // ── Handle Flag Resolution ──────────────────────────────────────
  async function handleResolve(issueId) {
    try {
      await complianceAPI.resolveFlag(issueId);
      message.success('Issue marked as resolved!');
      // Optimistic local state update
      setReport(prev => ({
        ...prev,
        flagged_issues: prev.flagged_issues.map(item =>
          item.id === issueId ? { ...item, is_resolved: true, status: 'resolved' } : item
        )
      }));
      setModalOpen(false);
      setActiveIssue(null);
    } catch (err) {
      message.error('Failed to update resolution state.');
    }
  }

  // ── Handle Re-scan ──────────────────────────────────────────────
  async function handleRescan() {
    if (!report?.policy) return;
    setRescanning(true);
    try {
      const res = await complianceAPI.triggerScan(report.policy);
      message.success('Policy re-scanned successfully!');
      navigate(`/reports/${res.data.id}`);
      window.location.reload();
    } catch (err) {
      message.error('Re-scan evaluation failed.');
    } finally {
      setRescanning(false);
    }
  }

  // ── Handle PDF Download ─────────────────────────────────────────
  async function handleDownloadPDF() {
    if (!report || !report.id) return;
    setDownloading(true);
    message.loading({ content: 'Generating professional PDF report...', key: 'pdf_download', duration: 0 });
    try {
      const res = await reportsAPI.downloadPdf(report.id);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const fileName = `THEMIS_Compliance_Report_${report.id}.pdf`;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success({ content: 'PDF report downloaded successfully!', key: 'pdf_download', duration: 3 });
    } catch (err) {
      message.error({ content: 'Failed to generate PDF report. Please try again.', key: 'pdf_download', duration: 3 });
    } finally {
      setDownloading(false);
    }
  }

  // ── Handle Copy Template Fix ────────────────────────────────────
  function handleCopyFix(text) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    message.success('Template remediation copy added to clipboard!');
    setTimeout(() => setCopied(false), 3000);
  }

  // ── Compute Category Breakdown Metrics ──────────────────────────
  const categoryStats = !report ? [] : [
    'labour', 'data_privacy', 'workplace_safety', 'employee_benefits', 'corporate_governance', 'cyber_security', 'general'
  ].map(catKey => {
    const matchingIssues = (report.flagged_issues || []).filter(
      i => (i.legal_rule?.category || 'general').toLowerCase() === catKey
    );
    const unresolvedCount = matchingIssues.filter(i => !i.is_resolved).length;
    // Calculate synthetic category compliance score based on flag count & severity
    const deduction = matchingIssues.reduce((acc, curr) => acc + (curr.is_resolved ? 0 : curr.severity_score / 4), 0);
    const score = Math.max(0, Math.min(100, Math.round(100 - deduction)));

    const labelMap = {
      labour: 'Labour & EPF',
      data_privacy: 'Data Privacy (DPDP)',
      workplace_safety: 'POSH & Safety',
      employee_benefits: 'Gratuity & Benefits',
      corporate_governance: 'Governance',
      cyber_security: 'Cyber Security',
      general: 'General Handbooks',
    };

    return {
      category: labelMap[catKey] || catKey,
      score,
      flagCount: unresolvedCount,
    };
  }).filter(c => c.flagCount > 0 || c.category === 'Labour & EPF' || c.category === 'Data Privacy (DPDP)' || c.category === 'POSH & Safety');

  // ── Table Column Architecture ───────────────────────────────────
  const columns = [
    {
      title: 'SEVERITY',
      dataIndex: 'severity_score',
      key: 'severity_icon',
      width: 100,
      render: (val, record) => {
        if (record.is_resolved) return <span style={{ color: 'var(--success)', fontWeight: 600 }}>🟢 Resolved</span>;
        if (val >= 70) return <span style={{ color: 'var(--danger)', fontWeight: 600 }}>🔴 High</span>;
        if (val >= 40) return <span style={{ color: 'var(--warning)', fontWeight: 600 }}>🟡 Medium</span>;
        return <span style={{ color: 'var(--success)', fontWeight: 600 }}>🟢 Low</span>;
      }
    },
    {
      title: 'CLAUSE TEXT',
      dataIndex: 'clause_text',
      key: 'clause_text',
      render: (text, record) => {
        const isExpanded = !!expandedRowKeys[record.id];
        const isLong = text && text.length > 100;
        const display = isExpanded || !isLong ? text : `${text.slice(0, 100)}...`;

        return (
          <div>
            <div style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--ink)', lineHeight: 1.5 }}>
              {display || '—'}
            </div>
            {isLong && (
              <button
                type="button"
                className="btn btn-ghost"
                style={{ padding: 0, fontSize: 11, height: 'auto', marginTop: 4, textDecoration: 'underline' }}
                onClick={() => setExpandedRowKeys(prev => ({ ...prev, [record.id]: !prev[record.id] }))}
              >
                {isExpanded ? 'Show less' : 'Expand clause'}
              </button>
            )}
          </div>
        );
      }
    },
    {
      title: 'STATUTORY REQUIREMENT',
      dataIndex: ['legal_rule', 'law_name'],
      key: 'law',
      render: (_, record) => {
        const law = record.legal_rule?.law_name || 'General Standard';
        const sec = record.legal_rule?.section ? ` (§ ${record.legal_rule.section})` : '';
        return (
          <div className="mono" style={{ fontSize: 12, color: 'var(--ink)' }}>
            {law}{sec}
          </div>
        );
      }
    },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (val, record) => getStatusTag(record.is_resolved ? 'RESOLVED' : val)
    },
    {
      title: 'SCORE',
      dataIndex: 'severity_score',
      key: 'score',
      width: 130,
      render: (val, record) => {
        const color = record.is_resolved ? 'var(--success)' : (val >= 70 ? 'var(--danger)' : val >= 40 ? 'var(--warning)' : 'var(--success)');
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Progress percent={val} size="small" showInfo={false} strokeColor={color} style={{ width: 60 }} />
            <span className="mono" style={{ fontSize: 12, fontWeight: 500 }}>{val}/100</span>
          </div>
        );
      }
    },
    {
      title: 'ACTION',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => {
            setActiveIssue(record);
            setModalOpen(true);
            setCopied(false);
          }}
        >
          View Fix
        </button>
      )
    }
  ];

  // ── SKELETON LOADING STATE ──────────────────────────────────────
  if (loading || rescanning) {
    return (
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '24px 0' }}>
        {rescanning ? (
          <div className="panel" style={{ padding: '64px 32px', textAlign: 'center', margin: '48px 0' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
              <ThemisMark size={56} color="var(--accent)" thinking={true} />
            </div>
            <h2 style={{ fontFamily: "'Newsreader', serif", fontSize: 24, marginBottom: 8, color: 'var(--ink)' }}>
              Re-evaluating Compliance Posture
            </h2>
            <p style={{ color: 'var(--muted)', fontSize: 14 }}>Executing real-time semantic & numeric legal validations...</p>
          </div>
        ) : (
          <div className="panel" style={{ padding: '32px' }}>
            <Skeleton active paragraph={{ rows: 2 }} />
            <div style={{ marginTop: 32 }}><Skeleton.Button active style={{ width: 200, height: 120 }} /> <Skeleton.Button active style={{ width: 200, height: 120 }} /></div>
            <div style={{ marginTop: 32 }}><Skeleton active paragraph={{ rows: 6 }} /></div>
          </div>
        )}
      </div>
    );
  }

  if (error && !report) {
    return (
      <div style={{ maxWidth: 840, margin: '24px auto' }}>
        <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>
        <Link to="/dashboard" className="btn btn-secondary">&larr; Back to Dashboard</Link>
      </div>
    );
  }

  const issues = report?.flagged_issues || [];
  const activeIssues = issues.filter(i => !i.is_resolved && i.status !== 'compliant');
  const resolvedOrCompliant = issues.filter(i => i.is_resolved || i.status === 'compliant');

  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', paddingBottom: 48 }}>
      {/* ── 1. HEADER SECTION ──────────────────────────────────────── */}
      <div className="panel" style={{ padding: '32px', marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 24 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span className="label-sm">Compliance Scan Report</span>
              <span className="mono" style={{ color: 'var(--muted-2)' }}>ID: #{report?.id}</span>
              {getRiskTag(report?.risk_level)}
            </div>
            <h1 style={{ fontFamily: "'Newsreader', serif", fontSize: 32, margin: '4px 0 12px', color: 'var(--ink)' }}>
              {report?.policy_title || `Policy Document #${report?.policy}`}
            </h1>
            <div className="mono" style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', gap: 20 }}>
              <span>SCANNED: {report?.scanned_at ? new Date(report.scanned_at).toLocaleString() : 'Recent'}</span>
              <span>EXECUTION TIME: {(report?.scan_duration_seconds || 0).toFixed(2)}s</span>
              <span>CLAUSES TESTED: {report?.total_clauses || 0}</span>
            </div>
          </div>

          {/* Compliance Score Circle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, background: 'var(--surface)', padding: '16px 24px', borderRadius: 6, border: '1px solid var(--hairline)' }}>
            <Progress
              type="circle"
              percent={Math.round(report?.overall_score || 0)}
              size={84}
              strokeColor={getScoreColor(report?.overall_score || 0)}
              format={percent => (
                <span className="mono" style={{ fontSize: 22, fontWeight: 600, color: 'var(--ink)' }}>
                  {percent}%
                </span>
              )}
            />
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>Overall Compliance</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                {activeIssues.length} open flag{activeIssues.length !== 1 ? 's' : ''} detected
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 2. SCORE BREAKDOWN & CHART ─────────────────────────────── */}
      <div style={{ marginBottom: 32 }}>
        <div className="label-sm" style={{ marginBottom: 12 }}>Domain Posture & Coverage</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginBottom: 20 }}>
          {categoryStats.map((cat, idx) => (
            <div key={idx} className="panel" style={{ padding: '16px', borderRadius: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{cat.category}</span>
                <span className="mono" style={{ fontSize: 12, color: cat.flagCount > 0 ? 'var(--danger)' : 'var(--success)' }}>
                  {cat.flagCount > 0 ? `${cat.flagCount} flags` : 'Clear'}
                </span>
              </div>
              <Progress
                percent={cat.score}
                size="small"
                showInfo={false}
                strokeColor={getScoreColor(cat.score)}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>Score</span>
                <span className="mono" style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink)' }}>{cat.score}%</span>
              </div>
            </div>
          ))}
        </div>

        {/* Recharts Visual BarChart */}
        <div className="panel" style={{ padding: '24px', height: 240 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={categoryStats} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="category" stroke="var(--muted-2)" fontSize={11} tickLine={false} axisLine={{ stroke: 'var(--hairline)' }} />
              <YAxis domain={[0, 100]} stroke="var(--muted-2)" fontSize={11} tickLine={false} axisLine={{ stroke: 'var(--hairline)' }} />
              <RechartsTooltip
                contentStyle={{ background: 'var(--bg)', border: '1px solid var(--hairline-2)', borderRadius: 4, fontFamily: 'var(--font-mono)', fontSize: 12 }}
                formatter={(val) => [`${val}%`, 'Score']}
              />
              <Bar dataKey="score" radius={[2, 2, 0, 0]} maxBarSize={48}>
                {categoryStats.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getScoreColor(entry.score)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── 3. FLAGGED ISSUES TABLE ────────────────────────────────── */}
      <div className="panel" style={{ marginBottom: 32 }}>
        <div className="panel-section" style={{ padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--ink)', margin: 0 }}>Flagged Legal Clauses</h2>
            <p style={{ fontSize: 13, color: 'var(--muted)', margin: '4px 0 0' }}>
              Actionable conflicts and structural omissions detected across Indian regulatory frameworks
            </p>
          </div>
          <Badge count={activeIssues.length} overflowCount={99} style={{ backgroundColor: 'var(--danger)', fontWeight: 600 }} />
        </div>

        <Table
          dataSource={activeIssues}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 10, position: ['bottomRight'] }}
          locale={{ emptyText: 'No unresolved legal conflicts detected in this document.' }}
          style={{ background: 'var(--bg)', borderTop: '1px solid var(--hairline)' }}
        />
      </div>

      {/* ── 4. COMPLIANT CLAUSES (COLLAPSIBLE) ─────────────────────── */}
      <div style={{ marginBottom: 32 }}>
        <Collapse
          style={{ background: 'var(--bg)', border: '1px solid var(--hairline)', borderRadius: 4 }}
          items={[{
            key: '1',
            label: (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '4px 0' }}>
                <span style={{ color: 'var(--success)' }}>✅</span>
                <span style={{ fontWeight: 600, color: 'var(--ink)' }}>Compliant & Resolved Clauses</span>
                <span className="mono" style={{ color: 'var(--muted)', fontSize: 12 }}>
                  ({report?.compliant_clauses || resolvedOrCompliant.length} clauses passed)
                </span>
              </div>
            ),
            children: (
              <div style={{ padding: '8px 16px' }}>
                {resolvedOrCompliant.length === 0 ? (
                  <p className="mono" style={{ color: 'var(--muted)', fontSize: 12, margin: 0 }}>
                    {report?.compliant_clauses ? `${report.compliant_clauses} unflagged clauses successfully evaluated and verified clean.` : 'No compliant entries listed in diagnostic trace.'}
                  </p>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--ink)', fontSize: 13, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {resolvedOrCompliant.map((item, i) => (
                      <li key={item.id || i}>
                        <span style={{ fontWeight: 500 }}>Clause #{item.clause_index + 1}: </span>
                        <span style={{ color: 'var(--muted)' }}>{item.clause_text || '—'}</span>
                        {item.is_resolved && <Tag color="success" style={{ marginLeft: 8 }}>Manually Resolved</Tag>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          }]}
        />
      </div>

      {/* ── 5. FOOTER ACTIONS ──────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderTop: '1px solid var(--hairline)' }}>
        <Link to="/dashboard" className="btn btn-secondary">&larr; Back to Dashboard</Link>
        <div style={{ display: 'flex', gap: 12 }}>
          <button type="button" className="btn btn-secondary" onClick={handleDownloadPDF} disabled={downloading} style={{ opacity: downloading ? 0.7 : 1 }}>
            {downloading ? 'Generating PDF...' : 'Download PDF Report'}
          </button>
          <button type="button" className="btn btn-primary" onClick={handleRescan}>
            Re-scan Policy
          </button>
        </div>
      </div>

      {/* ── 6. "VIEW FIX" MODAL DRAWER ─────────────────────────────── */}
      <Modal
        title={<span style={{ fontFamily: "'Newsreader', serif", fontSize: 20, color: 'var(--ink)' }}>Remediation & Legal Fix</span>}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setActiveIssue(null); }}
        footer={[
          <button key="close" type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>
            Close
          </button>,
          !activeIssue?.is_resolved && (
            <button key="resolve" type="button" className="btn btn-primary" onClick={() => handleResolve(activeIssue?.id)}>
              Mark as Resolved
            </button>
          )
        ]}
        width={720}
        styles={{ body: { padding: '20px 0 10px' } }}
      >
        {activeIssue && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Section 1: Problematic Clause */}
            <div>
              <div className="label-sm" style={{ marginBottom: 6, color: 'var(--danger)' }}>Problematic Clause Text</div>
              <div style={{
                padding: '12px 16px',
                background: '#FDF3F3',
                border: '1px solid #F0C4C4',
                borderRadius: 4,
                color: '#801C1C',
                fontFamily: 'var(--font-sans)',
                fontSize: 13,
                lineHeight: 1.5,
              }}>
                {activeIssue.clause_text}
              </div>
            </div>

            {/* Section 2: Law Requirement */}
            <div>
              <div className="label-sm" style={{ marginBottom: 6 }}>Statutory Requirement & Violation Notice</div>
              <div style={{ padding: '12px 16px', background: 'var(--surface)', border: '1px solid var(--hairline)', borderRadius: 4, fontSize: 13, color: 'var(--ink)' }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {activeIssue.legal_rule?.law_name || 'Standard Legal Provision'}
                  {activeIssue.legal_rule?.section && ` — Section ${activeIssue.legal_rule.section}`}
                </div>
                <div>
                  {activeIssue.description || activeIssue.legal_rule?.description || 'Clause fails to satisfy statutory minimum guarantees under labor and corporate compliance regulations.'}
                </div>
              </div>
            </div>

            {/* Section 3: Suggested Template Fix */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span className="label-sm" style={{ color: 'var(--success)' }}>Suggested Compliant Template Fix</span>
                <button
                  type="button"
                  className="btn btn-ghost"
                  style={{ padding: '2px 8px', height: 'auto', fontSize: 11 }}
                  onClick={() => handleCopyFix(activeIssue.template_fix || 'No template fix provided for this specific custom rule.')}
                >
                  {copied ? '✅ Copied to clipboard' : '📋 Copy Text'}
                </button>
              </div>
              <pre className="mono" style={{
                margin: 0,
                padding: '16px',
                background: '#16181A',
                color: '#E2E1DC',
                borderRadius: 4,
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                border: '1px solid #3E4452',
              }}>
                {activeIssue.template_fix || 'Insert standardized statutory definition ensuring compliance with governing jurisdiction provisions and employee notification obligations.'}
              </pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
