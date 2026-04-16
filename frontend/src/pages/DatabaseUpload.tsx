import { router, usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'

interface DatabaseUploadPageProps {
  message?: string
}

export default function DatabaseUpload() {
  const { message } = usePage().props as DatabaseUploadPageProps

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    router.post('/databaseUpload/', new FormData(e.currentTarget))
  }

  return (
    <MainLayout>
      <div className="container my-4" style={{ maxWidth: 600 }}>
        <h1>Upload Maimai Database JSON</h1>
        {message && (
          <p className={message.startsWith('Error') ? 'text-danger' : 'text-success'}>{message}</p>
        )}
        <form onSubmit={handleSubmit} encType="multipart/form-data">
          <div className="mb-3">
            <input type="file" className="form-control" name="json_file" accept=".json" required />
          </div>
          <button type="submit" className="btn btn-primary">Upload</button>
        </form>
      </div>
    </MainLayout>
  )
}
