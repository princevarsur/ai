export default function UploadPage() {
  return (
    <div>
      <div className="page-header">
        <h1>Upload Policy</h1>
        <p>Submit a PDF or DOCX for automated compliance scanning</p>
      </div>
      <div className="placeholder-block">
        <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted-2)' }}>
          Phase 13
        </h4>
        <p>Drag-and-drop upload, scan trigger, processing indicator</p>
      </div>
    </div>
  );
}
