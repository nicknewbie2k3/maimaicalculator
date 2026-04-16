import { useEffect, useState } from 'react'
import { usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'

export default function DatabaseUpload() {
  const { message } = usePage().props
  const [csrf, setCsrf] = useState('')

  useEffect(() => {
    const c = document.cookie.split(';').find(s => s.trim().startsWith('csrftoken='))
    if (c) setCsrf(decodeURIComponent(c.trim().slice('csrftoken='.length)))
  }, [])

  return (
    <MainLayout>
      <div className="container my-4" style={{ maxWidth: 600 }}>
        <h1>Upload Maimai Database JSON</h1>
        {message && (
          <p className={message.startsWith('Error') ? 'text-danger' : 'text-success'}>{message}</p>
        )}
        <form method="post" encType="multipart/form-data" action="/databaseUpload/">
          <input type="hidden" name="csrfmiddlewaretoken" value={csrf} readOnly />
          <div className="mb-3">
            <input type="file" className="form-control" name="json_file" accept=".json" required />
          </div>
          <button type="submit" className="btn btn-primary">Upload</button>
        </form>
      </div>
    </MainLayout>
  )
}
