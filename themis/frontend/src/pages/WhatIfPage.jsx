import { useState } from 'react';
import { motion } from 'framer-motion';
import { Input, Button, Tag, Card, Empty, message } from 'antd';
import { SearchOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, CopyOutlined } from '@ant-design/icons';
import Layout from '../components/Layout';
import { complianceAPI } from '../services/api';

const { TextArea } = Input;

const EXAMPLE_CLAUSES = [
  'Female employees get 12 weeks maternity leave',
  'Employee data may be shared with vendors',
  'All complaints will be handled by HR',
];

const getSeverityColor = (score) => {
  if (score < 0.4) return 'var(--success)';
  if (score < 0.6) return 'var(--warning)';
  return 'var(--error)';
};

const getSeverityIcon = (score) => {
  if (score < 0.4) return <CheckCircleOutlined />;
  if (score < 0.6) return <WarningOutlined />;
  return <CloseCircleOutlined />;
};

const getSeverityLabel = (score) => {
  if (score < 0.4) return 'Compliant';
  if (score < 0.6) return 'Possible Issue';
  return 'Likely Violation';
};

const WhatIfPage = () => {
  const [clauseText, setClauseText] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const handleCheck = async () => {
    if (!clauseText.trim()) {
      message.warning('Please enter clause text');
      return;
    }

    setLoading(true);
    try {
      const { data } = await complianceAPI.whatIfCheck(clauseText);
      setResults(data);
    } catch (error) {
      message.error('Failed to check clause');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    message.success('Copied to clipboard');
  };

  return (
    <Layout title="What-If Checker">
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
          style={{ marginBottom: '1.5rem' }}
        >
          <h3 style={{ marginBottom: '0.5rem' }}>Check Clause Compliance</h3>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Paste a draft clause to check if it violates any law. THEMIS will analyze it against 22 legal rules.
          </p>

          <TextArea
            value={clauseText}
            onChange={(e) => setClauseText(e.target.value)}
            placeholder="Enter your clause text here..."
            rows={6}
            style={{
              marginBottom: '1rem',
              fontSize: '0.9375rem',
            }}
          />

          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Try examples:
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {EXAMPLE_CLAUSES.map((example, idx) => (
                <Tag
                  key={idx}
                  style={{ cursor: 'pointer', padding: '0.5rem 0.75rem' }}
                  onClick={() => setClauseText(example)}
                >
                  {example}
                </Tag>
              ))}
            </div>
          </div>

          <Button
            type="primary"
            size="large"
            icon={<SearchOutlined />}
            onClick={handleCheck}
            loading={loading}
            style={{
              background: 'var(--accent-primary)',
              borderColor: 'var(--accent-primary)',
            }}
          >
            Check Compliance
          </Button>
        </motion.div>

        {results && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {results.matches && results.matches.length > 0 ? (
              <div>
                <h3 style={{ marginBottom: '1rem' }}>Analysis Results ({results.matches.length} matches)</h3>
                {results.matches.map((match, idx) => (
                  <Card
                    key={idx}
                    className="card"
                    style={{ marginBottom: '1rem' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                      <div style={{
                        fontSize: '2rem',
                        color: getSeverityColor(match.combined_score),
                      }}>
                        {getSeverityIcon(match.combined_score)}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                          <div>
                            <h4 style={{ margin: 0, marginBottom: '0.25rem' }}>{match.law_name}</h4>
                            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                              {match.section}
                            </p>
                          </div>
                          <Tag color={match.category === 'labour' ? 'blue' : match.category === 'data_privacy' ? 'purple' : 'default'}>
                            {match.category}
                          </Tag>
                        </div>

                        <div style={{
                          padding: '0.75rem',
                          background: 'var(--bg-tertiary)',
                          borderRadius: '8px',
                          marginBottom: '0.75rem',
                          borderLeft: `3px solid ${getSeverityColor(match.combined_score)}`,
                        }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: getSeverityColor(match.combined_score), marginBottom: '0.25rem' }}>
                            {getSeverityLabel(match.combined_score)}
                          </div>
                          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            Combined Score: {(match.combined_score * 100).toFixed(1)}% | 
                            MiniLM: {(match.miniml_similarity * 100).toFixed(1)}% | 
                            InLegal: {(match.inlegal_similarity * 100).toFixed(1)}%
                          </div>
                        </div>

                        <div style={{ marginBottom: '0.75rem' }}>
                          <div style={{ fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>
                            Law Requirement:
                          </div>
                          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            {match.requirement_text}
                          </div>
                        </div>

                        {match.is_potential_conflict && match.template_fix && (
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                              <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                                Suggested Fix:
                              </div>
                              <Button
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => copyToClipboard(match.template_fix)}
                              >
                                Copy
                              </Button>
                            </div>
                            <div style={{
                              padding: '0.75rem',
                              background: 'var(--bg-tertiary)',
                              borderRadius: '8px',
                              fontFamily: 'monospace',
                              fontSize: '0.875rem',
                              whiteSpace: 'pre-wrap',
                            }}>
                              {match.template_fix}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="card">
                <Empty description="No compliance issues found. This clause appears to be compliant." />
              </div>
            )}
          </motion.div>
        )}
      </div>
    </Layout>
  );
};

export default WhatIfPage;
