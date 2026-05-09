import { useState, useRef, useMemo } from 'react'
import { usePage, router, Link } from '@inertiajs/react'
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Download, FileUp, Tag, X, Info } from 'lucide-react'

interface AnalyzedSkill {
  Slide?: { Total?: number; 'estimated difficulty'?: number }
  Spin?: { Total?: number; avg?: number }
  Taps?: { Total?: number; avg?: number }
  Trills?: { Total?: number; avg?: number }
}

interface SongInfo {
  version?: string
  chart_type?: string
  image_url?: string
  analyzed_skills?: Record<string, AnalyzedSkill>
}

type SongsDict = Record<string, SongInfo>

interface DbSong {
  id: number
  title: string
  title_kana: string
  artist: string
  catcode: string
  image_url: string
  release: string
  lev_bas: string
  lev_adv: string
  lev_exp: string
  lev_mas: string
  lev_remas: string
  sort: string
  version: string
  chart_type: string
}

interface Pagination {
  page: number
  numPages: number
  hasPrevious: boolean
  hasNext: boolean
  previousPage: number
  nextPage: number
  totalCount: number
  startIndex: number
}

interface Filters {
  title: string
  version: string
  artist: string
  catcode: string
  chartType: string
  difficulty: string
}

interface ChartDatabasePageProps {
  songs: DbSong[]
  pagination: Pagination
  filterTitles: string[]
  filterVersions: string[]
  filterArtists: string[]
  filterCatcodes: string[]
  aliasToTitleMap: Record<string, string>
  currentFilters: Filters
  maimaiSongsDict: SongsDict
}

interface AutocompleteProps {
  id: string
  value: string
  onChange: (val: string) => void
  options: string[]
  aliasMap?: Record<string, string>
  placeholder: string
}

interface DropdownItem {
  value: string
  type: 'exact' | 'fuzzy'
  sim: number
}

interface AliasStatus {
  msg: string
  type: string
  show: boolean
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

function aliasStatusClass(type: string): string {
  if (type === 'success') return 'border-green-500/50 bg-green-50 text-green-800 dark:bg-green-950/30 dark:text-green-400'
  if (type === 'warning') return 'border-yellow-500/40 bg-yellow-50 text-yellow-800 dark:bg-yellow-950/30 dark:text-yellow-400'
  return ''
}

function Autocomplete({ id, value, onChange, options, aliasMap, placeholder }: AutocompleteProps) {
  const [items, setItems] = useState<DropdownItem[]>([])

  function build(val: string) {
    if (!val) { setItems([]); return }
    const v = val.toLowerCase()
    const matches: DropdownItem[] = []
    const seen = new Set<string>()
    const add = (value: string, type: 'exact' | 'fuzzy', sim = 100) => {
      if (!seen.has(value)) { seen.add(value); matches.push({ value, type, sim }) }
    }
    if (aliasMap) {
      Object.keys(aliasMap).filter(a => a.toLowerCase().includes(v)).forEach(a => add(aliasMap[a], 'exact'))
      options.filter(n => n.toLowerCase().includes(v)).forEach(n => add(n, 'exact'))
      if (matches.length < 5) {
        Object.keys(aliasMap).forEach(a => {
          const t = aliasMap[a]
          if (!seen.has(t)) { const s = calcSimilarity(v, a.toLowerCase()); if (s >= 30) { seen.add(t); matches.push({ value: t, type: 'fuzzy', sim: s }) } }
        })
        options.forEach(n => {
          if (!seen.has(n)) { const s = calcSimilarity(v, n.toLowerCase()); if (s >= 30) { seen.add(n); matches.push({ value: n, type: 'fuzzy', sim: s }) } }
        })
      }
    } else {
      options.filter(o => o.toLowerCase().includes(v)).forEach(o => add(o, 'exact'))
      if (matches.length < 5) options.forEach(o => {
        if (!seen.has(o)) { const s = calcSimilarity(v, o.toLowerCase()); if (s >= 30) { seen.add(o); matches.push({ value: o, type: 'fuzzy', sim: s }) } }
      })
    }
    matches.sort((a, b) => { if (a.type !== b.type) return a.type === 'exact' ? -1 : 1; return b.sim - a.sim })
    setItems(matches.slice(0, 10))
  }

  return (
    <div className="relative">
      <Input
        id={id}
        type="text"
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        onChange={e => { onChange(e.target.value); build(e.target.value) }}
      />
      {items.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border bg-popover text-popover-foreground shadow-md">
          {items.map((m, i) => (
            <button
              key={i}
              type="button"
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              onClick={() => { onChange(m.value); setItems([]) }}
            >
              {m.value}
              {m.type === 'fuzzy' && <span className="text-muted-foreground text-xs ml-1">({m.sim}% match)</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ChartDatabase() {
  const { songs, pagination, filterTitles, filterVersions, filterArtists, filterCatcodes, aliasToTitleMap, currentFilters, maimaiSongsDict } =
    usePage().props as unknown as ChartDatabasePageProps

  const [filters, setFilters] = useState<Filters>(currentFilters)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalSong, setModalSong] = useState<DbSong | null>(null)
  const [aliases, setAliases] = useState<string[]>([])
  const [newAlias, setNewAlias] = useState('')
  const [aliasStatus, setAliasStatus] = useState<AliasStatus>({ msg: '', type: 'info', show: false })
  const statusTimer = useRef<number>(0)

  function setF(key: keyof Filters) { return (val: string) => setFilters(f => ({ ...f, [key]: val })) }

  function handleFilter(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const params: Record<string, string> = {}
    if (filters.title) params.title = filters.title
    if (filters.version) params.version = filters.version
    if (filters.artist) params.artist = filters.artist
    if (filters.catcode) params.catcode = filters.catcode
    if (filters.chartType) params.chart_type = filters.chartType
    if (filters.difficulty) params.difficulty = filters.difficulty
    router.get('/chart-database/', params, { preserveState: false })
  }

  function pageUrl(p: number): string {
    const params = new URLSearchParams()
    if (currentFilters.title) params.set('title', currentFilters.title)
    if (currentFilters.version) params.set('version', currentFilters.version)
    if (currentFilters.artist) params.set('artist', currentFilters.artist)
    if (currentFilters.catcode) params.set('catcode', currentFilters.catcode)
    if (currentFilters.chartType) params.set('chart_type', currentFilters.chartType)
    if (currentFilters.difficulty) params.set('difficulty', currentFilters.difficulty)
    params.set('page', String(p))
    return `/chart-database/?${params.toString()}`
  }

  const sortedSongs = useMemo(() => {
    return songs
  }, [songs])

  function showAliasMsg(msg: string, type: string, ms = 3000) {
    clearTimeout(statusTimer.current)
    setAliasStatus({ msg, type, show: true })
    if (ms > 0) statusTimer.current = window.setTimeout(() => setAliasStatus(s => ({ ...s, show: false })), ms)
  }

  async function openModal(song: DbSong) {
    setModalSong(song); setNewAlias(''); setAliasStatus({ msg: '', type: 'info', show: false })
    const res = await fetch(`/chart-database/get-aliases/${song.id}/`)
    const d = await res.json() as { status: string; aliases: string[] }
    setAliases(d.status === 'success' ? d.aliases : [])
    setModalOpen(true)
  }

  async function addAlias() {
    if (!newAlias.trim()) { showAliasMsg('Enter an alias name', 'warning'); return }
    showAliasMsg('Adding...', 'info', 0)
    const res = await fetch('/chart-database/add-alias/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ song_id: modalSong!.id, alias: newAlias.trim() }),
    })
    const d = await res.json() as { status: string; aliases: string[]; message: string }
    if (d.status === 'success') { setAliases(d.aliases); setNewAlias(''); showAliasMsg(d.message, 'success') }
    else showAliasMsg(d.message, 'danger', 0)
  }

  async function removeAlias(alias: string) {
    showAliasMsg('Removing...', 'info', 0)
    const res = await fetch('/chart-database/remove-alias/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify({ song_id: modalSong!.id, alias }),
    })
    const d = await res.json() as { status: string; aliases: string[]; message: string }
    if (d.status === 'success') { setAliases(d.aliases); showAliasMsg(d.message, 'success') }
    else showAliasMsg(d.message, 'danger', 0)
  }

  return (
    <MainLayout>
      <div className="w-full px-4 py-8 max-w-5xl mx-auto">
          <div className="text-center mb-8">
            <div className="mx-auto mb-1">
              <span className="text-5xl font-extrabold leading-tight truncate" style={{ color: '#fff', textShadow: '0 2px 18px rgba(236,72,153,0.6)' }}>
                Chart Database
              </span>
            </div>
            <p className="text-sm page-subtitle">Browse and filter all maimai songs</p>
          </div>

        <div className="rounded-xl border bg-card shadow-sm p-4 mb-6 semi-transparent">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">Filters</p>
          <form className="flex flex-wrap gap-2 items-center" autoComplete="off" onSubmit={handleFilter}>
            <div className="w-44">
              <Autocomplete id="filter_title" value={filters.title} onChange={setF('title')} options={filterTitles} aliasMap={aliasToTitleMap} placeholder="Song Name or Alias" />
            </div>
            <div className="w-36">
              <Autocomplete id="filter_version" value={filters.version} onChange={setF('version')} options={filterVersions} placeholder="Version" />
            </div>
            <div className="w-36">
              <Autocomplete id="filter_artist" value={filters.artist} onChange={setF('artist')} options={filterArtists} placeholder="Artist" />
            </div>
            <Select value={filters.catcode} onValueChange={(v) => setF('catcode')(v ?? '')}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Catcode" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="">All Catcodes</SelectItem>
                  {filterCatcodes.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={filters.chartType} onValueChange={(v) => setF('chartType')(v ?? '')}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Chart Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="">All Types</SelectItem>
                  <SelectItem value="STD">STD</SelectItem>
                  <SelectItem value="DX">DX</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
            <Select value={filters.difficulty} onValueChange={(v) => setF('difficulty')(v ?? '')}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Difficulty" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="">All Difficulties</SelectItem>
                  {['Basic', 'Advanced', 'Expert', 'Master', 'Re:Master'].map(d => (
                    <SelectItem key={d} value={d}>{d}</SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <div className="h-5 w-px bg-border mx-0.5" />
            <Button type="submit">Filter</Button>
            <Link href="/chart-database/">
              <Button type="button" variant="secondary">Reset</Button>
            </Link>
            <a href="/chart-database/download/">
              <Button type="button" variant="outline" size="sm">
                <Download data-icon="inline-start" />
                Download JSON
              </Button>
            </a>
            <Link href="/chart-database/alias-upload/">
              <Button type="button" variant="outline" size="sm">
                <FileUp data-icon="inline-start" />
                Alias Upload
              </Button>
            </Link>
          </form>
        </div>

        <div className="flex items-center justify-between mb-3 text-sm">
          <div><strong>{pagination.totalCount}</strong> result{pagination.totalCount !== 1 ? 's' : ''} found</div>
          <span className="text-muted-foreground flex items-center gap-1 text-xs">
            <Info className="size-3.5" /> Search by song name or aliases
          </span>
        </div>

        <div className="rounded-xl border bg-card shadow-sm overflow-hidden mb-6 semi-transparent">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">#</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Artist</TableHead>
                <TableHead>Image</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Basic</TableHead>
                <TableHead>Adv</TableHead>
                <TableHead>Exp</TableHead>
                <TableHead>Mas</TableHead>
                <TableHead>Re:Mas</TableHead>
                <TableHead className="w-44">Skills Rating</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {songs.length === 0
                ? <TableRow><TableCell colSpan={13} className="text-center text-muted-foreground py-12">No songs found.</TableCell></TableRow>
                : sortedSongs.map((s, i) => (
                  <TableRow key={s.id}>
                    <TableCell className="text-muted-foreground text-xs">{pagination.startIndex + i}</TableCell>
                    <TableCell className="font-medium max-w-[180px]">
                      <div className="truncate">{s.title}</div>
                      {s.catcode && <div className="text-xs text-muted-foreground">{s.catcode}</div>}
                    </TableCell>
                    <TableCell className="text-sm max-w-[140px]"><div className="truncate">{s.artist}</div></TableCell>
                    <TableCell>
                      {s.image_url
                        ? <a href={s.image_url} target="_blank" rel="noreferrer">
                            <img src={s.image_url} alt="" loading="lazy" className="h-10 w-10 rounded object-cover" />
                          </a>
                        : <div className="h-10 w-10 rounded bg-muted flex items-center justify-center text-muted-foreground text-xs">—</div>}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground max-w-[120px]"><div className="truncate">{s.version}</div></TableCell>
                    <TableCell>
                      <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-semibold ${s.chart_type === 'DX' ? 'bg-amber-100 text-amber-700' : 'bg-sky-100 text-sky-700'}`}>
                        {s.chart_type}
                      </span>
                    </TableCell>
                    <TableCell>{s.lev_bas ? <span className="inline-block rounded px-1.5 py-0.5 text-xs font-semibold bg-green-100 text-green-700">{s.lev_bas}</span> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                    <TableCell>{s.lev_adv ? <span className="inline-block rounded px-1.5 py-0.5 text-xs font-semibold bg-orange-100 text-orange-700">{s.lev_adv}</span> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                    <TableCell>{s.lev_exp ? <span className="inline-block rounded px-1.5 py-0.5 text-xs font-semibold bg-red-100 text-red-700">{s.lev_exp}</span> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                    <TableCell>{s.lev_mas ? <span className="inline-block rounded px-1.5 py-0.5 text-xs font-semibold bg-purple-100 text-purple-700">{s.lev_mas}</span> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                    <TableCell>{s.lev_remas ? <span className="inline-block rounded px-1.5 py-0.5 text-xs font-semibold bg-fuchsia-100 text-fuchsia-700">{s.lev_remas}</span> : <span className="text-muted-foreground text-xs">—</span>}</TableCell>
                    <TableCell className="w-44 text-xs">
                      {(() => {
                        const difficulties = [
                          { name: 'Basic', lev: s.lev_bas },
                          { name: 'Adv', lev: s.lev_adv },
                          { name: 'Exp', lev: s.lev_exp },
                          { name: 'Mas', lev: s.lev_mas },
                          { name: 'Re:Mas', lev: s.lev_remas },
                        ]
                        return (
                          <div className="text-left pl-1">
                            {difficulties.map(({ name, lev }) => {
                              const data = lev && maimaiSongsDict?.[s.title]?.analyzed_skills?.[name]
                              if (!data) return null
                              return (
                                <div key={name} className="mb-0.5">
                                  <span className="text-muted-foreground">{name}:</span> {data.Slide?.Total?.toFixed(0) || '-'}/{data.Spin?.Total?.toFixed(0) || '-'}/{data.Taps?.Total?.toFixed(0) || '-'}/{data.Trills?.Total?.toFixed(0) || '-'}
                                </div>
                              )
                            })}
                          </div>
                        )
                      })()}
                    </TableCell>
                    <TableCell>
                      <Button size="sm" variant="outline" onClick={() => openModal(s)}>
                        <Tag data-icon="inline-start" />
                        Aliases
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>

        <div className="flex items-center justify-center gap-1 mt-4">
          {pagination.hasPrevious
            ? <Link href={pageUrl(1)}><Button variant="outline" size="sm">« First</Button></Link>
            : <Button variant="outline" size="sm" disabled>« First</Button>}
          {pagination.hasPrevious
            ? <Link href={pageUrl(pagination.previousPage)}><Button variant="outline" size="sm">‹ Prev</Button></Link>
            : <Button variant="outline" size="sm" disabled>‹ Prev</Button>}
          <Button variant="ghost" size="sm" disabled>
            Page {pagination.page} of {pagination.numPages}
          </Button>
          {pagination.hasNext
            ? <Link href={pageUrl(pagination.nextPage)}><Button variant="outline" size="sm">Next ›</Button></Link>
            : <Button variant="outline" size="sm" disabled>Next ›</Button>}
          {pagination.hasNext
            ? <Link href={pageUrl(pagination.numPages)}><Button variant="outline" size="sm">Last »</Button></Link>
            : <Button variant="outline" size="sm" disabled>Last »</Button>}
        </div>

        <Dialog open={modalOpen} onOpenChange={setModalOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Manage Aliases</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col gap-4">
              <div className="text-sm"><strong>Song:</strong> {modalSong?.title}</div>

              <div className="flex flex-col gap-1.5">
                <Label>Add New Alias:</Label>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    value={newAlias}
                    placeholder="Enter alias name"
                    onChange={e => setNewAlias(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addAlias()}
                  />
                  <Button type="button" onClick={addAlias}>Add</Button>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Current Aliases:</Label>
                <div className="border rounded-lg min-h-24 max-h-48 overflow-y-auto p-2 flex flex-col gap-1.5">
                  {aliases.length === 0
                    ? <em className="text-muted-foreground text-sm">No aliases added yet.</em>
                    : aliases.map((a, i) => (
                      <div key={i} className="flex items-center justify-between rounded-md bg-muted px-3 py-1.5 text-sm">
                        <span>{a}</span>
                        <Button size="icon-xs" variant="destructive" onClick={() => removeAlias(a)}>
                          <X />
                        </Button>
                      </div>
                    ))}
                </div>
              </div>

              {aliasStatus.show && (
                <Alert
                  variant={aliasStatus.type === 'danger' ? 'destructive' : 'default'}
                  className={aliasStatusClass(aliasStatus.type)}
                >
                  <AlertDescription>{aliasStatus.msg}</AlertDescription>
                </Alert>
              )}
            </div>
            <DialogFooter showCloseButton />
          </DialogContent>
        </Dialog>
      </div>
    </MainLayout>
  )
}
