export default function WhatIfPage() {
  return (
    <div>
      <div className="page-header">
        <h1>What-If Checker</h1>
        <p>Test a single policy clause against all active legal rules before committing to a scan</p>
      </div>
      <div className="placeholder-block">
        <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-2)' }}>
          Phase 13
        </h4>
        <p>Paste clause text, run instant check, inspect all signal scores</p>
      </div>
    </div>
  );
}
