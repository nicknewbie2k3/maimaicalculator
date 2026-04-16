import html2canvas from 'html2canvas-pro'
import { useState, useEffect, useRef, useCallback } from 'react'
import { usePage } from '@inertiajs/react'
import MainLayout from '../layouts/MainLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import {
  Download,
  Upload,
  ArrowLeftRight,
  Camera,
  Trash2,
  Info,
} from 'lucide-react'

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
      <h2 className="text-xl font-semibold mt-8 mb-3" id={`${idPrefix}Header`}>
        {label} ({songs.length})
      </h2>
      <div className="mb-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Song Name</TableHead>
              <TableHead>Difficulty</TableHead>
              <TableHead>Rank</TableHead>
              <TableHead>Achievement</TableHead>
              <TableHead>Chart Difficulty</TableHead>
              <TableHead>Calculated Rating</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {songs.length === 0
              ? <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground">No songs found.</TableCell></TableRow>
              : songs.map((s, i) => (
                <TableRow key={i} className={isNewChart(s, {}) ? 'new-chart-row' : 'old-chart-row'}>
                  <TableCell>{i + 1}</TableCell>
                  <TableCell>{s.song_name}</TableCell>
                  <TableCell>{s.difficulty_type}</TableCell>
                  <TableCell>{s.rank}</TableCell>
                  <TableCell>{parseFloat(String(s.achievement)).toFixed(4)}%</TableCell>
                  <TableCell>{parseFloat(String(s.chart_difficulty)).toFixed(1)}</TableCell>
                  <TableCell>{s.calculated_rating}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>
    </>
  )
}

function statusAlertClass(type: string): string {
  if (type === 'success') return 'border-green-500/50 bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-400'
  if (type === 'warning') return 'border-yellow-500/40 bg-yellow-50 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400'
  return ''
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
    matches.sort((a, b) => { if (a.type !== b.type) return a.type === 'exact' ? -1 : 1; return b.sim - a.sim })
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
        if (data.b35_15_data) writeB50(data.b35_15_data)
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
    if (!gridRef.current) return
    showStatus('Generating image...', 'info', 0)
    try {
      const canvas = await html2canvas(gridRef.current, { backgroundColor: '#fff', scale: 2, useCORS: true })
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
      <div className="w-full px-4 py-6">
        <h1 className="text-2xl font-bold text-center mb-2">AstroDX Manual Rating Converter</h1>
        <h2 className="text-xl font-semibold text-center mb-2">Total Rating: {totalRating}</h2>
        <p className="text-center text-sm text-muted-foreground mb-6">
          Old Chart Total Rating: {oldRating} &nbsp;|&nbsp;
          New Chart Total Rating: {newRating} &nbsp;|&nbsp;
          Total Average Rating: {avgRating}
        </p>

        <div className="flex flex-wrap justify-center gap-2 mb-4">
          <Button onClick={saveToFile}>
            <Download data-icon="inline-start" />
            Save B50 Data
          </Button>
          <Button variant="outline" onClick={() => b50FileRef.current?.click()}>
            <Upload data-icon="inline-start" />
            Load B50 Data
          </Button>
          <Button variant="outline" onClick={() => cacheFileRef.current?.click()}>
            <ArrowLeftRight data-icon="inline-start" />
            Convert Cache to B50
          </Button>
          <Button variant="secondary" onClick={printB50}>
            <Camera data-icon="inline-start" />
            Print B50
          </Button>
          <Button variant="destructive" onClick={clearData}>
            <Trash2 data-icon="inline-start" />
            Clear B50 Data
          </Button>
          <input ref={b50FileRef} type="file" accept=".json" className="hidden" onChange={handleB50File} />
          <input ref={cacheFileRef} type="file" accept="*" className="hidden" onChange={handleCacheFile} />
        </div>

        {status.show && (
          <div className="max-w-2xl mx-auto mb-4">
            <Alert
              variant={status.type === 'danger' ? 'destructive' : 'default'}
              className={statusAlertClass(status.type)}
              style={{ whiteSpace: 'pre-line' }}
            >
              <AlertDescription>{status.msg}</AlertDescription>
            </Alert>
          </div>
        )}

        <div className="flex justify-center gap-6 mb-6 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <span className="inline-block w-1 h-4 rounded" style={{ background: '#007bff' }} />
            Old Charts (PRE-PRiSM)
          </span>
          <span className="flex items-center gap-2">
            <span className="inline-block w-1 h-4 rounded" style={{ background: '#28a745' }} />
            New Charts (PRiSM PLUS / CiRCLE)
          </span>
        </div>

        <form className="flex flex-wrap gap-3 items-center mb-6 relative" autoComplete="off" onSubmit={addSong}>
          <div className="flex items-center gap-2">
            <Label htmlFor="song-input">Song Name:</Label>
          </div>
          <div className="relative" style={{ minWidth: 250 }}>
            <Input
              id="song-input"
              type="text"
              value={songInput}
              required
              onChange={e => { setSongInput(e.target.value); buildDropdown(e.target.value) }}
              placeholder="Song Name or Alias"
            />
            {dropdown.length > 0 && (
              <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border bg-popover text-popover-foreground shadow-md">
                {dropdown.map((m, i) => (
                  <button
                    key={i}
                    type="button"
                    className="w-full text-left px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => { setSongInput(m.value); setDropdown([]) }}
                  >
                    {m.value}
                    {m.type === 'fuzzy' && <span className="text-muted-foreground text-xs ml-1">({m.sim}% match)</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <Label>Difficulty:</Label>
          <Select value={difficulty} onValueChange={setDifficulty}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master'].map(d => (
                  <SelectItem key={d} value={d}>{d}</SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <Label htmlFor="achievement-input">Achievement:</Label>
          <Input
            id="achievement-input"
            type="number"
            className="w-32"
            step="0.0001"
            min="0"
            max="101"
            value={achievement}
            required
            onChange={e => setAchievement(e.target.value)}
          />
          <Button type="submit">Add</Button>
        </form>

        <p className="text-sm text-muted-foreground mb-6 flex items-center gap-1">
          <Info className="size-4" />
          If you want to add an alias to a song, consider clicking Chart Database!
        </p>

        <h2 className="text-xl font-semibold mt-4 mb-3">All Songs (Old + New) Grid View</h2>
        <div ref={gridRef} className="wide-grid-container mb-6" style={{ background: '#fff', color: '#111' }}>
          <table className="wide-grid-table" style={{ tableLayout: 'fixed', borderCollapse: 'collapse' }}>
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
