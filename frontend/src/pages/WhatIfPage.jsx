import { useState } from 'react';
import { Input, Button, Tag, Progress, Skeleton, message, Divider, Alert } from 'antd';
import { complianceAPI } from '../services/api';
import ThemisMark from '../components/ThemisMark';

const EXAMPLE_CLAUSES = [
  "Female employees get 12 weeks maternity leave",
  "Employee data may be shared with vendors",
  "All complaints will be handled by HR",
  "If an employee resigns without serving notice, all earned salary will be forfeited",
  "Any late arrival after 10:15 am will result in half-day salary deduction"
];

export default function WhatIfPage() {
  const [clauseText, setClauseText] = useState('');
  const [loading, setLoading]       = useState(false);
  const [results, setResults]       = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  async function handleCheck(textToTest) {
    const targetText = typeof textToTest === 'string' ? textToTest : clauseText;
    if (!targetText.trim()) {
      message.warning('Please enter or select a draft policy clause to analyze.');
      return;
    }

    setLoading(true);
    setResults(null);
    try {
      const res = await complianceAPI.whatIfCheck(targetText);
      setResults(res.data.matches || []);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Evaluation failed. Please try again.';
      message.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }

  function handleChipClick(chipText) {
    setClauseText(chipText);
    handleCheck(chipText);
  }

  function copyToClipboard(text, idx) {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    message.success('Suggested remediation copied to clipboard!');
    setTimeout(() => setCopiedIndex(null), 2500);
  }

  function getMatchLevel(match) {
    if (typeof match === 'number') {
      const score = match;
      if (score >= 0.60) return { label: 'Likely Violation', color: '#A33F3F', badge: 'error', bg: 'var(--danger-bg)' };
      if (score >= 0.40) return { label: 'Possible Issue / Gap', color: '#A67C3D', badge: 'warning', bg: 'var(--warning-bg)' };
      return { label: 'Compliant / Unlikely', color: '#4A7856', badge: 'success', bg: 'var(--success-bg)' };
    }
    const status = (match.status || '').toUpperCase();
    if (status === 'CONFLICT') return { label: match.status_label || 'Likely Violation', color: '#A33F3F', badge: 'error', bg: 'var(--danger-bg)' };
    if (status === 'GAP') return { label: match.status_label || 'Possible Issue / Gap', color: '#A67C3D', badge: 'warning', bg: 'var(--warning-bg)' };
    return { label: match.status_label || 'Compliant / Lawful', color: '#4A7856', badge: 'success', bg: 'var(--success-bg)' };
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontFamily: "'Newsreader', serif", fontSize: '32px', color: 'var(--ink)', fontWeight: 500 }}>
          Live Clause Checker
        </h1>
        <p style={{ fontSize: '15px', color: 'var(--muted)', marginTop: '4px' }}>
          Test draft HR policies against 44 Indian labour codes, data privacy laws, and POSH regulations in real-time.
        </p>
      </div>

      {/* Input section card */}
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--hairline)',
        borderRadius: '8px',
        padding: '28px',
        marginBottom: '36px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <ThemisMark size={20} color="var(--accent)" />
          <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: '12px', color: 'var(--ink-2)' }}>
            Statutory Evaluation Sandbox
          </span>
        </div>

        <Input.TextArea
          rows={5}
          value={clauseText}
          onChange={(e) => setClauseText(e.target.value)}
          placeholder="Paste a draft clause or HR standing order to check if it violates any applicable Indian employment law..."
          style={{
            fontSize: '15px',
            lineHeight: '1.6',
            padding: '16px',
            borderRadius: '6px',
            border: '1px solid var(--hairline-2)',
            background: 'var(--bg)',
            color: 'var(--ink)',
            marginBottom: '20px',
            fontFamily: "'IBM Plex Sans', sans-serif"
          }}
        />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <Button
            type="primary"
            size="large"
            loading={loading}
            onClick={() => handleCheck()}
            style={{
              background: 'var(--accent-mid)',
              borderColor: 'var(--accent-mid)',
              fontWeight: 500,
              padding: '0 32px',
              height: '44px',
              borderRadius: '6px',
              fontSize: '14px',
              letterSpacing: '0.03em'
            }}
          >
            {loading ? 'Evaluating Statues...' : 'Check Compliance'}
          </Button>

          <span style={{ fontSize: '12px', color: 'var(--muted-2)' }}>
            Powered by Dual-Model Consensus (MiniLM + InLegal-SBERT)
          </span>
        </div>

        <Divider style={{ margin: '24px 0', borderColor: 'var(--hairline)' }} />

        {/* Example Chips */}
        <div>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '12px' }}>
            Or try these common high-risk sample clauses:
          </span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {EXAMPLE_CLAUSES.map((chip, idx) => (
              <Tag
                key={idx}
                onClick={() => handleChipClick(chip)}
                style={{
                  cursor: 'pointer',
                  padding: '6px 14px',
                  borderRadius: '99px',
                  background: 'var(--bg)',
                  border: '1px solid var(--hairline-2)',
                  color: 'var(--ink-2)',
                  fontSize: '13px',
                  transition: 'all 150ms ease-out',
                  userSelect: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.background = 'var(--accent-soft)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--hairline-2)';
                  e.currentTarget.style.background = 'var(--bg)';
                }}
              >
                {chip}
              </Tag>
            ))}
          </div>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div style={{ background: 'var(--surface)', padding: '32px', borderRadius: '8px', border: '1px solid var(--hairline)' }}>
          <Skeleton active paragraph={{ rows: 6 }} />
        </div>
      )}

      {/* Analysis Results */}
      {!loading && results && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '20px', fontFamily: "'Newsreader', serif", color: 'var(--ink)', margin: 0 }}>
              Statutory Alignment Report
            </h3>
            <span style={{ fontSize: '13px', color: 'var(--muted)', fontWeight: 500 }}>
              Showing {results.length} relevant statutory matches
            </span>
          </div>

          {results.length === 0 ? (
            <Alert
              message="No Significant Legal Conflicts Detected"
              description="This clause does not appear to trigger standard statutory red flags across current labour codes or privacy mandates."
              type="success"
              showIcon
              style={{ padding: '16px', borderRadius: '6px' }}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {results.map((match, idx) => {
                const level = getMatchLevel(match);
                return (
                  <div
                    key={idx}
                    style={{
                      background: 'var(--surface)',
                      borderRadius: '8px',
                      border: '1px solid var(--hairline)',
                      borderLeft: `5px solid ${level.color}`,
                      padding: '24px',
                      transition: 'box-shadow 0.2s'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                          <Tag color="default" style={{ fontWeight: 600, fontSize: '11px', textTransform: 'uppercase' }}>
                            {match.category}
                          </Tag>
                          <Tag color={level.color} style={{ fontWeight: 600 }}>
                            {level.label}
                          </Tag>
                          {match.keyword_found && (
                            <Tag color="cyan" style={{ fontSize: '11px' }}>Keyword Match</Tag>
                          )}
                        </div>
                        <h4 style={{ fontSize: '17px', fontWeight: 600, color: 'var(--ink)', textTransform: 'none', letterSpacing: 'normal', margin: '0 0 6px 0' }}>
                          {match.law_name} <span style={{ fontWeight: 400, color: 'var(--muted)' }}>— {match.section}</span>
                        </h4>
                        {match.explanation && (
                          <div style={{ fontSize: '13px', color: 'var(--ink-2)', fontStyle: 'italic' }}>
                            {match.explanation}
                          </div>
                        )}
                      </div>

                      {/* Similarity Scores Pill */}
                      <div style={{ display: 'flex', gap: '16px', background: 'var(--bg)', padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--hairline)' }}>
                        <div>
                          <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--muted)' }}>Combined Score</div>
                          <div style={{ fontSize: '15px', fontWeight: 600, color: level.color, fontFamily: "'IBM Plex Mono', monospace" }}>
                            {Math.round(match.combined_score * 100)}%
                          </div>
                        </div>
                        <div style={{ borderLeft: '1px solid var(--hairline)', paddingLeft: '16px' }}>
                          <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--muted)' }}>InLegal SBERT</div>
                          <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--ink-2)', fontFamily: "'IBM Plex Mono', monospace" }}>
                            {Math.round(match.inlegal_similarity * 100)}%
                          </div>
                        </div>
                      </div>
                    </div>

                    <div style={{ background: 'var(--bg)', padding: '16px', borderRadius: '6px', border: '1px solid var(--hairline-2)', marginBottom: match.is_potential_conflict && match.template_fix ? '16px' : '0' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                        Statutory Mandate & Obligation:
                      </span>
                      <p style={{ margin: 0, color: 'var(--ink-2)', fontSize: '14px', lineHeight: '1.6' }}>
                        {match.requirement_text}
                      </p>
                    </div>

                    {/* Suggested Fix - only show if there's an issue */}
                    {match.is_potential_conflict && match.template_fix && (
                      <div style={{
                        background: 'var(--accent-soft)',
                        border: '1px solid #CBD5E1',
                        borderRadius: '6px',
                        padding: '16px',
                        position: 'relative'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent-mid)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            ✓ Compliant Template Replacement
                          </span>
                          <Button
                            size="small"
                            onClick={() => copyToClipboard(match.template_fix, idx)}
                            style={{ fontSize: '12px', borderColor: '#94A3B8', background: 'white' }}
                          >
                            {copiedIndex === idx ? 'Copied!' : 'Copy Fix'}
                          </Button>
                        </div>
                        <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '13px', color: '#1E293B', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                          {match.template_fix}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
