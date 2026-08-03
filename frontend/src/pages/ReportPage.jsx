export default function ReportPage() {
  return (
    <div>
      <div className="page-header">
        <h1>Compliance Report</h1>
        <p>Detailed findings with flagged clauses, severity scores, and remediation notes</p>
      </div>
      <div className="placeholder-block">
        <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-2)' }}>
          Phase 13
        </h4>
        <p>Score gauge, issue list, per-clause detail, PDF export</p>
      </div>
    </div>
  );
}
