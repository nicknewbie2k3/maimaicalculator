import { router, usePage } from '@inertiajs/react'
import { Link } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
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
  if (type === 'danger') return ''
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
      <div className="max-w-3xl mx-auto my-8 px-4">
        <Card>
          <CardHeader className="border-b bg-primary text-primary-foreground rounded-t-xl">
            <CardTitle className="flex items-center gap-2 text-primary-foreground">
              <FileUp className="size-5" />
              Add Aliases via File
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-6 pt-6">

            <Alert>
              <Info className="size-4" />
              <AlertTitle>File Format Information</AlertTitle>
              <AlertDescription>
                To bulk upload aliases, use a JSON file with the following format:
              </AlertDescription>
            </Alert>

            <div className="rounded-lg bg-muted p-4 flex flex-col gap-4">
              <h6 className="text-sm font-semibold flex items-center gap-2">
                <Code2 className="size-4 text-primary" />
                JSON Format Options:
              </h6>

              <div>
                <p className="text-sm font-medium flex items-center gap-2 mb-2">
                  <Music className="size-4 text-green-600" />
                  Single Song Format:
                </p>
                <pre className="rounded-lg bg-muted-foreground/10 border p-3 text-sm font-mono overflow-x-auto">
                  <code>{`{\n  "chart_name": "Base Song Title (without [DX]/[STD])",\n  "chart_alias": ["alias1", "alias2", "alias3"]\n}`}</code>
                </pre>
              </div>

              <div>
                <p className="text-sm font-medium flex items-center gap-2 mb-2">
                  <List className="size-4 text-green-600" />
                  Multiple Songs Format:
                </p>
                <pre className="rounded-lg bg-muted-foreground/10 border p-3 text-sm font-mono overflow-x-auto">
                  <code>{`[\n  {\n    "chart_name": "First Song Title",\n    "chart_alias": ["alias1", "alias2"]\n  },\n  {\n    "chart_name": "Second Song Title",\n    "chart_alias": ["alias3", "alias4"]\n  }\n]`}</code>
                </pre>
              </div>
            </div>

            <Alert className="border-yellow-500/40 bg-yellow-50 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400">
              <AlertTriangle className="size-4" />
              <AlertTitle>Important Notes:</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-4 mt-1 flex flex-col gap-1">
                  <li><strong>chart_name</strong> can be the base song title (system will auto-match [DX]/[STD] variants)</li>
                  <li><strong>chart_alias</strong> should be an array of strings</li>
                  <li>If both [DX] and [STD] versions exist, aliases will be added to both automatically</li>
                  <li>Aliases will be added to existing aliases (not replace them)</li>
                  <li>Duplicate aliases will be ignored automatically</li>
                </ul>
              </AlertDescription>
            </Alert>

            <div className="text-center">
              <Link href="/chart-database/">
                <Button variant="secondary">
                  <ArrowLeft data-icon="inline-start" />
                  Back to Chart Database
                </Button>
              </Link>
            </div>

            <Separator />

            <div className="flex flex-col gap-4">
              <h5 className="text-base font-semibold flex items-center gap-2">
                <FileUp className="size-4 text-primary" />
                Upload Alias File
              </h5>

              {messages && messages.map((m, i) => (
                <Alert
                  key={i}
                  variant={m.type === 'danger' ? 'destructive' : 'default'}
                  className={flashClass(m.type)}
                  style={{ whiteSpace: 'pre-line' }}
                >
                  <AlertDescription>{m.text}</AlertDescription>
                </Alert>
              ))}

              <form onSubmit={handleSubmit} encType="multipart/form-data" className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="alias_file" className="flex items-center gap-2">
                    <FileUp className="size-4" />
                    Select JSON File:
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
                <Shield className="size-3" />
                File processed securely and deleted after processing
              </p>
            </div>

            <Separator />

            <div className="text-muted-foreground text-sm flex flex-col gap-1">
              <h6 className="font-semibold flex items-center gap-2">
                <Users className="size-4" />
                Community Feature
              </h6>
              <p>This alias system is community-driven. Your contributions help make song searching easier for everyone.</p>
            </div>

          </CardContent>
        </Card>
      </div>
    </MainLayout>
  )
}
