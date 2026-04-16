export default function MainLayout({ children }) {
  return (
    <div>
      <div className="container" style={{ maxWidth: 800, marginTop: 24, marginBottom: 0, background: 'none', boxShadow: 'none', padding: '16px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem' }}>
          <a href="/" className="button">Rating Calculator</a>
          <a href="/chart-database/" className="button">Chart Database</a>
          <a href="/databaseUpload/" className="button">Database Upload</a>
        </div>
      </div>
      {children}
    </div>
  )
}
