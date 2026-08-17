import { useState, useMemo } from 'react'
import { useData } from '../hooks/useData'
import { fetchTeamIndividual, fetchTeamEventDivisionGenderTotals, fetchTeamTotals } from '../services/api'
import FilterBar from '../components/FilterBar'
import DataGrid from '../components/DataGrid'
import { Spinner, ErrorState } from '../components/LoadingState'

const TEAM_INDIV_FILTERS = [
  { key: 'event_name', label: 'Event' },
  { key: 'division',   label: 'Division' },
  { key: 'gender',     label: 'Gender' },
  { key: 'team',       label: 'Team' },
]

const TEAM_INDIV_COLS = [
  { key: 'rank',              label: 'Rank',       type: 'rank' },
  { key: 'team',              label: 'Team' },
  { key: 'runner',            label: 'Runner' },
  { key: 'age',               label: 'Age' },
  { key: 'time',              label: 'Time',       type: 'time' },
  { key: 'team_time',         label: 'Team Time',  type: 'time' },
  { key: 'overall_race_rank', label: 'Overall' },
  { key: 'division',          label: 'Division',   type: 'division' },
  { key: 'gender',            label: 'Gender',     type: 'gender' },
  { key: 'event_name',        label: 'Event' },
]

const TOTALS_FILTERS = [
  { key: 'event_name', label: 'Event' },
  { key: 'division',   label: 'Division' },
  { key: 'gender',     label: 'Gender' },
]


function useFiltered(data, filters) {
  return useMemo(() => {
    return data.filter(row =>
      Object.entries(filters).every(([k, v]) =>
        !v || String(row[k]).toLowerCase() === String(v).toLowerCase()
      )
    )
  }, [data, filters])
}

function rankByPoints(rows) {
  return [...rows]
    .map(r => ({ ...r, total_points: Number(r.total_points) || 0 }))
    .sort((a, b) => b.total_points - a.total_points)
    .map((r, i) => ({ ...r, team_rank: i + 1 }))
}

/**
 * Team Standings — season totals by default; re-aggregates when filters are set.
 */
function TeamStandingsSection({ title, subtitle, loading, error, data, seasonTotals = [], onReload }) {
  const [filters, setFilters] = useState({})
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))

  const hasFilter = Object.values(filters).some(Boolean)
  const filteredRaw = useFiltered(data, filters)

  const aggregated = useMemo(() => {
    if (!hasFilter) {
      return rankByPoints(seasonTotals)
    }
    const map = {}
    for (const row of filteredRaw) {
      const t = row.team
      if (!map[t]) map[t] = { team: t, total_points: 0 }
      map[t].total_points += Number(row.total_points) || 0
      if (filters.division)   map[t].division   = row.division
      if (filters.gender)     map[t].gender      = row.gender
      if (filters.event_name) map[t].event_name  = row.event_name
    }
    return rankByPoints(Object.values(map))
  }, [filteredRaw, filters, hasFilter, seasonTotals])

  const columns = useMemo(() => {
    const cols = [
      { key: 'team_rank',    label: 'Rank',   type: 'rank' },
      { key: 'team',         label: 'Team' },
      { key: 'total_points', label: 'Points', type: 'points' },
    ]
    if (filters.division)   cols.push({ key: 'division',   label: 'Division', type: 'division' })
    if (filters.gender)     cols.push({ key: 'gender',     label: 'Gender',   type: 'gender' })
    if (filters.event_name) cols.push({ key: 'event_name', label: 'Event' })
    return cols
  }, [filters])

  return (
    <section className="mb-10">
      <div className="mb-4">
        <h2 className="section-header">{title}</h2>
        {subtitle && <p className="text-sm text-brand-muted mt-1">{subtitle}</p>}
      </div>
      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={onReload} />}
      {!loading && !error && (
        <>
          <FilterBar
            filters={TOTALS_FILTERS}
            values={filters}
            onChange={setFilter}
            data={data}
          />
          <DataGrid
            data={aggregated}
            columns={columns}
            rowCount={aggregated.length}
            defaultSortKey="total_points"
            defaultSortDir="desc"
          />
        </>
      )}
    </section>
  )
}

function numericValue(v) {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const t = v.trim()
    if (t === '') return null
    const n = Number(t)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function multiSort(rows, keys) {
  return [...rows].sort((a, b) => {
    for (const { key, dir } of keys) {
      const av = a[key], bv = b[key]
      const aNum = numericValue(av)
      const bNum = numericValue(bv)
      const cmp = (aNum !== null && bNum !== null)
        ? aNum - bNum
        : String(av ?? '').localeCompare(String(bv ?? ''), undefined, { numeric: true })
      if (cmp !== 0) return dir === 'desc' ? -cmp : cmp
    }
    return 0
  })
}

function Section({ title, subtitle, loading, error, data, columns, filterDefs, onReload, limit = null, preSortKeys = null }) {
  const [filters, setFilters] = useState({})
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))
  const filtered = useFiltered(data, filters)
  const display = useMemo(
    () => preSortKeys ? multiSort(filtered, preSortKeys) : filtered,
    [filtered, preSortKeys]
  )

  return (
    <section className="mb-10">
      <div className="mb-4">
        <h2 className="section-header">{title}</h2>
        {subtitle && <p className="text-sm text-brand-muted mt-1">{subtitle}</p>}
      </div>

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={onReload} />}

      {!loading && !error && (
        <>
          <FilterBar
            filters={filterDefs}
            values={filters}
            onChange={setFilter}
            data={data}
          />
          <DataGrid data={display} columns={columns} rowCount={data.length} limit={limit} />
        </>
      )}
    </section>
  )
}

export default function Team() {
  const ti  = useData(fetchTeamIndividual)
  const tot = useData(fetchTeamEventDivisionGenderTotals)
  const season = useData(fetchTeamTotals)

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="font-display font-extrabold text-4xl text-brand-navy tracking-wide uppercase">
          Team Standings
        </h1>
        <p className="text-brand-muted mt-1">
          Scoring members and point totals per event, division, and gender.
        </p>
      </div>

      <TeamStandingsSection
        title="Team Points"
        subtitle="Total points and rank per team. Use filters to narrow by event, division, or gender."
        loading={tot.loading || season.loading}
        error={tot.error || season.error}
        data={tot.data}
        seasonTotals={season.data}
        onReload={() => { tot.reload(); season.reload() }}
      />

      <Section
        title="Scoring Members"
        subtitle="Individual runners who counted toward their team's score for each event."
        loading={ti.loading}
        error={ti.error}
        data={ti.data}
        columns={TEAM_INDIV_COLS}
        filterDefs={TEAM_INDIV_FILTERS}
        onReload={ti.reload}
        limit={10}
        preSortKeys={[
          { key: 'rank',           dir: 'asc' },
          { key: 'team',           dir: 'asc' },
          { key: 'time_in_millis', dir: 'asc' },
        ]}
      />
    </div>
  )
}
