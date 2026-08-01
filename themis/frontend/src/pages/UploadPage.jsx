import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Select, Button, Spin, message } from 'antd';
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';
import Layout from '../components/Layout';
import { policiesAPI, complianceAPI } from '../services/api';

const { Dragger } = Upload;

const CATEGORIES = [
  { label: 'General', value: 'general' },
  { label: 'Labour Law', value: 'labour' },
  { label: 'Data Privacy', value: 'data_privacy' },
  { label: 'Workplace Safety', value: 'workplace_safety' },
  { label: 'Employee Benefits', value: 'employee_benefits' },
  { label: 'Corporate Governance', value: 'corporate_governance' },
  { label: 'Cyber Security', value: 'cyber_security' },
];

const UploadPage = () => {
  const navigate = useNavigate();
  
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('general');
  const [uploading, setUploading] = useState(false);
  const [uploadedPolicy, setUploadedPolicy] = useState(null);
  const [scanning, setScanning] = useState(false);

  const uploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.docx,.txt',
    maxCount: 1,
    beforeUpload: (file) => {
      const isValidType = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'].includes(file.type);
      if (!isValidType) {
        message.error('Only PDF, DOCX, and TXT files are supported');
        return Upload.LIST_IGNORE;
      }

      const isValidSize = file.size / 1024 / 1024 < 10;
      if (!isValidSize) {
        message.error('File must be smaller than 10MB');
        return Upload.LIST_IGNORE;
      }

      setFile(file);
      const filename = file.name.replace(/\.[^/.]+$/, '');
      setTitle(filename);
      return false;
    },
    onRemove: () => {
      setFile(null);
      setTitle('');
      setUploadedPolicy(null);
    },
  };

  const handleUpload = async () => {
    if (!file) {
      message.error('Please select a file');
      return;
    }

    if (!title.trim()) {
      message.error('Please enter a policy title');
      return;
    }

    setUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', title);
      formData.append('category', category);

      const { data } = await policiesAPI.upload(formData);
      
      message.success('Policy uploaded successfully');
      
      // Backend returns {policy: {...}, extraction_stats: {...}}
      const mergedData = {
        ...data.policy,
        word_count: data.extraction_stats?.word_count || 0,
        page_count: data.extraction_stats?.page_count || 0,
      };
      
      setUploadedPolicy(mergedData);
    } catch (error) {
      message.error(error.response?.data?.error || 'Failed to upload policy');
    } finally {
      setUploading(false);
    }
  };

  const handleScan = async () => {
    if (!uploadedPolicy?.id) return;

    setScanning(true);

    try {
      const { data } = await complianceAPI.triggerScan(uploadedPolicy.id);
      
      message.success('Scan completed successfully');
      navigate(`/reports/${data.id}`);
    } catch (error) {
      message.error(error.response?.data?.error || 'Failed to run compliance scan');
      setScanning(false);
    }
  };

  return (
    <Layout title="Upload Policy">
      <div style={{
        maxWidth: '800px',
        margin: '0 auto',
      }}>
        {!uploadedPolicy ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            <h2 style={{ marginBottom: '1.5rem' }}>Upload Policy Document</h2>

            <Dragger
              {...uploadProps}
              style={{
                background: 'var(--bg-tertiary)',
                border: '2px dashed var(--border-color)',
                borderRadius: '8px',
                marginBottom: '1.5rem',
              }}
            >
              <p style={{ fontSize: '3rem', margin: '1rem 0' }}>
                <InboxOutlined style={{ color: 'var(--accent-primary)' }} />
              </p>
              <p style={{
                fontSize: '1rem',
                fontWeight: 500,
                color: 'var(--text-primary)',
                marginBottom: '0.5rem',
              }}>
                Click or drag file to upload
              </p>
              <p style={{
                fontSize: '0.875rem',
                color: 'var(--text-tertiary)',
              }}>
                Supports PDF, DOCX, TXT (max 10MB)
              </p>
            </Dragger>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                marginBottom: '0.5rem',
                color: 'var(--text-secondary)',
              }}>
                Policy Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter policy title"
                disabled={!file}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: 500,
                marginBottom: '0.5rem',
                color: 'var(--text-secondary)',
              }}>
                Category
              </label>
              <Select
                value={category}
                onChange={setCategory}
                disabled={!file}
                style={{ width: '100%' }}
                size="large"
              >
                {CATEGORIES.map((cat) => (
                  <Select.Option key={cat.value} value={cat.value}>
                    {cat.label}
                  </Select.Option>
                ))}
              </Select>
            </div>

            <Button
              type="primary"
              size="large"
              onClick={handleUpload}
              loading={uploading}
              disabled={!file || uploading}
              style={{
                width: '100%',
                height: '48px',
                background: 'var(--accent-primary)',
                borderColor: 'var(--accent-primary)',
                fontSize: '1rem',
                fontWeight: 600,
              }}
            >
              {uploading ? 'Uploading...' : 'Upload Policy'}
            </Button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="card"
            style={{
              textAlign: 'center',
              padding: '3rem 2rem',
            }}
          >
            <div style={{
              fontSize: '4rem',
              color: 'var(--success)',
              marginBottom: '1rem',
            }}>
              <CheckCircleOutlined />
            </div>

            <h2 style={{ marginBottom: '0.5rem' }}>Upload Successful</h2>
            <p style={{
              color: 'var(--text-secondary)',
              marginBottom: '2rem',
            }}>
              {uploadedPolicy.title}
            </p>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '1rem',
              marginBottom: '2rem',
              padding: '1.5rem',
              background: 'var(--bg-tertiary)',
              borderRadius: '8px',
            }}>
              <div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: 'var(--accent-primary)',
                }}>
                  {uploadedPolicy.word_count || 0}
                </div>
                <div style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-tertiary)',
                }}>
                  Words
                </div>
              </div>
              <div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: 'var(--accent-primary)',
                }}>
                  {uploadedPolicy.clause_count || 0}
                </div>
                <div style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-tertiary)',
                }}>
                  Clauses
                </div>
              </div>
              <div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 600,
                  color: 'var(--accent-primary)',
                }}>
                  {uploadedPolicy.file_type || 'PDF'}
                </div>
                <div style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-tertiary)',
                }}>
                  Format
                </div>
              </div>
            </div>

            {scanning ? (
              <div>
                <Spin size="large" />
                <p style={{
                  marginTop: '1rem',
                  color: 'var(--text-secondary)',
                }}>
                  Scanning policy for compliance issues...
                  <br />
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-tertiary)' }}>
                    This may take 15-30 seconds
                  </span>
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '1rem' }}>
                <Button
                  size="large"
                  onClick={() => {
                    setFile(null);
                    setTitle('');
                    setCategory('general');
                    setUploadedPolicy(null);
                  }}
                  style={{
                    flex: 1,
                    height: '48px',
                    fontSize: '1rem',
                  }}
                >
                  Upload Another
                </Button>
                <Button
                  type="primary"
                  size="large"
                  onClick={handleScan}
                  style={{
                    flex: 2,
                    height: '48px',
                    background: 'var(--accent-primary)',
                    borderColor: 'var(--accent-primary)',
                    fontSize: '1rem',
                    fontWeight: 600,
                  }}
                >
                  Run Compliance Scan
                </Button>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </Layout>
  );
};

export default UploadPage;
