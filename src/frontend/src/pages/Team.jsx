import { useState, useMemo } from 'react'
import { useData } from '../hooks/useData'
import { fetchTeamIndividual, fetchTeamEventDivisionGenderTotals } from '../services/api'
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

/**
 * Team Standings — aggregates filtered rows by team, sums points, re-ranks.
 */
function TeamStandingsSection({ title, subtitle, loading, error, data, onReload }) {
  const [filters, setFilters] = useState({})
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))

  const filteredRaw = useFiltered(data, filters)

  const aggregated = useMemo(() => {
    const map = {}
    for (const row of filteredRaw) {
      const t = row.team
      if (!map[t]) map[t] = { team: t, total_points: 0 }
      map[t].total_points += Number(row.total_points) || 0
      if (filters.division)   map[t].division   = row.division
      if (filters.gender)     map[t].gender      = row.gender
      if (filters.event_name) map[t].event_name  = row.event_name
    }
    const rows = Object.values(map).sort((a, b) => b.total_points - a.total_points)
    rows.forEach((r, i) => { r.team_rank = i + 1 })
    return rows
  }, [filteredRaw, filters])

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
          <DataGrid data={aggregated} columns={columns} rowCount={aggregated.length} />
        </>
      )}
    </section>
  )
}

function Section({ title, subtitle, loading, error, data, columns, filterDefs, onReload, limit = null }) {
  const [filters, setFilters] = useState({})
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))
  const filtered = useFiltered(data, filters)

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
          <DataGrid data={filtered} columns={columns} rowCount={data.length} limit={limit} />
        </>
      )}
    </section>
  )
}

export default function Team() {
  const ti  = useData(fetchTeamIndividual)
  const tot = useData(fetchTeamEventDivisionGenderTotals)

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
        loading={tot.loading}
        error={tot.error}
        data={tot.data}
        onReload={tot.reload}
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
      />
    </div>
  )
}
