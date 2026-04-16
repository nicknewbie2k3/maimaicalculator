import { router, usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'

interface FlashMessage {
  type: string
  text: string
}

interface AliasUploadPageProps {
  messages?: FlashMessage[]
}

export default function AliasUpload() {
  const { messages } = usePage().props as AliasUploadPageProps

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    router.post('/chart-database/alias-upload/', new FormData(e.currentTarget))
  }

  return (
    <MainLayout>
      <div className="container my-4">
        <div className="row justify-content-center">
          <div className="col-md-10 col-lg-8">
            <div className="card shadow">
              <div className="card-header bg-primary text-white">
                <h3 className="card-title mb-0"><i className="fas fa-file-upload me-2" />Add Aliases via File</h3>
              </div>
              <div className="card-body">

                <div className="alert alert-info">
                  <h5><i className="fas fa-info-circle me-2" />File Format Information</h5>
                  <p className="mb-0">To bulk upload aliases, use a JSON file with the following format:</p>
                </div>

                <div className="bg-light p-4 rounded">
                  <h6 className="text-primary mb-3"><i className="fas fa-code me-2" />JSON Format Options:</h6>
                  <div className="mb-4">
                    <h6 className="text-success"><i className="fas fa-music me-2" />Single Song Format:</h6>
                    <pre className="bg-dark text-light p-3 rounded"><code>{`{\n  "chart_name": "Base Song Title (without [DX]/[STD])",\n  "chart_alias": ["alias1", "alias2", "alias3"]\n}`}</code></pre>
                  </div>
                  <div className="mb-3">
                    <h6 className="text-success"><i className="fas fa-list me-2" />Multiple Songs Format:</h6>
                    <pre className="bg-dark text-light p-3 rounded"><code>{`[\n  {\n    "chart_name": "First Song Title",\n    "chart_alias": ["alias1", "alias2"]\n  },\n  {\n    "chart_name": "Second Song Title",\n    "chart_alias": ["alias3", "alias4"]\n  }\n]`}</code></pre>
                  </div>
                </div>

                <div className="alert alert-warning mt-4">
                  <h6><i className="fas fa-exclamation-triangle me-2" />Important Notes:</h6>
                  <ul className="mb-0">
                    <li><strong>chart_name</strong> can be the base song title (system will auto-match [DX]/[STD] variants)</li>
                    <li><strong>chart_alias</strong> should be an array of strings</li>
                    <li>If both [DX] and [STD] versions exist, aliases will be added to both automatically</li>
                    <li>Aliases will be added to existing aliases (not replace them)</li>
                    <li>Duplicate aliases will be ignored automatically</li>
                  </ul>
                </div>

                <div className="mt-4 text-center">
                  <a href="/chart-database/" className="btn btn-secondary">
                    <i className="fas fa-arrow-left me-2" />Back to Chart Database
                  </a>
                </div>

                <hr className="my-4" />

                <div className="bg-light p-4 rounded">
                  <h5 className="text-primary mb-3"><i className="fas fa-upload me-2" />Upload Alias File</h5>

                  {messages && messages.map((m, i) => (
                    <div key={i} className={`alert alert-${m.type} alert-dismissible fade show`} style={{ whiteSpace: 'pre-line' }}>
                      {m.text}
                      <button type="button" className="btn-close" data-bs-dismiss="alert" />
                    </div>
                  ))}

                  <form onSubmit={handleSubmit} encType="multipart/form-data" className="mb-3">
                    <div className="mb-3">
                      <label htmlFor="alias_file" className="form-label">
                        <i className="fas fa-file-code me-2" />Select JSON File:
                      </label>
                      <input type="file" className="form-control" id="alias_file" name="alias_file" accept=".json" required />
                      <div className="form-text">Only JSON files accepted (maximum 5MB).</div>
                    </div>
                    <div className="d-grid gap-2">
                      <button type="submit" className="btn btn-success btn-lg">
                        <i className="fas fa-cloud-upload-alt me-2" />Upload Aliases
                      </button>
                    </div>
                  </form>

                  <div className="text-center">
                    <small className="text-muted"><i className="fas fa-shield-alt me-1" />File processed securely and deleted after processing</small>
                  </div>
                </div>

                <hr className="my-4" />

                <div className="text-muted small">
                  <h6><i className="fas fa-users me-2" />Community Feature</h6>
                  <p className="mb-0">This alias system is community-driven. Your contributions help make song searching easier for everyone.</p>
                </div>

              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  )
}
