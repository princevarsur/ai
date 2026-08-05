import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, message } from 'antd';
import { policiesAPI, complianceAPI } from '../services/api';
import ThemisMark from '../components/ThemisMark';
import ChalkBookLoader from '../components/ChalkBookLoader';

const { Dragger } = Upload;

const CATEGORY_OPTIONS = [
  { value: 'general',              label: 'General Policy' },
  { value: 'labour',               label: 'Labour Law & Employment' },
  { value: 'data_privacy',         label: 'Data Privacy & Protection' },
  { value: 'workplace_safety',     label: 'Workplace Safety & POSH' },
  { value: 'employee_benefits',    label: 'Employee Benefits & Gratuity' },
  { value: 'corporate_governance', label: 'Corporate Governance' },
  { value: 'cyber_security',       label: 'Cyber Security & IT' },
];

export default function UploadPage() {
  const navigate = useNavigate();

  // File & form state
  const [file, setFile]           = useState(null);
  const [title, setTitle]         = useState('');
  const [category, setCategory]   = useState('general');
  const [error, setError]         = useState('');

  // Execution steps: 'idle' | 'uploading' | 'extracted' | 'scanning'
  const [step, setStep]           = useState('idle');
  const [policyData, setPolicyData] = useState(null);
  const [stats, setStats]         = useState(null);

  // ── Handle file selection & validation ──────────────────────────
  function handleBeforeUpload(newFile) {
    setError('');
    const isValidType = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', '.pdf', '.docx', '.txt'].some(
      t => newFile.type === t || newFile.name.toLowerCase().endsWith(t)
    );

    if (!isValidType) {
      const msg = 'Unsupported file format. Please submit a PDF, DOCX, or TXT document.';
      setError(msg);
      message.error(msg);
      return Upload.LIST_IGNORE;
    }

    const isLt10M = newFile.size / 1024 / 1024 <= 10;
    if (!isLt10M) {
      const msg = 'File size exceeds the 10MB limit.';
      setError(msg);
      message.error(msg);
      return Upload.LIST_IGNORE;
    }

    setFile(newFile);
    // Auto-fill title without extension
    const baseName = newFile.name.replace(/\.[^/.]+$/, '');
    setTitle(baseName);
    setStep('idle');
    return false; // Prevent automatic HTTP post by Antd Dragger
  }

  function handleRemove() {
    setFile(null);
    setTitle('');
    setError('');
    setStep('idle');
  }

  // ── Step 1: Upload & Extract Text ───────────────────────────────
  async function handleUpload(e) {
    e.preventDefault();
    if (!file) { setError('Please select a policy document first.'); return; }
    if (!title.trim()) { setError('Policy title is required.'); return; }

    setStep('uploading');
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title.trim());
    formData.append('category', category);

    try {
      const res = await policiesAPI.upload(formData);
      const { policy, extraction_stats, extraction_warning } = res.data;

      setPolicyData(policy);
      setStats(extraction_stats || {
        word_count: policy.extracted_text?.split(/\s+/).length || 0,
        clause_count: policy.clause_count || 0,
        file_type: policy.file_type || file.name.split('.').pop().toUpperCase(),
      });

      if (extraction_warning) {
        message.warning('Uploaded with extraction warning: ' + extraction_warning);
      } else {
        message.success('Document uploaded and clauses extracted successfully.');
      }
      setStep('extracted');
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.response?.data?.file?.[0] || 'Server error during upload.';
      setError(errMsg);
      message.error(errMsg);
      setStep('idle');
    }
  }

  // ── Step 2: Trigger ML Compliance Scan ─────────────────────────
  async function handleRunScan() {
    if (!policyData?.id) return;
    setStep('scanning');
    setError('');

    try {
      const res = await complianceAPI.triggerScan(policyData.id);
      message.success('Compliance scan completed!');
      navigate(`/reports/${res.data.id}`);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Execution failed during AI scan sequence.';
      setError(errMsg);
      message.error(errMsg);
      setStep('extracted');
    }
  }

  return (
    <div style={{ maxWidth: 840, margin: '0 auto' }}>
      {/* ── Page Header ────────────────────────────────────────── */}
      <div className="page-header">
        <h1>Upload Policy Document</h1>
        <p>Submit a corporate handbook or HR policy for multi-signal legal compliance verification</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 24 }}>{error}</div>}

      {/* ── STATE: Scanning (Transparent Charcoal Book Animation) ── */}
      {step === 'scanning' ? (
        <div className="panel" style={{ padding: '64px 32px', textAlign: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
            <ChalkBookLoader size={68} />
          </div>
          <h2 style={{ fontFamily: "'Newsreader', serif", fontSize: 24, marginBottom: 8, color: 'var(--ink)' }}>
            Analyzing Legal Clauses
          </h2>
          <p style={{ maxWidth: 420, margin: '0 auto 24px', color: 'var(--muted)' }}>
            Running semantic embedding matching, deterministic numeric bound verifications, and NLI contradiction detection across active statutes.
          </p>
          <div className="mono" style={{ color: 'var(--accent)', fontSize: 12, letterSpacing: '0.04em' }}>
            PROCESSING... THIS MAY TAKE 15–30 SECONDS
          </div>
        </div>
      ) : (
        /* ── STATE: Idle / Uploading / Extracted ───────────────── */
        <div className="panel" style={{ transition: 'all var(--t)' }}>
          {/* Section 1: Drag & Drop Zone */}
          <div className="panel-section" style={{ padding: '32px' }}>
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span className="label-sm">Document Source</span>
              <span className="mono" style={{ color: 'var(--muted-2)' }}>MAX 10MB • PDF, DOCX, TXT</span>
            </div>

            <Dragger
              name="file"
              multiple={false}
              fileList={file ? [file] : []}
              beforeUpload={handleBeforeUpload}
              onRemove={handleRemove}
              disabled={step === 'uploading'}
              className="themis-dropzone"
              style={{
                background: file ? 'var(--surface-hover, #1E2228)' : 'var(--bg)',
                border: file ? '1.5px solid var(--success)' : '1px dashed var(--hairline-2)',
                borderRadius: 'var(--r-sm, 6px)',
                padding: '36px 24px',
                transition: 'border-color 0.25s cubic-bezier(0.16, 1, 0.3, 1), background 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                cursor: 'pointer',
                boxShadow: file ? '0 0 16px rgba(74, 120, 86, 0.12)' : 'none',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div style={{ transform: 'scale(1)', transition: 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)' }}>
                  <ThemisMark
                    size={44}
                    color={file ? 'var(--success)' : 'var(--accent)'}
                    thinking={step === 'uploading' || step === 'scanning'}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: file ? 'var(--success)' : 'var(--ink)', transition: 'color 0.2s ease-out' }}>
                    {file ? `Selected: ${file.name}` : 'Click or drag policy file here to weigh compliance'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                    {file ? 'Ready for deep statutory extraction and multi-signal scoring' : 'Supports corporate policy manuals and handbook text formats'}
                  </div>
                </div>
              </div>
            </Dragger>
          </div>

          {/* Section 2: Metadata Form */}
          <form onSubmit={handleUpload}>
            <div className="panel-section" style={{ padding: '24px 32px', display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 24 }}>
              <div className="form-group">
                <label className="form-label" htmlFor="title">Policy Title</label>
                <input
                  id="title"
                  name="title"
                  type="text"
                  className="form-input"
                  placeholder="e.g., TechNova Employee HR Policy 2026"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                  disabled={step !== 'idle'}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="category">Law Category</label>
                <select
                  id="category"
                  name="category"
                  className="form-input form-select"
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  disabled={step !== 'idle'}
                >
                  {CATEGORY_OPTIONS.map(c => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Section 3: Action & Post-Upload Extraction Stats */}
            <div className="panel-section" style={{ padding: '20px 32px', background: 'var(--bg)', borderTop: '1px solid var(--hairline)' }}>
              {step === 'idle' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                  {file && (
                    <button type="button" className="btn btn-secondary" onClick={handleRemove}>
                      Clear
                    </button>
                  )}
                  <button
                    type="submit"
                    className="btn btn-primary btn-lg"
                    disabled={!file || !title.trim()}
                  >
                    Upload & Extract Text
                  </button>
                </div>
              )}

              {step === 'uploading' && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '8px 0' }}>
                  <ThemisMark size={24} color="var(--accent)" thinking={true} />
                  <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>
                    Uploading document and running semantic clause parser...
                  </span>
                </div>
              )}

              {step === 'extracted' && stats && (
                <div style={{ animation: 'fadeIn 200ms ease-out' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="badge badge-ok">EXTRACTED</span>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)' }}>Ready for Compliance Engine</span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => { setStep('idle'); setPolicyData(null); }}
                    >
                      Upload different file
                    </button>
                  </div>

                  {/* Stats display */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 16,
                    padding: '16px',
                    background: 'var(--surface)',
                    border: '1px solid var(--hairline)',
                    borderRadius: 4,
                    marginBottom: 20,
                  }}>
                    <div>
                      <div className="label-sm">Total Words</div>
                      <div className="mono" style={{ fontSize: 18, fontWeight: 500, color: 'var(--ink)', marginTop: 4 }}>
                        {stats.word_count || '—'}
                      </div>
                    </div>
                    <div>
                      <div className="label-sm">Parsed Clauses</div>
                      <div className="mono" style={{ fontSize: 18, fontWeight: 500, color: 'var(--ink)', marginTop: 4 }}>
                        {stats.clause_count || 0}
                      </div>
                    </div>
                    <div>
                      <div className="label-sm">Document Type</div>
                      <div className="mono" style={{ fontSize: 16, fontWeight: 500, color: 'var(--ink)', marginTop: 4, textTransform: 'uppercase' }}>
                        {stats.file_type || policyData?.file_type || 'TXT'}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-lg"
                      onClick={handleRunScan}
                    >
                      Run Compliance Scan
                    </button>
                  </div>
                </div>
              )}
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
