import { useState, useEffect } from 'react';
import { Table, Input, Tabs, Tag, Progress, Button, Skeleton, message, Badge } from 'antd';
import { lawsAPI } from '../services/api';
import ThemisMark from '../components/ThemisMark';

const CATEGORY_COLORS = {
  labour: 'blue',
  posh: 'magenta',
  data_privacy: 'purple',
  maternity: 'pink',
  workplace_safety: 'cyan',
  contract: 'geekblue',
  governance: 'gold',
  epf: 'orange',
  default: 'default',
};

export default function LawDatabasePage() {
  const [laws, setLaws]           = useState([]);
  const [loading, setLoading]     = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [copiedId, setCopiedId]   = useState(null);

  useEffect(() => {
    async function fetchLaws() {
      setLoading(true);
      try {
        const res = await lawsAPI.list();
        const data = (res.data && res.data.results) ? res.data.results : (Array.isArray(res.data) ? res.data : []);
        setLaws(data);
      } catch (err) {
        message.error('Failed to load Indian employment law database.');
      } finally {
        setLoading(false);
      }
    }
    fetchLaws();
  }, []);

  function copyTemplate(text, ruleId) {
    navigator.clipboard.writeText(text || '');
    setCopiedId(ruleId);
    message.success('Compliant template copied to clipboard!');
    setTimeout(() => setCopiedId(null), 2000);
  }

  // Build dynamic category list for tabs
  const categories = ['all', ...Array.from(new Set(laws.map(item => item.category || 'general')))];
  const tabItems = categories.map(cat => ({
    key: cat,
    label: cat === 'all' ? 'All Laws & Codes' : cat.replace(/_/g, ' ').toUpperCase(),
  }));

  // Filter laws based on active Category and Search Term
  const filteredLaws = laws.filter(rule => {
    const matchesCategory = activeCategory === 'all' || rule.category === activeCategory;
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = !searchTerm || (
      (rule.law_name || '').toLowerCase().includes(searchLower) ||
      (rule.section || '').toLowerCase().includes(searchLower) ||
      (rule.requirement_text || '').toLowerCase().includes(searchLower) ||
      (rule.template_fix || '').toLowerCase().includes(searchLower)
    );
    return matchesCategory && matchesSearch;
  });

  const columns = [
    {
      title: 'Law / Statutory Code',
      dataIndex: 'law_name',
      key: 'law_name',
      sorter: (a, b) => (a.law_name || '').localeCompare(b.law_name || ''),
      render: (val, record) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--ink)', fontSize: '14px' }}>{val}</div>
          <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{record.section}</div>
        </div>
      ),
      width: '28%',
    },
    {
      title: 'Domain Category',
      dataIndex: 'category',
      key: 'category',
      filters: categories.filter(c => c !== 'all').map(c => ({ text: c.replace(/_/g, ' ').toUpperCase(), value: c })),
      onFilter: (value, record) => record.category === value,
      render: (cat) => (
        <Tag color={CATEGORY_COLORS[cat] || CATEGORY_COLORS.default} style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.04em' }}>
          {(cat || 'General').replace(/_/g, ' ')}
        </Tag>
      ),
      width: '18%',
    },
    {
      title: 'Severity Weight',
      dataIndex: 'severity_weight',
      key: 'severity_weight',
      sorter: (a, b) => (a.severity_weight || 0) - (b.severity_weight || 0),
      render: (val) => {
        const pct = Math.min(100, (val || 5) * 10);
        let color = '#4A7856';
        if (val >= 8) color = '#A33F3F';
        else if (val >= 6) color = '#A67C3D';
        return (
          <div style={{ width: 120 }}>
            <div style={{ fontSize: '11px', color: 'var(--muted)', display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <span>Weight {val}/10</span>
              <span style={{ color, fontWeight: 600 }}>{val >= 8 ? 'High' : val >= 6 ? 'Med' : 'Low'}</span>
            </div>
            <Progress percent={pct} showInfo={false} strokeColor={color} size="small" />
          </div>
        );
      },
      width: '18%',
    },
    {
      title: 'Statutory Obligation Summary',
      dataIndex: 'requirement_text',
      key: 'requirement',
      render: (text) => (
        <div style={{ fontSize: '13px', color: 'var(--ink-2)', lineHeight: '1.5', maxWidth: '480px', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
          {text}
        </div>
      ),
      width: '28%',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? '#4A7856' : 'default'} style={{ margin: 0, fontWeight: 500 }}>
          {active ? 'ACTIVE' : 'INACTIVE'}
        </Tag>
      ),
      width: '8%',
    },
  ];

  const expandable = {
    expandedRowRender: (record) => (
      <div style={{ background: 'var(--bg)', padding: '24px 32px', border: '1px solid var(--hairline-2)', borderRadius: '6px', margin: '8px 0' }}>
        <div style={{ marginBottom: '20px' }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.08em', display: 'block', marginBottom: '6px' }}>
            Full Statutory Mandate:
          </span>
          <p style={{ fontSize: '14px', color: 'var(--ink)', lineHeight: '1.6', margin: 0 }}>
            {record.requirement_text}
          </p>
        </div>



        {record.template_fix && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#334155', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                ✓ Pre-Validated Compliant Template Clause:
              </span>
              <Button
                size="small"
                onClick={() => copyTemplate(record.template_fix, record.id)}
                style={{ fontSize: '12px', background: 'white', borderColor: '#CBD5E1' }}
              >
                {copiedId === record.id ? 'Copied!' : 'Copy Template Fix'}
              </Button>
            </div>
            <div style={{ background: 'var(--accent-soft)', border: '1px solid #CBD5E1', color: '#1E293B', padding: '14px 16px', borderRadius: '4px', fontFamily: "'IBM Plex Mono', monospace", fontSize: '13px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
              {record.template_fix}
            </div>
          </div>
        )}
      </div>
    ),
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '16px', marginBottom: '28px' }}>
        <div>
          <h1 style={{ fontFamily: "'Newsreader', serif", fontSize: '32px', color: 'var(--ink)', fontWeight: 500 }}>
            Statutory Law Database
          </h1>
          <p style={{ fontSize: '15px', color: 'var(--muted)', marginTop: '4px' }}>
            Browse active Indian labour codes, corporate regulations, DPDP rules, and POSH mandates enforced by the compliance engine.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--surface)', padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--hairline)' }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#4A7856', display: 'inline-block' }} />
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink-2)' }}>
            {laws.length} Active Rules Loaded
          </span>
        </div>
      </div>

      {/* Filter and Search controls */}
      <div style={{ background: 'var(--surface)', padding: '20px 24px', borderRadius: '8px', border: '1px solid var(--hairline)', marginBottom: '24px' }}>
        <Input.Search
          placeholder="Search by law name, section, keyword, or requirement text..."
          allowClear
          size="large"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ maxWidth: '600px', marginBottom: '16px' }}
        />
        
        <Tabs
          activeKey={activeCategory}
          onChange={setActiveCategory}
          items={tabItems}
          style={{ marginBottom: '-16px', fontWeight: 500 }}
        />
      </div>

      {/* Main Table */}
      <div style={{ background: 'var(--surface)', borderRadius: '8px', border: '1px solid var(--hairline)', padding: '12px 20px', overflow: 'hidden' }}>
        <Table
          columns={columns}
          dataSource={filteredLaws}
          rowKey="id"
          loading={loading}
          expandable={expandable}
          pagination={{ pageSize: 15, showSizeChanger: true, pageSizeOptions: ['10', '15', '25', '50'], showTotal: (total) => `Total ${total} rules` }}
          style={{ background: 'transparent' }}
        />
      </div>
    </div>
  );
}
