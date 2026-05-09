import { router, usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Upload, FileSpreadsheet } from 'lucide-react'
import { useState } from 'react'

interface DatabaseUploadPageProps {
  message?: string
  skill_import_message?: string
}

export default function DatabaseUpload() {
  const { message, skill_import_message } = usePage().props as DatabaseUploadPageProps
  const [skillFile, setSkillFile] = useState<File | null>(null)

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    router.post('/databaseUpload/', new FormData(e.currentTarget))
  }

  const handleSkillImport = () => {
    if (!skillFile) return

    const formData = new FormData()
    formData.append('json_file', skillFile)
    router.post('/import-skill-analyzer/', formData)
  }

  return (
    <MainLayout>
      <div className="max-w-md mx-auto my-12 px-4 space-y-8">
        {/* Database Upload Section */}
        <div className="rounded-xl border bg-card shadow-sm p-8 semi-transparent">
          <div className="text-center mb-6">
            <span className="text-3xl font-extrabold leading-tight" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)' }}>
              Upload Database
            </span>
          </div>
          <p className="text-sm text-muted-foreground mb-6">Update the maimai song database JSON</p>

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

        {/* Skill Analyzer Import Section */}
        <div className="rounded-xl border bg-card shadow-sm p-8 semi-transparent">
          <div className="text-center mb-6">
            <span className="text-3xl font-extrabold leading-tight" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)' }}>
              Import Skill Analyzer
            </span>
          </div>
          <p className="text-sm text-muted-foreground mb-6">Import skill analyzer JSON to add analyzed skills data</p>

          {skill_import_message && (
            <p className={`text-sm mb-4 rounded-lg px-3 py-2 ${skill_import_message.startsWith('Error') ? 'bg-destructive/10 text-destructive' : 'bg-green-50 text-green-700 border border-green-200'}`}>
              {skill_import_message}
            </p>
          )}

          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="skill_json_file">JSON File</Label>
              <Input
                type="file"
                id="skill_json_file"
                accept=".json"
                onChange={(e) => {
                  const file = e.target.files?.[0] || null
                  setSkillFile(file)
                }}
              />
              <p className="text-xs text-muted-foreground">Only .json files accepted (reformatted skill analyzer output).</p>
            </div>
            <Button
              type="button"
              className="w-full"
              onClick={handleSkillImport}
              disabled={!skillFile}
            >
              <FileSpreadsheet data-icon="inline-start" />
              Import Skill Analyzer
            </Button>
          </div>
        </div>
      </div>
    </MainLayout>
  )
}