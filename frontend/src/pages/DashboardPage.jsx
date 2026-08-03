export default function DashboardPage() {
  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Compliance posture across all submitted policies</p>
      </div>
      <div className="placeholder-block">
        <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-2)' }}>
          Phase 13
        </h4>
        <p>Score overview, recent scans, issue breakdown by law</p>
      </div>
    </div>
  );
}
