import { Link } from '@inertiajs/react'
import React from 'react'

export default function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <div className="container" style={{ maxWidth: 800, marginTop: 24, marginBottom: 0, background: 'none', boxShadow: 'none', padding: '16px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem' }}>
          <Link href="/" className="button">Rating Calculator</Link>
          <Link href="/chart-database/" className="button">Chart Database</Link>
          <Link href="/databaseUpload/" className="button">Database Upload</Link>
        </div>
      </div>
      {children}
    </div>
  )
}
