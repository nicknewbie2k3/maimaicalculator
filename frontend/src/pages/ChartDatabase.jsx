import { useState, useRef } from 'react'
import { usePage, router } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'

function getCsrf() {
  const c = document.cookie.split(';').find(s => s.trim().startsWith('csrftoken='))
  return c ? decodeURIComponent(c.trim().slice('csrftoken='.length)) : ''
}

function calcSimilarity(a, b) {
  const s1 = a.toLowerCase(), s2 = b.toLowerCase()
  if (s1 === s2) return 100
  if (!s1.length || !s2.length) return 0
  const c1 = {}, c2 = {}
  for (const ch of s1) c1[ch] = (c1[ch] || 0) + 1
  for (const ch of s2) c2[ch] = (c2[ch] || 0) + 1
  let common = 0
  for (const ch in c1) if (c2[ch]) common += Math.min(c1[ch], c2[ch])
  const minLen = Math.min(s1.length, s2.length)
  let pos = 0
  for (let i = 0; i < minLen; i++) if (s1[i] === s2[i]) pos++
  const sub = (s1.includes(s2) || s2.includes(s1)) ? Math.min(s1.length, s2.length) * 0.3 : 0
  const total = Math.max(s1.length, s2.length)
  return Math.round((common / total) * 70 + (pos / minLen) * 20 + (sub / total) * 10)
}

function Autocomplete({ id, value, onChange, options, aliasMap, placeholder }) {
  const [items, setItems] = useState([])

  function build(val) {
    if (!val) { setItems([]); return }
    const v = val.toLowerCase()
    const matches = []; const seen = new Set()
    const add = (value, type, sim = 100) => { if (!seen.has(value)) { seen.add(value); matches.push({ value, type, sim }) } }

    if (aliasMap) {
      Object.keys(aliasMap).filter(a => a.toLowerCase().includes(v)).forEach(a => add(aliasMap[a], 'exact'))
      options.filter(n => n.toLowerCase().includes(v)).forEach(n => add(n, 'exact'))
      if (matches.length < 5) {
        Object.keys(aliasMap).forEach(a => { const t = aliasMap[a]; if (!seen.has(t)) { const s = calcSimilarity(v, a.toLowerCase()); if (s >= 30) { seen.add(t); matches.push({ value: t, type: 'fuzzy', sim: s }) } } })
        options.forEach(n => { if (!seen.has(n)) { const s = calcSimilarity(v, n.toLowerCase()); if (s >= 30) { seen.add(n); matches.push({ value: n, type: 'fuzzy', sim: s }) } } })
      }
    } else {
      options.filter(o => o.toLowerCase().includes(v)).forEach(o => add(o, 'exact'))
      if (matches.length < 5) options.forEach(o => { if (!seen.has(o)) { const s = calcSimilarity(v, o.toLowerCase()); if (s >= 30) { seen.add(o); matches.push({ value: o, type: 'fuzzy', sim: s }) } } })
    }
    matches.sort((a, b) => { if (a.type !== b.type) return a.type === 'exact' ? -1 : 1; return b.sim - a.sim })
    setItems(matches.slice(0, 10))
  }

  return (
    <div className="position-relative">
      <input id={id} type="text" className="form-control" value={value} placeholder={placeholder} autoComplete="off"
        onChange={e => { onChange(e.target.value); build(e.target.value) }} />
      {items.length > 0 && (
        <div className="dropdown-menu show" style={{ maxHeight: 200, overflowY: 'auto', width: '100%' }}>
          {items.map((m, i) => (
            <button key={i} type="button" className="dropdown-item" onClick={() => { onChange(m.value); setItems([]) }}>
              {m.value}{m.type === 'fuzzy' ? <small className="text-muted"> ({m.sim}% match)</small> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChartDatabase() {
  const { songs, pagination, filterTitles, filterVersions, filterArtists, filterCatcodes, aliasToTitleMap, currentFilters } = usePage().props

  const [filters, setFilters] = useState(currentFilters)
  const [modalSong, setModalSong] = useState(null)
  const [aliases, setAliases] = useState([])
  const [newAlias, setNewAlias] = useState('')
  const [aliasStatus, setAliasStatus] = useState({ msg: '', type: 'info', show: false })
  const statusTimer = useRef(null)

  function setF(key) { return val => setFilters(f => ({ ...f, [key]: val })) }

  function handleFilter(e) {
    e.preventDefault()
    const params = {}
    if (filters.title) params.title = filters.title
    if (filters.version) params.version = filters.version
    if (filters.artist) params.artist = filters.artist
    if (filters.catcode) params.catcode = filters.catcode
    if (filters.chartType) params.chart_type = filters.chartType
    if (filters.difficulty) params.difficulty = filters.difficulty
    router.get('/chart-database/', params, { preserveState: false })
  }

  function pageUrl(p) {
    const params = new URLSearchParams()
    if (currentFilters.title) params.set('title', currentFilters.title)
    if (currentFilters.version) params.set('version', currentFilters.version)
    if (currentFilters.artist) params.set('artist', currentFilters.artist)
    if (currentFilters.catcode) params.set('catcode', currentFilters.catcode)
    if (currentFilters.chartType) params.set('chart_type', currentFilters.chartType)
    if (currentFilters.difficulty) params.set('difficulty', currentFilters.difficulty)
    params.set('page', p)
    return `/chart-database/?${params.toString()}`
  }

  function showAliasMsg(msg, type, ms = 3000) {
    clearTimeout(statusTimer.current)
    setAliasStatus({ msg, type, show: true })
    if (ms > 0) statusTimer.current = setTimeout(() => setAliasStatus(s => ({ ...s, show: false })), ms)
  }

  async function openModal(song) {
    setModalSong(song); setNewAlias(''); setAliasStatus({ show: false })
    const res = await fetch(`/chart-database/get-aliases/${song.id}/`)
    const d = await res.json()
    setAliases(d.status === 'success' ? d.aliases : [])
    const modal = new window.bootstrap.Modal(document.getElementById('aliasModal'))
    modal.show()
  }

  async function addAlias() {
    if (!newAlias.trim()) { showAliasMsg('Enter an alias name', 'warning'); return }
    showAliasMsg('Adding...', 'info', 0)
    const res = await fetch('/chart-database/add-alias/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() }, body: JSON.stringify({ song_id: modalSong.id, alias: newAlias.trim() }) })
    const d = await res.json()
    if (d.status === 'success') { setAliases(d.aliases); setNewAlias(''); showAliasMsg(d.message, 'success') }
    else showAliasMsg(d.message, 'danger', 0)
  }

  async function removeAlias(alias) {
    showAliasMsg('Removing...', 'info', 0)
    const res = await fetch('/chart-database/remove-alias/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() }, body: JSON.stringify({ song_id: modalSong.id, alias }) })
    const d = await res.json()
    if (d.status === 'success') { setAliases(d.aliases); showAliasMsg(d.message, 'success') }
    else showAliasMsg(d.message, 'danger', 0)
  }

  return (
    <MainLayout>
      <div className="container-fluid my-4" style={{ maxWidth: '150vw' }}>
        <h1 className="text-center mb-4">Maimai Chart Database</h1>

        <form className="row g-2 mb-4" autoComplete="off" onSubmit={handleFilter}>
          <div className="col-md-2">
            <Autocomplete id="filter_title" value={filters.title} onChange={setF('title')} options={filterTitles} aliasMap={aliasToTitleMap} placeholder="Song Name or Alias" />
          </div>
          <div className="col-md-2">
            <Autocomplete id="filter_version" value={filters.version} onChange={setF('version')} options={filterVersions} placeholder="Version" />
          </div>
          <div className="col-md-2">
            <Autocomplete id="filter_artist" value={filters.artist} onChange={setF('artist')} options={filterArtists} placeholder="Artist" />
          </div>
          <div className="col-md-2">
            <select className="form-select" value={filters.catcode} onChange={e => setF('catcode')(e.target.value)}>
              <option value="">Catcode</option>
              {filterCatcodes.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="col-md-2">
            <select className="form-select" value={filters.chartType} onChange={e => setF('chartType')(e.target.value)}>
              <option value="">Chart Type</option>
              <option value="STD">STD</option>
              <option value="DX">DX</option>
            </select>
          </div>
          <div className="col-md-2">
            <select className="form-select" value={filters.difficulty} onChange={e => setF('difficulty')(e.target.value)}>
              <option value="">Difficulty</option>
              {['Basic','Advanced','Expert','Master','Re:Master'].map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="col-md-12 mt-2">
            <button type="submit" className="btn btn-primary">Filter</button>
            <a href="/chart-database/" className="btn btn-secondary ms-2">Reset</a>
            <a href="/chart-database/download/" className="btn btn-success ms-3"><i className="fas fa-download me-1" />Download Full Database (JSON)</a>
            <a href="/chart-database/alias-upload/" className="btn btn-info ms-3"><i className="fas fa-file-upload me-1" />Add Alias via File</a>
          </div>
        </form>

        <div className="mb-2 d-flex justify-content-between align-items-center">
          <div><strong>{pagination.totalCount}</strong> result{pagination.totalCount !== 1 ? 's' : ''} found.</div>
          <small className="text-muted"><i className="fas fa-info-circle" /> Search by song name or aliases</small>
        </div>

        <div className="table-responsive" style={{ overflowX: 'auto' }}>
          <table className="table table-striped table-bordered align-middle w-100">
            <thead className="table-dark">
              <tr>
                <th>#</th><th>Title</th><th>Title Kana</th><th>Artist</th><th>Catcode</th>
                <th>Image</th><th>Release</th><th>Basic</th><th>Adv</th><th>Exp</th><th>Mas</th><th>Re:Mas</th>
                <th>Sort</th><th>Version</th><th>Type</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {songs.length === 0
                ? <tr><td colSpan={16} className="text-center">No songs found.</td></tr>
                : songs.map((s, i) => (
                  <tr key={s.id}>
                    <td>{pagination.startIndex + i}</td>
                    <td>{s.title}</td><td>{s.title_kana}</td><td>{s.artist}</td><td>{s.catcode}</td>
                    <td>
                      {s.image_url
                        ? <a href={s.image_url} target="_blank" rel="noreferrer"><img src={s.image_url} alt="" loading="lazy" style={{ height: 40, maxWidth: 60, borderRadius: 4 }} /></a>
                        : '-'}
                    </td>
                    <td>{s.release}</td><td>{s.lev_bas}</td><td>{s.lev_adv}</td><td>{s.lev_exp}</td><td>{s.lev_mas}</td><td>{s.lev_remas}</td>
                    <td>{s.sort}</td><td>{s.version}</td><td>{s.chart_type}</td>
                    <td>
                      <button type="button" className="btn btn-sm btn-primary" onClick={() => openModal(s)}>
                        <i className="fas fa-tag" /> Aliases
                      </button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        <nav>
          <ul className="pagination justify-content-center">
            <li className={`page-item${!pagination.hasPrevious ? ' disabled' : ''}`}>
              <a className="page-link" href={pagination.hasPrevious ? pageUrl(1) : '#'}>&laquo; First</a>
            </li>
            <li className={`page-item${!pagination.hasPrevious ? ' disabled' : ''}`}>
              <a className="page-link" href={pagination.hasPrevious ? pageUrl(pagination.previousPage) : '#'}>&lsaquo; Prev</a>
            </li>
            <li className="page-item disabled">
              <span className="page-link">Page {pagination.page} of {pagination.numPages}</span>
            </li>
            <li className={`page-item${!pagination.hasNext ? ' disabled' : ''}`}>
              <a className="page-link" href={pagination.hasNext ? pageUrl(pagination.nextPage) : '#'}>Next &rsaquo;</a>
            </li>
            <li className={`page-item${!pagination.hasNext ? ' disabled' : ''}`}>
              <a className="page-link" href={pagination.hasNext ? pageUrl(pagination.numPages) : '#'}>Last &raquo;</a>
            </li>
          </ul>
        </nav>

        {/* Alias Modal */}
        <div className="modal fade" id="aliasModal" tabIndex="-1">
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Manage Aliases</h5>
                <button type="button" className="btn-close" data-bs-dismiss="modal" />
              </div>
              <div className="modal-body">
                <div className="mb-3"><strong>Song:</strong> {modalSong?.title}</div>
                <div className="mb-3">
                  <label className="form-label">Add New Alias:</label>
                  <div className="input-group">
                    <input type="text" className="form-control" value={newAlias} placeholder="Enter alias name"
                      onChange={e => setNewAlias(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && addAlias()} />
                    <button className="btn btn-success" type="button" onClick={addAlias}>Add</button>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label">Current Aliases:</label>
                  <div className="border p-2 rounded" style={{ minHeight: 100, maxHeight: 200, overflowY: 'auto' }}>
                    {aliases.length === 0
                      ? <em className="text-muted">No aliases added yet.</em>
                      : aliases.map((a, i) => (
                        <div key={i} className="d-flex justify-content-between align-items-center mb-2 p-2 bg-light rounded">
                          <span>{a}</span>
                          <button className="btn btn-sm btn-danger" onClick={() => removeAlias(a)}><i className="fas fa-times" /></button>
                        </div>
                      ))}
                  </div>
                </div>
                {aliasStatus.show && <div className={`alert alert-${aliasStatus.type}`}>{aliasStatus.msg}</div>}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  )
}
