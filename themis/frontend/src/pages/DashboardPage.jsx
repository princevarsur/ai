import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { format } from 'date-fns';
import { Card, Statistic, Table, Button, Empty, Skeleton } from 'antd';
import { FileTextOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined, PlusOutlined, SearchOutlined, BookOutlined, LineChartOutlined, UploadOutlined } from '@ant-design/icons';
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
import Layout from '../components/Layout';
import { complianceAPI } from '../services/api';

const getSeverityColor = (score) => {
  if (score >= 70) return 'var(--success)';
  if (score >= 40) return 'var(--warning)';
  return 'var(--error)';
};

const DashboardPage = () => {
  const navigate = useNavigate();
  
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const { data } = await complianceAPI.getDashboard();
      setDashboard(data);
    } catch (error) {
      console.error('Failed to load dashboard', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Layout title="Dashboard">
        <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
          <Skeleton active paragraph={{ rows: 10 }} />
        </div>
      </Layout>
    );
  }

  if (!dashboard || dashboard.total_policies_scanned === 0) {
    return (
      <Layout title="Dashboard">
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
            <Empty
              image={<UploadOutlined style={{ fontSize: '4rem', color: 'var(--text-tertiary)' }} />}
              description={
                <div>
                  <h3 style={{ marginTop: '1rem' }}>No policies scanned yet</h3>
                  <p style={{ color: 'var(--text-secondary)' }}>
                    Upload your first policy to get started with compliance scanning
                  </p>
                </div>
              }
            >
              <Button
                type="primary"
                size="large"
                icon={<PlusOutlined />}
                onClick={() => navigate('/upload')}
                style={{
                  marginTop: '1rem',
                  background: 'var(--accent-primary)',
                  borderColor: 'var(--accent-primary)',
                }}
              >
                Upload Policy
              </Button>
            </Empty>
          </div>
        </div>
      </Layout>
    );
  }

  const recentScansColumns = [
    {
      title: 'Policy Name',
      dataIndex: 'policy_title',
      key: 'policy_title',
      render: (text) => <span style={{ fontWeight: 500 }}>{text}</span>,
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
    },
    {
      title: 'Risk Level',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 120,
      render: (level) => {
        const colorMap = {
          LOW: 'var(--success)',
          MEDIUM: 'var(--warning)',
          HIGH: 'var(--error)',
          CRITICAL: 'var(--risk-critical)',
        };
        return (
          <span style={{ color: colorMap[level] || 'var(--text-secondary)', fontWeight: 500 }}>
            {level}
          </span>
        );
      },
    },
    {
      title: 'Date',
      dataIndex: 'scanned_at',
      key: 'scanned_at',
      width: 150,
      render: (date) => {
        try {
          return format(new Date(date), 'MMM dd, yyyy');
        } catch {
          return 'Invalid date';
        }
      },
    },
    {
      title: 'Flags',
      dataIndex: 'flagged_clauses',
      key: 'flagged_clauses',
      width: 80,
      render: (count) => (
        <span style={{ color: count > 0 ? 'var(--warning)' : 'var(--success)' }}>
          {count}
        </span>
      ),
    },
  ];

  const trendData = dashboard.trend_data?.map((item) => {
    try {
      return {
        date: format(new Date(item.date), 'MMM dd'),
        score: item.score,
      };
    } catch {
      return {
        date: 'N/A',
        score: item.score,
      };
    }
  }) || [];

  const categoryData = dashboard.category_breakdown?.map((cat) => ({
    name: cat.category,
    value: cat.avg_score,
  })) || [];

  const COLORS = ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#d1fae5', '#f59e0b', '#fbbf24'];

  return (
    <Layout title="Dashboard">
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header and Quick Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0, color: 'var(--text-primary)' }}>Overview</h2>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/upload')}
              style={{ background: 'var(--accent-primary)', borderColor: 'var(--accent-primary)' }}
            >
              Upload Policy
            </Button>
            <Button
              icon={<SearchOutlined />}
              onClick={() => navigate('/what-if')}
            >
              What-If Checker
            </Button>
          </div>
        </div>

        {/* Top Stats Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="card" style={{ padding: '1rem', height: '100%' }}>
              <Statistic
                title="Total Policies Scanned"
                value={dashboard.total_policies_scanned}
                prefix={<FileTextOutlined style={{ color: 'var(--accent-primary)' }} />}
                valueStyle={{ color: 'var(--text-primary)' }}
              />
            </Card>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="card" style={{ padding: '1rem', height: '100%' }}>
              <Statistic
                title="Average Compliance Score"
                value={dashboard.average_compliance_score}
                suffix="/100"
                valueStyle={{ color: getSeverityColor(dashboard.average_compliance_score) }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="card" style={{ padding: '1rem', height: '100%' }}>
              <Statistic
                title="Total Flagged Issues"
                value={dashboard.total_flagged_issues}
                prefix={<WarningOutlined style={{ color: 'var(--warning)' }} />}
                valueStyle={{ color: 'var(--text-primary)' }}
              />
              <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                {dashboard.resolved_issues || 0} resolved • {dashboard.unresolved_issues || 0} pending
              </div>
            </Card>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="card" style={{ padding: '1rem', height: '100%' }}>
              <Statistic
                title="Critical Flags"
                value={dashboard.critical_count || 0}
                prefix={<CloseCircleOutlined style={{ color: 'var(--risk-critical)' }} />}
                valueStyle={{ color: 'var(--risk-critical)', fontWeight: 700 }}
              />
            </Card>
          </motion.div>
        </div>

        {/* Middle Row: Charts */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '60% 40%',
          gap: '1.5rem',
          marginBottom: '1.5rem',
        }}>
          {/* Trend Chart */}
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>Compliance Score Trend</h3>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                  <XAxis dataKey="date" stroke="var(--text-secondary)" />
                  <YAxis domain={[0, 100]} stroke="var(--text-secondary)" />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="var(--accent-primary)"
                    strokeWidth={2}
                    fill="url(#colorScore)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="No trend data available" />
              </div>
            )}
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>Breakdown</h3>
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {categoryData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '6px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Empty description="No category data available" />
              </div>
            )}
          </div>
        </div>

        {/* Bottom Row: Recent Scans */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Recent Scans</h3>
          <Table
            columns={recentScansColumns}
            dataSource={dashboard.recent_scans || []}
            rowKey="id"
            pagination={false}
            size="middle"
            onRow={(record) => ({
              onClick: () => navigate(`/reports/${record.id}`),
              style: { cursor: 'pointer' },
            })}
          />
        </div>
      </div>
    </Layout>
  );
};

export default DashboardPage;
