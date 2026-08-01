import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { Table, Input, Tag, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import Layout from '../components/Layout';
import { complianceAPI } from '../services/api';

const { Search } = Input;

const getSeverityColor = (score) => {
  if (score >= 70) return 'var(--success)';
  if (score >= 40) return 'var(--warning)';
  return 'var(--error)';
};

const ReportsPage = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [filteredReports, setFilteredReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    fetchReports();
  }, []);

  useEffect(() => {
    filterReports();
  }, [reports, searchText]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const { data } = await complianceAPI.getReports();
      // Handle both paginated {results: [...]} and direct array
      const reportsData = Array.isArray(data) ? data : (data.results || []);
      setReports(reportsData);
    } catch (error) {
      message.error('Failed to load scan history');
    } finally {
      setLoading(false);
    }
  };

  const filterReports = () => {
    if (!searchText) {
      setFilteredReports(reports);
      return;
    }

    const search = searchText.toLowerCase();
    const filtered = reports.filter(report =>
      report.policy_title?.toLowerCase().includes(search)
    );
    setFilteredReports(filtered);
  };

  const columns = [
    {
      title: 'Policy Name',
      dataIndex: 'policy_title',
      key: 'policy_title',
      render: (text) => <span style={{ fontWeight: 500 }}>{text}</span>,
      sorter: (a, b) => (a.policy_title || '').localeCompare(b.policy_title || ''),
    },
    {
      title: 'Score',
      dataIndex: 'overall_score',
      key: 'overall_score',
      width: 100,
      render: (score) => (
        <span style={{ color: getSeverityColor(score), fontWeight: 600 }}>
          {score}
        </span>
      ),
      sorter: (a, b) => a.overall_score - b.overall_score,
      defaultSortOrder: 'descend',
    },
    {
      title: 'Risk Level',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 130,
      render: (level) => {
        const colorMap = {
          LOW: 'success',
          MEDIUM: 'warning',
          HIGH: 'error',
          CRITICAL: 'error',
        };
        return <Tag color={colorMap[level] || 'default'}>{level}</Tag>;
      },
      filters: [
        { text: 'Low', value: 'LOW' },
        { text: 'Medium', value: 'MEDIUM' },
        { text: 'High', value: 'HIGH' },
        { text: 'Critical', value: 'CRITICAL' },
      ],
      onFilter: (value, record) => record.risk_level === value,
    },
    {
      title: 'Total Clauses',
      dataIndex: 'total_clauses',
      key: 'total_clauses',
      width: 120,
    },
    {
      title: 'Flagged',
      dataIndex: 'flagged_clauses',
      key: 'flagged_clauses',
      width: 100,
      render: (count) => (
        <span style={{ color: count > 0 ? 'var(--warning)' : 'var(--success)' }}>
          {count}
        </span>
      ),
    },
    {
      title: 'Scan Date',
      dataIndex: 'scanned_at',
      key: 'scanned_at',
      width: 150,
      render: (date) => {
        try {
          return format(new Date(date), 'MMM dd, yyyy HH:mm');
        } catch {
          return 'Invalid date';
        }
      },
      sorter: (a, b) => new Date(a.scanned_at) - new Date(b.scanned_at),
    },
  ];

  return (
    <Layout title="Scan History">
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div style={{ marginBottom: '1.5rem' }}>
            <Search
              placeholder="Search by policy name"
              prefix={<SearchOutlined />}
              onChange={(e) => setSearchText(e.target.value)}
              size="large"
            />
          </div>

          <div className="card">
            <Table
              columns={columns}
              dataSource={filteredReports}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 15, showSizeChanger: true }}
              onRow={(record) => ({
                onClick: () => navigate(`/reports/${record.id}`),
                style: { cursor: 'pointer' },
              })}
            />
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default ReportsPage;
