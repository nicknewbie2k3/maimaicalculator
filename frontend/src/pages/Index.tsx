import { useState, useEffect, useRef, useCallback } from 'react'
import { usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'

const B50_KEY = 'maimai_b50_data'
const FULL_KEY = 'maimai_full_scores_data'

interface Song {
  song_name: string
  difficulty_type: string
  rank: string
  achievement: number | string
  chart_difficulty: number | string
  calculated_rating: number
  version?: string
}

interface B50Data {
  old_songs: Song[]
  new_songs: Song[]
}

interface SongInfo {
  version?: string
  chart_type?: string
  image_url?: string
}

type SongsDict = Record<string, SongInfo>

interface DropdownItem {
  value: string
  type: 'exact' | 'fuzzy'
  sim: number
}

interface StatusState {
  msg: string
  type: string
  show: boolean
}

interface IndexPageProps {
  allSongNames: string[]
  maimaiSongsDict: SongsDict
  aliasToTitleMap: Record<string, string>
}

function getCsrf(): string {
  const c = document.cookie.split(';').find(s => s.trim().startsWith('csrftoken='))
  return c ? decodeURIComponent(c.trim().slice('csrftoken='.length)) : ''
}

function calcSimilarity(a: string, b: string): number {
  const s1 = a.toLowerCase(), s2 = b.toLowerCase()
  if (s1 === s2) return 100
  if (!s1.length || !s2.length) return 0
  const c1: Record<string, number> = {}, c2: Record<string, number> = {}
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

function isNewChart(song: Pick<Song, 'version' | 'song_name'>, dict: SongsDict): boolean {
  const v = song.version || (dict[song.song_name] || {}).version || ''
  return v === 'PRiSM PLUS' || v === 'CiRCLE'
}

function diffClass(d: string): string {
  return ({ basic: 'diff-basic', advanced: 'diff-advanced', expert: 'diff-expert', master: 'diff-master', 're:master': 'diff-remas', remaster: 'diff-remas' } as Record<string, string>)[d.toLowerCase()] || ''
}

function recategorize(data: B50Data, dict: SongsDict): B50Data {
  const out: B50Data = { old_songs: [], new_songs: [] }
  const add = (song: Song, arr: Song[]) => {
    const idx = arr.findIndex(s => s.song_name === song.song_name && s.difficulty_type === song.difficulty_type)
    if (idx !== -1) { if (song.achievement > arr[idx].achievement) arr[idx] = song }
    else arr.push(song)
  }
  ;[...data.old_songs, ...data.new_songs].forEach(s => {
    if (!s.version) s.version = (dict[s.song_name] || {}).version || ''
    const isNew = isNewChart(s, dict)
    add(s, isNew ? out.new_songs : out.old_songs)
  })
  out.old_songs.sort((a, b) => b.calculated_rating - a.calculated_rating)
  out.new_songs.sort((a, b) => b.calculated_rating - a.calculated_rating)
  out.old_songs = out.old_songs.slice(0, 35)
  out.new_songs = out.new_songs.slice(0, 15)
  return out
}

interface SongCellProps {
  song: Song | null
  songDict: SongsDict
  divider?: boolean
}

function SongCell({ song, songDict, divider }: SongCellProps) {
  if (!song) return <td className={`song-grid-cell${divider ? ' border-divider-row' : ''}`}><div className="song-grid-cell-inner" /></td>
  const info: SongInfo = songDict[song.song_name] ?? {}
  const titleClass = info.chart_type === 'STD' ? 'song-title-std' : info.chart_type === 'DX' ? 'song-title-dx' : ''
  const chartClass = isNewChart(song, songDict) ? 'new-chart' : 'old-chart'
  return (
    <td className={`song-grid-cell ${diffClass(song.difficulty_type)} ${chartClass}${divider ? ' border-divider-row' : ''}`}>
      <div className="song-grid-cell-inner">
        <span className={`song-title-oneline ${titleClass}`}>{song.song_name}</span>
        {info.image_url && (
          <a href={info.image_url} target="_blank" rel="noreferrer" className="song-cell-image">
            <img src={info.image_url} alt="" loading="lazy" decoding="async" />
          </a>
        )}
        <div className="song-cell-bottom-left">
          <span className="song-rank-bold">{song.rank}</span><br />
          <span className="song-achievement">{parseFloat(String(song.achievement)).toFixed(4)}%</span><br />
          <span className="song-chart-diff-bold">{parseFloat(String(song.chart_difficulty)).toFixed(1)}</span>
        </div>
        <div className="song-cell-bottom-right">{song.calculated_rating}</div>
      </div>
    </td>
  )
}

interface SongTableProps {
  label: string
  songs: Song[]
  idPrefix: string
}

function SongTable({ label, songs, idPrefix }: SongTableProps) {
  return (
    <>
      <h2 id={`${idPrefix}Header`}>{label} ({songs.length})</h2>
      <div className="table-responsive mb-4">
        <table className="table table-striped table-bordered align-middle">
          <thead className="table-dark">
            <tr><th>#</th><th>Song Name</th><th>Difficulty</th><th>Rank</th><th>Achievement</th><th>Chart Difficulty</th><th>Calculated Rating</th></tr>
          </thead>
          <tbody>
            {songs.length === 0
              ? <tr><td colSpan={7} className="text-center">No songs found.</td></tr>
              : songs.map((s, i) => (
                <tr key={i} className={isNewChart(s, {}) ? 'new-chart-row' : 'old-chart-row'}>
                  <td>{i + 1}</td><td>{s.song_name}</td><td>{s.difficulty_type}</td><td>{s.rank}</td>
                  <td>{parseFloat(String(s.achievement)).toFixed(4)}%</td>
                  <td>{parseFloat(String(s.chart_difficulty)).toFixed(1)}</td>
                  <td>{s.calculated_rating}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export default function Index() {
  const { allSongNames, maimaiSongsDict, aliasToTitleMap } = usePage().props as unknown as IndexPageProps

  const [b50, setB50State] = useState<B50Data>({ old_songs: [], new_songs: [] })
  const [fullData, setFullDataState] = useState<B50Data | null>(null)
  const [status, setStatus] = useState<StatusState>({ msg: '', type: 'info', show: false })
  const [songInput, setSongInput] = useState('')
  const [difficulty, setDifficulty] = useState('Basic')
  const [achievement, setAchievement] = useState('')
  const [dropdown, setDropdown] = useState<DropdownItem[]>([])

  const b50FileRef = useRef<HTMLInputElement>(null)
  const cacheFileRef = useRef<HTMLInputElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const statusTimerRef = useRef<number>(0)

  const showStatus = useCallback((msg: string, type: string, ms = 4000) => {
    clearTimeout(statusTimerRef.current)
    setStatus({ msg, type, show: true })
    if (ms > 0) statusTimerRef.current = window.setTimeout(() => setStatus(s => ({ ...s, show: false })), ms)
  }, [])

  const readB50 = (): B50Data => {
    try { return (JSON.parse(localStorage.getItem(B50_KEY) || 'null') as B50Data | null) ?? { old_songs: [], new_songs: [] } }
    catch { return { old_songs: [], new_songs: [] } }
  }
  const writeB50 = (d: B50Data) => { localStorage.setItem(B50_KEY, JSON.stringify(d)); setB50State(d) }
  const readFull = (): B50Data | null => { try { return JSON.parse(localStorage.getItem(FULL_KEY) || 'null') as B50Data | null } catch { return null } }
  const writeFull = (d: B50Data) => { try { localStorage.setItem(FULL_KEY, JSON.stringify(d)); setFullDataState(d) } catch { /* storage quota exceeded */ } }

  useEffect(() => {
    const stored = readB50()
    setB50State(recategorize(stored, maimaiSongsDict))
    setFullDataState(readFull())
  }, [])

  function buildDropdown(val: string) {
    if (!val) { setDropdown([]); return }
    const v = val.toLowerCase()
    const matches: DropdownItem[] = []
    const seen = new Set<string>()

    const addMatch = (value: string, type: 'exact' | 'fuzzy') => {
      if (!seen.has(value)) { seen.add(value); matches.push({ value, type, sim: type === 'exact' ? 100 : 0 }) }
    }

    Object.keys(aliasToTitleMap).filter(a => a.toLowerCase().includes(v)).forEach(a => addMatch(aliasToTitleMap[a], 'exact'))
    allSongNames.filter(n => n.toLowerCase().includes(v)).forEach(n => addMatch(n, 'exact'))

    if (matches.length < 5) {
      Object.keys(aliasToTitleMap).forEach(a => {
        const t = aliasToTitleMap[a]
        if (!seen.has(t)) { const s = calcSimilarity(v, a.toLowerCase()); if (s >= 30) { seen.add(t); matches.push({ value: t, type: 'fuzzy', sim: s }) } }
      })
      allSongNames.forEach(n => {
        if (!seen.has(n)) { const s = calcSimilarity(v, n.toLowerCase()); if (s >= 30) { seen.add(n); matches.push({ value: n, type: 'fuzzy', sim: s }) } }
      })
    }

    matches.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'exact' ? -1 : 1
      return b.sim - a.sim
    })
    setDropdown(matches.slice(0, 10))
  }

  async function addSong(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData()
    fd.append('song_name', songInput)
    fd.append('difficulty_type', difficulty)
    fd.append('achievement', achievement)
    fd.append('csrfmiddlewaretoken', getCsrf())
    try {
      const res = await fetch('/', { method: 'POST', body: fd })
      const data = await res.json() as { status: string; song_data: Song }
      if (data.status !== 'success') return
      const song = data.song_data
      if (!song.version) song.version = (maimaiSongsDict[song.song_name] || {}).version || ''
      const raw = readB50()
      const isNew = isNewChart(song, maimaiSongsDict)
      const arr = isNew ? raw.new_songs : raw.old_songs
      const max = isNew ? 15 : 35
      const idx = arr.findIndex(s => s.song_name === song.song_name && s.difficulty_type === song.difficulty_type)
      if (idx !== -1) { if (song.achievement > arr[idx].achievement) arr.splice(idx, 1); else return }
      arr.push(song)
      arr.sort((a, b) => b.calculated_rating - a.calculated_rating)
      if (arr.length > max) arr.splice(max)
      const newB50 = recategorize(raw, maimaiSongsDict)
      writeB50(newB50)
      const full = readFull() ?? { old_songs: [], new_songs: [] }
      const fa = isNew ? full.new_songs : full.old_songs
      const fi = fa.findIndex(s => s.song_name === song.song_name && s.difficulty_type === song.difficulty_type)
      if (fi !== -1) { if (song.achievement > fa[fi].achievement) fa[fi] = song }
      else fa.push(song)
      full.old_songs.sort((a, b) => b.calculated_rating - a.calculated_rating)
      full.new_songs.sort((a, b) => b.calculated_rating - a.calculated_rating)
      writeFull(full)
      setSongInput(''); setAchievement('')
    } catch (err) { console.error(err) }
  }

  async function handleB50File(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    const fd = new FormData(); fd.append('b50_file', file); fd.append('csrfmiddlewaretoken', getCsrf())
    showStatus('Uploading B50 data...', 'info', 0)
    try {
      const res = await fetch('/load-b50/', { method: 'POST', body: fd })
      const data = await res.json() as { status: string; message: string; data: B50Data }
      if (data.status === 'success') {
        writeFull(data.data)
        const rec = recategorize(data.data, maimaiSongsDict)
        writeB50(rec)
        showStatus(`${data.message} Imported ${rec.old_songs.length} old and ${rec.new_songs.length} new songs.`, 'success')
      } else showStatus('Error: ' + data.message, 'danger')
    } catch (err) { showStatus('Network error: ' + (err as Error).message, 'danger') }
    e.target.value = ''
  }

  async function handleCacheFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    const fd = new FormData(); fd.append('cache_file', file); fd.append('csrfmiddlewaretoken', getCsrf())
    showStatus('Converting cache file...', 'info', 0)
    try {
      const res = await fetch('/convert-cache-to-all-scores/', { method: 'POST', body: fd })
      const data = await res.json() as { status: string; message: string; b35_15_data?: B50Data; data?: B50Data }
      if (data.status === 'success') {
        if (data.b35_15_data) { writeB50(data.b35_15_data) }
        if (data.data) writeFull(data.data)
        showStatus(data.message, 'success', 5000)
      } else showStatus('Error: ' + data.message, 'danger', 7000)
    } catch (err) { showStatus('Network error: ' + (err as Error).message, 'danger', 7000) }
    e.target.value = ''
  }

  async function saveToFile() {
    if (!b50.old_songs.length && !b50.new_songs.length) { showStatus('No B50 data to export.', 'warning'); return }
    showStatus('Generating export...', 'info', 0)
    try {
      const res = await fetch('/save-b50/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() }, body: JSON.stringify(b50) })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const ct = res.headers.get('content-type')
      if (ct && ct.includes('application/json')) { const d = await res.json() as { message: string }; throw new Error(d.message) }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = 'maimai_b50_data.json'
      document.body.appendChild(a); a.click(); URL.revokeObjectURL(url); document.body.removeChild(a)
      showStatus('B50 data exported!', 'success')
    } catch (err) { showStatus('Error: ' + (err as Error).message, 'danger', 5000) }
  }

  function clearData() {
    writeB50({ old_songs: [], new_songs: [] })
    localStorage.removeItem(FULL_KEY); setFullDataState(null)
    showStatus('B50 data cleared.', 'success')
  }

  async function printB50() {
    if (!gridRef.current || !window.html2canvas) return
    showStatus('Generating image...', 'info', 0)
    try {
      const canvas = await window.html2canvas(gridRef.current, { backgroundColor: '#fff', scale: 2, useCORS: true })
      const a = document.createElement('a'); a.download = 'maimai_b50_grid.png'; a.href = canvas.toDataURL('image/png')
      a.click()
      showStatus('Image generated!', 'success')
    } catch (err) { showStatus('Error: ' + (err as Error).message, 'danger') }
  }

  const display = b50
  const oldRating = display.old_songs.reduce((s, x) => s + x.calculated_rating, 0)
  const newRating = display.new_songs.reduce((s, x) => s + x.calculated_rating, 0)
  const totalRating = oldRating + newRating
  const count = display.old_songs.length + display.new_songs.length
  const avgRating = count > 0 ? Math.round(totalRating / count) : 0

  const oldPad: (Song | null)[] = [...display.old_songs]; while (oldPad.length < 35) oldPad.push(null)
  const newPad: (Song | null)[] = [...display.new_songs]; while (newPad.length < 15) newPad.push(null)

  const tableOld = fullData?.old_songs?.length ? fullData.old_songs : display.old_songs
  const tableNew = fullData?.new_songs?.length ? fullData.new_songs : display.new_songs

  return (
    <MainLayout>
      <div className="container-fluid my-4">
        <h1 className="text-center mb-4">AstroDX Manual Rating Converter</h1>
        <h2 className="text-center mb-4">Total Rating: {totalRating}</h2>
        <h4 className="text-center mb-3">
          Old Chart Total Rating: {oldRating} &nbsp;|&nbsp;
          New Chart Total Rating: {newRating} &nbsp;|&nbsp;
          Total Average Rating: {avgRating}
        </h4>

        <div className="text-center mb-4">
          <button className="btn btn-success me-2" onClick={saveToFile}><i className="fas fa-download me-1" />Save B50 Data</button>
          <button className="btn btn-primary me-2" onClick={() => b50FileRef.current?.click()}><i className="fas fa-upload me-1" />Load B50 Data</button>
          <button className="btn btn-warning me-2" onClick={() => cacheFileRef.current?.click()}><i className="fas fa-exchange-alt me-1" />Convert Cache to B50</button>
          <button className="btn btn-info me-2" onClick={printB50}><i className="fas fa-camera me-1" />Print B50</button>
          <button className="btn btn-danger" onClick={clearData}><i className="fas fa-trash me-1" />Clear B50 Data</button>
          <input ref={b50FileRef} type="file" accept=".json" style={{ display: 'none' }} onChange={handleB50File} />
          <input ref={cacheFileRef} type="file" accept="*" style={{ display: 'none' }} onChange={handleCacheFile} />
          {status.show && (
            <div className={`alert alert-${status.type} mt-3`} style={{ whiteSpace: 'pre-line' }}>{status.msg}</div>
          )}
          <div className="text-center mt-2">
            <small className="text-muted">
              <span style={{ borderLeft: '4px solid #007bff', paddingLeft: 8, marginRight: 15 }}>Old Charts (PRE-PRiSM)</span>
              <span style={{ borderLeft: '4px solid #28a745', paddingLeft: 8 }}>New Charts (PRiSM PLUS / CiRCLE)</span>
            </small>
          </div>
        </div>

        <form className="row g-3 align-items-center mb-4 position-relative" autoComplete="off" onSubmit={addSong}>
          <div className="col-auto"><label className="col-form-label">Song Name:</label></div>
          <div className="col-auto position-relative" style={{ minWidth: 250 }}>
            <input
              type="text" className="form-control" value={songInput} required
              onChange={e => { setSongInput(e.target.value); buildDropdown(e.target.value) }}
              placeholder="Song Name or Alias"
            />
            {dropdown.length > 0 && (
              <div className="dropdown-menu show" style={{ maxHeight: 200, overflowY: 'auto', width: '100%' }}>
                {dropdown.map((m, i) => (
                  <button key={i} type="button" className="dropdown-item" onClick={() => { setSongInput(m.value); setDropdown([]) }}>
                    {m.value}{m.type === 'fuzzy' ? <small className="text-muted"> ({m.sim}% match)</small> : null}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="col-auto"><label className="col-form-label">Difficulty:</label></div>
          <div className="col-auto">
            <select className="form-select" value={difficulty} onChange={e => setDifficulty(e.target.value)}>
              {['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master'].map(d => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="col-auto"><label className="col-form-label">Achievement:</label></div>
          <div className="col-auto">
            <input type="number" className="form-control" step="0.0001" min="0" max="101" value={achievement} required onChange={e => setAchievement(e.target.value)} />
          </div>
          <div className="col-auto"><button type="submit" className="btn btn-primary">Add</button></div>
        </form>

        <div className="mb-3">
          <small className="text-muted">
            <i className="fas fa-info-circle" /> If you want to add an alias to a song, consider clicking Chart Database!
          </small>
        </div>

        <h2 className="mt-5">All Songs (Old + New) Grid View</h2>
        <div ref={gridRef} className="table-responsive mb-4 wide-grid-container">
          <table className="table table-bordered align-middle wide-grid-table" style={{ tableLayout: 'fixed' }}>
            <tbody>
              {Array.from({ length: 10 }, (_, row) => (
                <tr key={row}>
                  {Array.from({ length: 5 }, (_, col) => {
                    const song = row < 7 ? oldPad[row * 5 + col] : newPad[(row - 7) * 5 + col]
                    return <SongCell key={col} song={song ?? null} songDict={maimaiSongsDict} divider={row === 7} />
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <SongTable label="Old Songs" songs={tableOld} idPrefix="old" />
        <SongTable label="New Songs" songs={tableNew} idPrefix="new" />
      </div>
    </MainLayout>
  )
}
