import { router, usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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
      <div className="max-w-lg mx-auto my-8 px-4">
        <h1 className="text-2xl font-semibold mb-4">Upload Maimai Database JSON</h1>
        {message && (
          <p className={message.startsWith('Error') ? 'text-destructive text-sm mb-3' : 'text-green-600 text-sm mb-3'}>
            {message}
          </p>
        )}
        <form onSubmit={handleSubmit} encType="multipart/form-data" className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="json_file">JSON File</Label>
            <Input type="file" id="json_file" name="json_file" accept=".json" required />
          </div>
          <div>
            <Button type="submit">Upload</Button>
          </div>
        </form>
      </div>
    </MainLayout>
  )
}
