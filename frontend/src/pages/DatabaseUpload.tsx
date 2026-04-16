import { router, usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Upload } from 'lucide-react'

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
      <div className="max-w-md mx-auto my-12 px-4">
        <div className="rounded-xl border bg-card shadow-sm p-8">
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Upload className="size-4" />
            </div>
            <h1 className="text-xl font-bold">Upload Database</h1>
          </div>
          <p className="text-sm text-muted-foreground mb-6 ml-12">Update the maimai song database JSON</p>

          {message && (
            <p className={`text-sm mb-4 rounded-lg px-3 py-2 ${message.startsWith('Error') ? 'bg-destructive/10 text-destructive' : 'bg-green-50 text-green-700 border border-green-200'}`}>
              {message}
            </p>
          )}

          <form onSubmit={handleSubmit} encType="multipart/form-data" className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="json_file">JSON File</Label>
              <Input type="file" id="json_file" name="json_file" accept=".json" required />
              <p className="text-xs text-muted-foreground">Only .json files accepted.</p>
            </div>
            <Button type="submit" className="w-full">
              <Upload data-icon="inline-start" />
              Upload Database
            </Button>
          </form>
        </div>
      </div>
    </MainLayout>
  )
}
