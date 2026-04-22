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
const USERNAME_KEY = 'maimai_username'

interface Song {
  song_name: string
  difficulty_type: string
  rank: string
  achievement: number | string
  chart_difficulty: number | string
  calculated_rating: number
  version?: string
  clear_type?: string | null
}
const CLEAR_ICONS: Record<string, string> = {
  'FC': '/static/image/music_icon_fc.png',
  'FC+': '/static/image/music_icon_fcp.png',
  'AP': '/static/image/music_icon_ap.png',
  'AP+': '/static/image/music_icon_app.png',
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

function rankClass(rank: string | number | null | undefined): string {
  if (rank === null || rank === undefined || rank === '') return 'rank-default'
  const r = String(rank).toUpperCase().trim()
  if (r === '3S+' || r === '3S') return 'rank-3s'
  if (r === '3A' || r === '2A' || r === 'A') return 'rank-pink'
  // treat 2S/2S+ and S/S+ as the default gold/yellow ranks per request
  if (r === '2S+' || r === '2S' || r === 'S+' || r === 'S') return 'rank-gold'
  return 'rank-default'
}

// Return a solid fallback text color for a given rank string.
function rankSolidColor(rank: string | number | null | undefined): string {
  if (rank === null || rank === undefined || String(rank).trim() === '') return '#8ed1ff'
  const r = String(rank).toUpperCase().trim()
  if (r === '3S+' || r === '3S') return '#ff8a2b' // orange-yellow for 3S variants
  if (r === '3A' || r === '2A' || r === 'A') return '#ff4da6' // pink for A tiers
  // treat 2S/2S+ and S/S+ as the default gold/yellow ranks per request
  if (r === '2S+' || r === '2S' || r === 'S+' || r === 'S') return '#fde68a'
  return '#8ed1ff' // fallback light-blue
}

// Map rank text to grade image filenames (stored in Django static image folder)
// Rank icon mapping (use the same static paths approach as `CLEAR_ICONS`)
const RANK_ICONS: Record<string, string> = {
  'D': '/static/image/grade_d.png',
  'C': '/static/image/grade_c.png',
  'B': '/static/image/grade_b.png',
  '2B': '/static/image/grade_bb.png',
  '3B': '/static/image/grade_bbb.png',
  'A': '/static/image/grade_a.png',
  '2A': '/static/image/grade_aa.png',
  '3A': '/static/image/grade_aaa.png',
  'S': '/static/image/grade_s.png',
  'S+': '/static/image/grade_s_plus.png',
  '2S': '/static/image/grade_ss.png',
  '2S+': '/static/image/grade_ss_plus.png',
  '3S': '/static/image/grade_sss.png',
  '3S+': '/static/image/grade_sss_plus.png',
}

function rankImageFile(rank: string | number | null | undefined): string | null {
  if (rank === null || rank === undefined) return null
  const r = String(rank).toUpperCase().trim()
  return RANK_ICONS[r] || null
}

function renderRankElement(rank: string | number | null | undefined) {
  const src = rankImageFile(rank)
  const cls = `song-card-rank ${rankClass(rank)}`
  if (src) {
    return (
      <span className={cls} aria-label={String(rank)} title={String(rank)}>
        <img src={src} alt={String(rank)} className="rank-image" />
      </span>
    )
  }
  return <span className={cls}>{rank}</span>
}

interface SongCellProps {
  song: Song | null
  songDict: SongsDict
}

function SongCell({ song, songDict }: SongCellProps) {
  if (!song) return <div className="song-card song-card-empty" />
  const info: SongInfo = songDict[song.song_name] ?? {}
  const chartTag = info.chart_type === 'STD' ? 'STD' : info.chart_type === 'DX' ? 'DX' : ''
  const chartTagClass = info.chart_type === 'STD' ? 'song-tag-std' : info.chart_type === 'DX' ? 'song-tag-dx' : ''
  const displayTitle = song.song_name.replace(/\s*\[(?:DX|STD)\]\s*$/i, '')
  const clearIconSrc = song.clear_type ? (CLEAR_ICONS[song.clear_type] || null) : null
  return (
    <div className={`song-card ${diffClass(song.difficulty_type)}`}>
      
      <div className="song-card-art" style={info.image_url ? { backgroundImage: `url(${info.image_url})` } : undefined}>
        {chartTag && <span className={`song-tag ${chartTagClass}`}>{chartTag}</span>}
        {clearIconSrc && (
          <img src={clearIconSrc} className="song-clear-badge" alt={String(song.clear_type)} />
        )}
      </div>
      <div className="song-card-info">
        <div className="song-card-title" title={song.song_name}>{displayTitle}</div>
        <div className="song-card-meta">
          {renderRankElement(song.rank)}
          <span className="song-card-ach-inline">{parseFloat(String(song.achievement)).toFixed(4)}%</span>
        </div>
        {/* Right side of info strip: stacked rating + chart constant */}
        <div className="song-card-const-group">
          <div className="song-card-rating">
            <span className="song-card-rating-value">{song.calculated_rating}</span>
            <span className="song-card-diff">{parseFloat(String(song.chart_difficulty)).toFixed(1)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

interface SongTableProps {
  label: string
  songs: Song[]
  idPrefix: string
}

function SongTable({ songs, idPrefix }: SongTableProps) {
  return (
    <Table id={`${idPrefix}Header`} className="table-fixed">
      <TableHeader>
        <TableRow>
          <TableHead className="w-8">#</TableHead>
          <TableHead className="w-12 text-center">Clear</TableHead>
          <TableHead className="w-[320px]">Song Name</TableHead>
          <TableHead className="w-28">Difficulty</TableHead>
          <TableHead className="w-20">Rank</TableHead>
          <TableHead className="w-36">Achievement</TableHead>
          <TableHead className="w-28 text-center">Chart Difficulty</TableHead>
          <TableHead className="w-36 text-center">Calculated Rating</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {songs.length === 0
          ? <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground py-8">No songs added yet.</TableCell></TableRow>
          : songs.map((s, i) => (
            <TableRow key={i} className={isNewChart(s, {}) ? 'new-chart-row' : 'old-chart-row'}>
              <TableCell className="text-muted-foreground text-xs w-8">{i + 1}</TableCell>
              <TableCell className="w-12 text-center">
                {s.clear_type && CLEAR_ICONS[s.clear_type] ? (
                  <img src={CLEAR_ICONS[s.clear_type]} alt={String(s.clear_type)} className="table-clear-icon" />
                ) : null}
              </TableCell>
              <TableCell className="font-medium max-w-[320px] truncate">{s.song_name}</TableCell>
              <TableCell className="w-28">{s.difficulty_type}</TableCell>
              <TableCell className="w-20">{renderRankElement(s.rank)}</TableCell>
              <TableCell className="w-36">{parseFloat(String(s.achievement)).toFixed(4)}%</TableCell>
              <TableCell className="w-28 text-center">{parseFloat(String(s.chart_difficulty)).toFixed(1)}</TableCell>
              <TableCell className="font-semibold text-primary w-36 text-center">{s.calculated_rating}</TableCell>
            </TableRow>
          ))}
      </TableBody>
    </Table>
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
  const [username, setUsername] = useState('')

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
    const full = readFull()
    if (full && ((full.old_songs && full.old_songs.length) || (full.new_songs && full.new_songs.length))) {
      setFullDataState(full)
      // Use the table's full-data ordering/content for the grid so they stay in sync
      const oldArr = (full.old_songs || []).slice().sort((a, b) => b.calculated_rating - a.calculated_rating).slice(0, 35)
      const newArr = (full.new_songs || []).slice().sort((a, b) => b.calculated_rating - a.calculated_rating).slice(0, 15)
      setB50State({ old_songs: oldArr, new_songs: newArr })
    } else {
      const stored = readB50()
      setB50State(recategorize(stored, maimaiSongsDict))
      setFullDataState(null)
    }
    setUsername(localStorage.getItem(USERNAME_KEY) || '')
  }, [maimaiSongsDict])

  const updateUsername = (val: string) => {
    setUsername(val)
    localStorage.setItem(USERNAME_KEY, val)
  }

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
    showStatus('Generating image from fixed viewport...', 'info', 0)
    const el = gridRef.current
    if (!el) return
    // Capture the entire B50 stage (includes player name and total rating)
    const prevOverflow = el.style.overflow
    const prevWidth = el.style.width

    // Render the grid in a hidden, fixed-size offscreen container so output is consistent
    const FIXED_VIEWPORT_WIDTH = 1000
    const MAX = 32000
    let container: HTMLDivElement | null = null
    try {
      // create offscreen container
      container = document.createElement('div')
      container.classList.add('b50-print-clone')
      container.style.position = 'fixed'
      container.style.left = '-100000px'
      container.style.top = '0'
      container.style.width = `${FIXED_VIEWPORT_WIDTH}px`
      container.style.overflow = 'visible'
      container.style.visibility = 'visible'
      container.style.zIndex = '2147483647'
      // Do NOT force layout styles here; preserve live styling and instead
      // crop the final canvas to the stage/grid bounding box so exported
      // images match the live UI without mutating layout.

      // clone the grid and sanitize styles that may vary per user
      const clone = el.cloneNode(true) as HTMLElement
      clone.querySelectorAll('[id]').forEach(n => n.removeAttribute('id'))
      clone.style.width = '100%'
      clone.style.boxSizing = 'border-box'
      clone.style.transform = 'none'
      clone.style.transition = 'none'
      clone.querySelectorAll('*').forEach(node => {
        const nn = node as HTMLElement
        nn.style.transition = 'none'
        nn.style.transform = 'none'
        nn.style.willChange = 'auto'
      })

      container.appendChild(clone)
      document.body.appendChild(container)

      // Neutralize any fixed-position descendants inside the clone so they
      // don't render relative to the real viewport. Keep layout stable.
      try {
        Array.from(container.querySelectorAll('*')).forEach(n => {
          try {
            const nn = n as HTMLElement
            const cs = window.getComputedStyle(nn)
            if (cs.position === 'fixed') {
              nn.style.position = 'relative'
              nn.style.top = 'auto'
              nn.style.left = 'auto'
            }
          } catch (e) { /* ignore per-node errors */ }
        })
      } catch (e) { /* ignore */ }

      // Copy a set of important computed style properties from the live
      // grid into the clone. This greatly improves fidelity for the
      // exported image without attempting to copy every single CSS
      // property (which can break layout when applied verbatim).
      try {
        // Copy a conservative set of visual properties. Intentionally omit
        // font-size/padding/margin/position-related properties so the
        // `print-b50.css` stylesheet can enforce consistent exported layout
        // (inline styles copied from computed styles would otherwise override it).
        const propsToCopy = [
          'color', 'background', 'background-image', 'background-color', 'background-size', 'background-position', 'background-clip', '-webkit-background-clip', '-webkit-text-fill-color',
          'text-shadow', 'letter-spacing',
          'border',
          'display', 'align-items', 'justify-content', 'box-sizing', 'white-space', 'overflow', 'text-align', 'vertical-align', 'opacity', 'flex-direction', 'flex-wrap', 'gap'
        ]

        // Limit computed-style copying to a small set of selectors to
        // reduce main-thread work on mobile devices.
        const sel = '.song-card, .song-card-art, .song-card-info, .song-card-title, .song-card-meta, .song-card-const-group, .song-card-rank, .b50-stage, .b50-total, .b50-section-banner'
        const origAll = Array.from(el.querySelectorAll(sel)) as HTMLElement[]
        const cloneAll = Array.from(clone.querySelectorAll(sel)) as HTMLElement[]
        const len = Math.min(origAll.length, cloneAll.length)
        for (let i = 0; i < len; i++) {
          try {
            const o = origAll[i]
            const c = cloneAll[i]
            const oc = window.getComputedStyle(o)
            for (const p of propsToCopy) {
              const val = oc.getPropertyValue(p)
              if (val && val !== 'initial' && val !== 'inherit') {
                c.style.setProperty(p, val, oc.getPropertyPriority(p))
              }
            }
          } catch (e) { /* ignore per-node copy errors */ }
        }

        // As a robust fallback, ensure achievement text remains readable and
        // try to preserve rank visuals where possible. html2canvas has
        // well-known limits for background-clip:text so we still fall back
        // to a solid color when necessary.
        const DEFAULT_TEXT_COLOR = '#ffffff'
        Array.from(clone.querySelectorAll('.song-card-ach')).forEach((n) => {
          try {
            const elA = n as HTMLElement
            elA.style.color = DEFAULT_TEXT_COLOR
            elA.style.backgroundImage = 'none'
            elA.style.backgroundClip = 'unset'
            ;(elA.style as any).webkitBackgroundClip = 'unset'
            ;(elA.style as any).webkitTextFillColor = DEFAULT_TEXT_COLOR
          } catch (e) { /* ignore per-node errors */ }
        })

        const origRanks = Array.from(el.querySelectorAll('.song-card-rank')) as HTMLElement[]
        const cloneRanks = Array.from(clone.querySelectorAll('.song-card-rank')) as HTMLElement[]
        for (let i = 0; i < cloneRanks.length; i++) {
          const o = origRanks[i]
          const cNode = cloneRanks[i]
          if (!o || !cNode) continue
          try {
            const oc = window.getComputedStyle(o)
            const bgImage = oc.getPropertyValue('background-image') || ''
            const hasTextGradient = /gradient|linear-gradient|radial-gradient/i.test(bgImage)
            if (!hasTextGradient) {
              cNode.style.backgroundImage = oc.backgroundImage || ''
              cNode.style.backgroundClip = oc.backgroundClip || ''
              ;(cNode.style as any).webkitBackgroundClip = (oc as any).webkitBackgroundClip || ''
              ;(cNode.style as any).webkitTextFillColor = (oc as any).webkitTextFillColor || ''
            } else {
              const rankText = (o.textContent || cNode.textContent || '').trim()
              cNode.style.backgroundImage = 'none'
              cNode.style.backgroundClip = 'unset'
              ;(cNode.style as any).webkitBackgroundClip = ''
              ;(cNode.style as any).webkitTextFillColor = ''
              cNode.style.color = rankSolidColor(rankText)
            }
            cNode.style.textShadow = oc.textShadow || ''
            cNode.style.fontWeight = oc.fontWeight || ''
            cNode.style.fontSize = oc.fontSize || ''
            cNode.style.padding = oc.padding || ''
          } catch (e) { /* ignore per-node errors */ }
        }
      } catch (e) {
        console.warn('Failed to copy computed styles for print clone:', e)
      }

      const w = clone.scrollWidth
      const h = clone.scrollHeight
      const isMobile = /Mobi|Android|iPhone|iPad|Mobile/i.test(navigator.userAgent) || window.innerWidth < 800
      const MAX_DIM = isMobile ? 16000 : MAX
      // Option A: on mobile, use the devicePixelRatio to improve output
      // quality for testing. Cap the DPR to a reasonable value to avoid
      // creating excessively large canvases on low-memory devices.
      const devicePR = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1
      const targetScale = isMobile ? Math.max(1, Math.min(devicePR, 3)) : 2
      const scale = Math.min(targetScale, MAX_DIM / Math.max(w, h))

      // Yield briefly so the browser can render the 'Generating...' status
      try { await new Promise(r => setTimeout(r, 50)) } catch (e) { /* ignore */ }

      // Ensure fonts are available and the clone uses the same font-family
      // This improves text metrics and truncation fidelity in html2canvas output.
      try {
        if ((document as any).fonts && (document as any).fonts.ready) {
          // await fonts to avoid layout with fallback fonts
          // eslint-disable-next-line @typescript-eslint/ban-ts-comment
          // @ts-ignore
          await (document as any).fonts.ready
        }
      } catch (e) { /* ignore font loading errors */ }
      try { clone.style.fontFamily = window.getComputedStyle(document.documentElement).fontFamily || '' } catch (e) { /* ignore */ }

      const bg = window.getComputedStyle(el).backgroundColor || '#0b1020'
      const canvas = await html2canvas(clone, {
        backgroundColor: bg,
        scale,
        useCORS: true,
        width: w,
        height: h,
        windowWidth: w,
        windowHeight: h,
      })

      // Crop the generated canvas to the visible stage (header -> last grid)
      // then convert to a Blob and present a preview using an object URL.
      try {
        let finalCanvas: HTMLCanvasElement = canvas
        try {
          const cloneRect = clone.getBoundingClientRect()
          const firstChild = clone.firstElementChild as HTMLElement | null
          const gridNodes = Array.from(clone.querySelectorAll('.b50-grid')) as HTMLElement[]

          const startY = firstChild ? Math.max(0, firstChild.getBoundingClientRect().top - cloneRect.top) : 0
          let endY = clone.scrollHeight
          if (gridNodes.length > 0) {
            const lastGrid = gridNodes[gridNodes.length - 1]
            const lastBottom = lastGrid.getBoundingClientRect().bottom - cloneRect.top
            endY = Math.min(clone.scrollHeight, Math.max(endY, lastBottom))
          }

          const safeStart = Math.max(0, Math.min(startY, clone.scrollHeight))
          const safeEnd = Math.max(safeStart, Math.min(endY, clone.scrollHeight))

          const sx = 0
          const sy = Math.round(safeStart * scale)
          const sw = Math.round(canvas.width)
          const sh = Math.round((safeEnd - safeStart) * scale)

          if (sh > 0 && sh <= canvas.height) {
            const cropped = document.createElement('canvas')
            cropped.width = sw
            cropped.height = sh
            const ctx = cropped.getContext('2d')
            if (ctx) ctx.drawImage(canvas, sx, sy, sw, sh, 0, 0, sw, sh)
            finalCanvas = cropped
          }
        } catch (e) {
          finalCanvas = canvas
        }

        const showPreviewFromUrl = (url: string) => {
          const overlay = document.createElement('div') as HTMLDivElement
          overlay.style.position = 'fixed'
          overlay.style.left = '0'
          overlay.style.top = '0'
          overlay.style.width = '100%'
          overlay.style.height = '100%'
          overlay.style.display = 'flex'
          overlay.style.alignItems = 'center'
          overlay.style.justifyContent = 'center'
          overlay.style.background = 'rgba(0,0,0,0.6)'
          overlay.style.zIndex = '2147483647'

          const modal = document.createElement('div') as HTMLDivElement
          modal.style.background = '#0b1020'
          modal.style.padding = '12px'
          modal.style.borderRadius = '8px'
          // Make the modal wide on mobile so the preview image can scale up
          modal.style.width = '90vw'
          modal.style.maxWidth = '1000px'
          modal.style.maxHeight = 'calc(100% - 120px)'
          modal.style.overflow = 'auto'
          modal.style.boxShadow = '0 8px 20px rgba(0,0,0,0.6)'
          modal.style.display = 'flex'
          modal.style.flexDirection = 'column'
          modal.style.alignItems = 'stretch'

          const img = document.createElement('img') as HTMLImageElement
          img.src = url
          // Force the preview image to fill the modal width so it is not tiny
          img.style.width = '100%'
          img.style.height = 'auto'
          img.style.maxHeight = 'calc(100vh - 200px)'
          img.style.display = 'block'
          img.style.margin = '0 auto'

          const controls = document.createElement('div') as HTMLDivElement
          controls.style.display = 'flex'
          controls.style.justifyContent = 'flex-end'
          controls.style.gap = '8px'
          controls.style.marginTop = '10px'

          const downloadBtn = document.createElement('button') as HTMLButtonElement
          downloadBtn.type = 'button'
          downloadBtn.textContent = 'Download'
          downloadBtn.style.background = '#7c3aed'
          downloadBtn.style.color = '#fff'
          downloadBtn.style.padding = '8px 12px'
          downloadBtn.style.borderRadius = '6px'
          downloadBtn.style.border = 'none'

          const closeBtn = document.createElement('button') as HTMLButtonElement
          closeBtn.type = 'button'
          closeBtn.textContent = 'Close'
          closeBtn.style.background = 'transparent'
          closeBtn.style.color = '#fff'
          closeBtn.style.padding = '8px 12px'
          closeBtn.style.border = '1px solid rgba(255,255,255,0.08)'
          closeBtn.style.borderRadius = '6px'

          const removeOverlay = () => {
            if (overlay.parentNode) overlay.parentNode.removeChild(overlay)
            try { URL.revokeObjectURL(url) } catch (e) { /* ignore */ }
          }

          // Defer creating the downloadable anchor until the user explicitly
          // taps the Download button — this prevents some mobile browsers
          // from auto-opening the download manager when the preview is shown.
          downloadBtn.addEventListener('click', () => {
            try {
              const a = document.createElement('a')
              a.href = url
              a.download = 'maimai_b50_grid.png'
              // Append to DOM for some browsers that require it for click()
              document.body.appendChild(a)
              a.click()
              document.body.removeChild(a)
            } catch (e) {
              // Fallback: open the image in a new tab
              try { window.open(url, '_blank') } catch (e) { /* ignore */ }
            }
            setTimeout(removeOverlay, 250)
          })

          closeBtn.addEventListener('click', () => removeOverlay())

          controls.appendChild(downloadBtn)
          controls.appendChild(closeBtn)
          modal.appendChild(img)
          modal.appendChild(controls)
          modal.addEventListener('click', e => e.stopPropagation())
          overlay.addEventListener('click', () => removeOverlay())
          overlay.appendChild(modal)
          document.body.appendChild(overlay)

          showStatus('Preview ready — close to dismiss or click Download.', 'success')
        }

        try {
          finalCanvas.toBlob((blob) => {
            if (!blob) {
              const url = finalCanvas.toDataURL('image/png')
              showPreviewFromUrl(url)
              return
            }
            const url = URL.createObjectURL(blob)
            showPreviewFromUrl(url)
          }, 'image/png')
        } catch (e) {
          const url = finalCanvas.toDataURL('image/png')
          showPreviewFromUrl(url)
        }
      } catch (err) {
        showStatus('Error: ' + (err as Error).message, 'danger')
      }
    } catch (err) {
      showStatus('Error: ' + (err as Error).message, 'danger')
    } finally {
      if (container && container.parentNode) container.parentNode.removeChild(container)
      el.style.overflow = prevOverflow
      el.style.width = prevWidth
    }
  }

  const display = b50
  const oldRating = display.old_songs.reduce((s, x) => s + x.calculated_rating, 0)
  const newRating = display.new_songs.reduce((s, x) => s + x.calculated_rating, 0)
  const totalRating = oldRating + newRating
  // Milestone image logic: choose the highest threshold <= totalRating
  const _milestones = [
    { t: 15000, file: '15k.png' },
    { t: 14500, file: '14k5.png' },
    { t: 14000, file: '14k.png' },
    { t: 13000, file: '13k.png' },
    { t: 12000, file: '12k.png' },
    { t: 10000, file: '10k.png' },
    { t: 7000, file: '7k.png' },
    { t: 4000, file: '4k.png' },
    { t: 2000, file: '2k.png' },
    { t: 1000, file: '1k.png' },
  ]
  const milestoneFile = _milestones.find(m => totalRating >= m.t)?.file ?? null
  const milestoneStyle = milestoneFile ? {
    backgroundImage: `url('/static/image/${milestoneFile}'), linear-gradient(135deg, #ec4899 0%, #a855f7 100%)`,
    backgroundSize: 'cover, cover',
    backgroundPosition: 'center, center',
    backgroundRepeat: 'no-repeat, no-repeat',
  } : undefined
  const count = display.old_songs.length + display.new_songs.length
  const avgRating = count > 0 ? Math.round(totalRating / count) : 0
  const oldCount = display.old_songs.length
  const newCount = display.new_songs.length
  const oldAvg = oldCount > 0 ? Math.round(oldRating / oldCount) : 0
  const newAvg = newCount > 0 ? Math.round(newRating / newCount) : 0

  const oldPad: (Song | null)[] = [...display.old_songs]; while (oldPad.length < 35) oldPad.push(null)
  const newPad: (Song | null)[] = [...display.new_songs]; while (newPad.length < 15) newPad.push(null)

  const tableOld = fullData?.old_songs?.length ? fullData.old_songs : display.old_songs
  const tableNew = fullData?.new_songs?.length ? fullData.new_songs : display.new_songs

  return (
    <MainLayout>
      <div className="w-full px-4 py-8 max-w-full sm:max-w-5xl mx-auto">
        <div className="text-center mb-8">
          <div className="mx-auto mb-1 max-w-full">
            <h1 className="font-extrabold leading-tight" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)', fontSize: 'clamp(1.4rem,6vw,3rem)' }}>
              AstroDX Rating Calculator
            </h1>
          </div>
        </div>

        <div className="rounded-xl border bg-card shadow-sm px-4 py-3 mb-6 flex flex-wrap gap-3 items-center semi-transparent">
          <div className="flex items-center gap-2">
            <Label htmlFor="username-input" className="text-xs text-muted-foreground">Player</Label>
            <Input
              id="username-input"
              type="text"
              value={username}
              onChange={e => updateUsername((e.target as HTMLInputElement).value)}
              placeholder="Your name"
              className="h-8 w-40"
              maxLength={32}
            />
          </div>
          <div className="h-5 w-px bg-border" />
          <div className="flex flex-wrap gap-2 items-center">
            <Button onClick={saveToFile} size="sm">
              <Download data-icon="inline-start" />
              Save B50
            </Button>
            <Button variant="outline" size="sm" onClick={() => b50FileRef.current?.click()}>
              <Upload data-icon="inline-start" />
              Load B50
            </Button>
            <Button variant="outline" size="sm" onClick={() => cacheFileRef.current?.click()}>
              <ArrowLeftRight data-icon="inline-start" />
              Convert Cache
            </Button>
            <div className="h-5 w-px bg-border mx-1" />
            <Button variant="secondary" size="sm" onClick={printB50}>
              <Camera data-icon="inline-start" />
              Print Grid
            </Button>
            <Button variant="destructive" size="sm" onClick={clearData}>
              <Trash2 data-icon="inline-start" />
              Clear
            </Button>
          </div>
          <input ref={b50FileRef} type="file" accept=".json" className="hidden" onChange={handleB50File} />
          <input ref={cacheFileRef} type="file" accept="*" className="hidden" onChange={handleCacheFile} />
        </div>

        {status.show && (
          <Alert
            variant={status.type === 'danger' ? 'destructive' : 'default'}
            className={`mb-4 ${statusAlertClass(status.type)}`}
            style={{ whiteSpace: 'pre-line' }}
          >
            <AlertDescription>{status.msg}</AlertDescription>
          </Alert>
        )}

        <div className="rounded-xl border bg-card shadow-sm p-4 mb-6 semi-transparent">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">Add Song</p>
          <form className="flex flex-wrap gap-3 items-end" autoComplete="off" onSubmit={addSong}>
            <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
              <Label htmlFor="song-input">Song Name</Label>
              <div className="relative">
                <Input
                  id="song-input"
                  type="text"
                  value={songInput}
                  required
                  onChange={e => { const v = (e.target as HTMLInputElement).value; setSongInput(v); buildDropdown(v); }}
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
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Difficulty</Label>
              <Select value={difficulty} onValueChange={(v) => setDifficulty(v ?? 'Basic')}>
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
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="achievement-input">Achievement (%)</Label>
              <Input
                id="achievement-input"
                type="number"
                className="w-36"
                step="0.0001"
                min="0"
                max="101"
                value={achievement}
                required
                onChange={e => setAchievement((e.target as HTMLInputElement).value)}
                placeholder="e.g. 100.5"
              />
            </div>
            <Button type="submit">Add Song</Button>
          </form>
        </div>

        <p className="text-xs mb-6 flex items-center gap-1.5 bg-muted/50 border rounded-lg px-3 py-2" style={{ color: 'rgba(0,0,0,0.95)' }}>
          <Info className="size-3.5 shrink-0" />
          To add an alias to a song, visit the Chart Database page.
        </p>

        {count > 0 && (
        <div className="rounded-xl border bg-card shadow-sm mb-6 overflow-hidden">
          <div ref={gridRef} className="b50-stage">
            <div className="flex flex-wrap items-center gap-4 px-5 py-4">
              <div className="flex flex-col flex-1 min-w-[260px]">
                <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#c4b5fd' }}>Player</span>
                <span className="text-5xl font-extrabold leading-tight truncate" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)' }}>
                  {username || 'Unnamed Player'}
                </span>
              </div>
              <div className="flex items-center gap-2 ml-auto">
                {display.old_songs.length > 0 && (
                  <div className="rounded-lg px-3 py-1.5 text-center" style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(96,165,250,0.4)' }}>
                    <div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: '#93c5fd' }}>Old B35</div>
                    <div className="text-lg font-black leading-none mt-0.5" style={{ color: '#fff' }}>{oldRating}</div>
                    <div className="b50-small-stat">{oldAvg}</div>
                  </div>
                )}
                <div className={`rounded-lg px-4 py-1.5 text-center b50-total`} style={milestoneStyle}>
                  <div className="text-[9px] font-bold uppercase tracking-widest b50-total-label">Total</div>
                  <div className="text-xl font-black leading-none mt-0.5 b50-total-value">{totalRating}</div>
                  <div className="b50-small-stat">{avgRating}</div>
                </div>
                {display.new_songs.length > 0 && (
                  <div className="rounded-lg px-3 py-1.5 text-center" style={{ background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(134,239,172,0.4)' }}>
                    <div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: '#86efac' }}>New B15</div>
                    <div className="text-lg font-black leading-none mt-0.5" style={{ color: '#fff' }}>{newRating}</div>
                    <div className="b50-small-stat">{newAvg}</div>
                  </div>
                )}
              </div>
              {/* removed Average Rating subtitle (averages now shown under each category) */}
            </div>

            {display.old_songs.length > 0 && (
              <>
                <div className="b50-section-banner b50-banner-old">
                  <span>★ Best 35 · Old Charts (PRE-PRiSM)</span>
                  <span className="b50-banner-stat">{oldRating}</span>
                </div>
                <div className="b50-grid">
                  {oldPad.slice(0, 35).map((s, i) => (
                    <SongCell key={i} song={s ?? null} songDict={maimaiSongsDict} />
                  ))}
                </div>
              </>
            )}

            {display.new_songs.length > 0 && (
              <>
                <div className="b50-section-banner b50-banner-new">
                  <span>★ Best 15 · New Charts (PRiSM PLUS / CiRCLE)</span>
                  <span className="b50-banner-stat">{newRating}</span>
                </div>
                <div className="b50-grid pb-4">
                  {newPad.slice(0, 15).map((s, i) => (
                    <SongCell key={i} song={s ?? null} songDict={maimaiSongsDict} />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
        )}

        {tableOld.length > 0 && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden mb-6">
            <div className="px-4 py-3 border-b bg-muted/30">
              <h2 className="text-sm font-semibold">Old Songs — All {fullData?.old_songs?.length ?? display.old_songs.length} chart scores</h2>
            </div>
            <SongTable label="Old Songs" songs={tableOld} idPrefix="old" />
          </div>
        )}
        {tableNew.length > 0 && (
          <div className="rounded-xl border bg-card shadow-sm overflow-hidden mb-6">
            <div className="px-4 py-3 border-b bg-muted/30">
              <h2 className="text-sm font-semibold">New Songs — All {fullData?.new_songs?.length ?? display.new_songs.length} chart scores</h2>
            </div>
            <SongTable label="New Songs" songs={tableNew} idPrefix="new" />
          </div>
        )}
      </div>
    </MainLayout>
  )
}
