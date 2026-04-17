import { router, usePage } from '@inertiajs/react'
import { Link } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Info,
  AlertTriangle,
  Code2,
  Music,
  List,
  FileUp,
  CloudUpload,
  Shield,
  Users,
  ArrowLeft,
} from 'lucide-react'

interface FlashMessage {
  type: string
  text: string
}

interface AliasUploadPageProps {
  messages?: FlashMessage[]
}

function flashClass(type: string): string {
  if (type === 'success') return 'border-green-500/50 bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-400'
  if (type === 'warning') return 'border-yellow-500/40 bg-yellow-50 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400'
  return ''
}

export default function AliasUpload() {
  const { messages } = usePage().props as AliasUploadPageProps

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    router.post('/chart-database/alias-upload/', new FormData(e.currentTarget))
  }

  return (
    <MainLayout>
      <div className="max-w-2xl mx-auto my-8 px-4 flex flex-col gap-4">

        {/* Page header */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-1">
            <span className="text-4xl font-extrabold leading-tight truncate" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)' }}>
              Add Aliases via File
            </span>
          </div>
        </div>

        {/* Format info */}
        <div className="rounded-xl border bg-card shadow-sm overflow-hidden semi-transparent">
          <div className="px-4 py-3 border-b bg-muted/40 flex items-center gap-2">
            <Info className="size-3.5 text-muted-foreground shrink-0" />
            <span className="text-sm text-muted-foreground">
              To bulk upload aliases, use a JSON file with one of these formats:
            </span>
          </div>

          <div className="p-4 flex flex-col gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider">
              <Code2 className="size-3.5" />
              JSON Format Options
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Music className="size-3.5 text-green-600 dark:text-green-400" />
                  <span className="text-xs font-medium text-muted-foreground">Single Song</span>
                </div>
                <pre className="rounded-lg border bg-muted/60 px-3 py-2.5 text-xs font-mono overflow-x-auto leading-relaxed">
                  <code>{`{\n  "chart_name": "Base Song Title (without [DX]/[STD])",\n  "chart_alias": ["alias1", "alias2", "alias3"]\n}`}</code>
                </pre>
              </div>

              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <List className="size-3.5 text-green-600 dark:text-green-400" />
                  <span className="text-xs font-medium text-muted-foreground">Multiple Songs</span>
                </div>
                <pre className="rounded-lg border bg-muted/60 px-3 py-2.5 text-xs font-mono overflow-x-auto leading-relaxed">
                  <code>{`[\n  {\n    "chart_name": "First Song Title",\n    "chart_alias": ["alias1", "alias2"]\n  },\n  {\n    "chart_name": "Second Song Title",\n    "chart_alias": ["alias3", "alias4"]\n  }\n]`}</code>
                </pre>
              </div>
            </div>
          </div>
        </div>

        {/* Important notes */}
        <Alert className="border-yellow-500/40 bg-yellow-50 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400 py-3">
          <AlertTriangle className="size-3.5" />
          <div className="ml-1">
            <p className="text-xs font-semibold mb-1">Important Notes</p>
            <ul className="text-xs list-disc pl-4 flex flex-col gap-0.5 text-yellow-700 dark:text-yellow-400/80">
              <li><strong>chart_name</strong> can be the base title — system will auto-match [DX]/[STD] variants</li>
              <li><strong>chart_alias</strong> must be an array of strings</li>
              <li>If both [DX] and [STD] versions exist, aliases are added to both automatically</li>
              <li>Aliases are appended to existing ones, not replaced</li>
              <li>Duplicate aliases are silently ignored</li>
            </ul>
          </div>
        </Alert>

        {/* Upload form */}
        <div className="rounded-xl border bg-card shadow-sm p-4 flex flex-col gap-3 semi-transparent">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Upload Alias File</p>
            <Link href="/chart-database/">
              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5">
                <ArrowLeft className="size-3" />
                Back
              </Button>
            </Link>
          </div>

          {messages && messages.map((m, i) => (
            <Alert
              key={i}
              variant={m.type === 'danger' ? 'destructive' : 'default'}
              className={`py-2 text-sm ${flashClass(m.type)}`}
              style={{ whiteSpace: 'pre-line' }}
            >
              <AlertDescription>{m.text}</AlertDescription>
            </Alert>
          ))}

          <form onSubmit={handleSubmit} encType="multipart/form-data" className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="alias_file" className="text-sm flex items-center gap-1.5">
                <FileUp className="size-3.5" />
                Select JSON File
              </Label>
              <Input type="file" id="alias_file" name="alias_file" accept=".json" required />
              <p className="text-xs text-muted-foreground">Only JSON files accepted (maximum 5MB).</p>
            </div>
            <Button type="submit" size="lg" className="w-full">
              <CloudUpload data-icon="inline-start" />
              Upload Aliases
            </Button>
          </form>

          <p className="text-center text-xs text-muted-foreground flex items-center justify-center gap-1">
            <Shield className="size-3 shrink-0" />
            File is processed securely and deleted after use
          </p>
        </div>

        {/* Community note */}
        <div className="flex items-start gap-2.5 px-1 pb-2">
          <Users className="size-3.5 text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-xs text-muted-foreground">
            This alias system is community-driven. Your contributions help make song searching easier for everyone.
          </p>
        </div>

      </div>
    </MainLayout>
  )
}
