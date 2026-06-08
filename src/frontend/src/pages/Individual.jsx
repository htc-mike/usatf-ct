import { useState, useMemo } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { useData } from '../hooks/useData'
import { fetchIndividual, fetchIndividualPoints } from '../services/api'
import FilterBar from '../components/FilterBar'
import DataGrid from '../components/DataGrid'
import { Spinner, ErrorState } from '../components/LoadingState'

const FILTER_DEFS = [
  { key: 'event_name', label: 'Event' },
  { key: 'division',   label: 'Division' },
  { key: 'gender',     label: 'Gender' },
  { key: 'team',       label: 'Team' },
]

const POINTS_FILTER_DEFS = [
  { key: 'event_name', label: 'Event' },
  { key: 'division',   label: 'Division' },
  { key: 'gender',     label: 'Gender' },
  { key: 'team',       label: 'Team' },
]

const POINTS_COLUMNS = [
  { key: 'rank',       label: 'Rank',     type: 'rank' },
  { key: 'division',   label: 'Division', type: 'division' },
  { key: 'runner',     label: 'Runner' },
  { key: 'gender',     label: 'Gender',   type: 'gender' },
  { key: 'age',        label: 'Age' },
  { key: 'time',       label: 'Time',     type: 'time' },
  { key: 'pace',       label: 'Pace/mi',  type: 'time' },
  { key: 'team',       label: 'Team' },
  { key: 'points',     label: 'Points',   type: 'points' },
  { key: 'event_name', label: 'Event' },
]

const POINTS_EXPAND_LIMIT = 10

const DIV_RANK_META = {
  open_rank:             'Open Rank',
  masters_rank:          'Masters Rank',
  grandmasters_rank:     'GM Rank',
  seniors_rank:          'Seniors Rank',
  open_m_rank:           'Open M Rank',
  open_f_rank:           'Open F Rank',
  masters_m_rank:        'Masters M Rank',
  masters_f_rank:        'Masters F Rank',
  grandmasters_m_rank:   'GM M Rank',
  grandmasters_f_rank:   'GM F Rank',
  seniors_m_rank:        'Seniors M Rank',
  seniors_f_rank:        'Seniors F Rank',
}

function getDivRankKey(division, gender) {
  const divMap = { open: 'open', masters: 'masters', grandmasters: 'grandmasters', seniors: 'seniors' }
  const genMap = { m: 'm', f: 'f' }
  const d = divMap[String(division ?? '').toLowerCase()] ?? null
  const g = genMap[String(gender ?? '').toLowerCase()] ?? null
  if (d && g) return `${d}_${g}_rank`
  if (d) return `${d}_rank`
  return null
}

const COLS_BEFORE_RUNNER = [
  { key: 'overall_race_rank', label: 'Overall', type: 'rank' },
  // dynamic division rank column inserted here at runtime
]

const COLS_AFTER_RUNNER = [
  { key: 'runner',         label: 'Runner' },
  { key: 'gender',         label: 'Gender',      type: 'gender' },
  { key: 'age',            label: 'Age' },
  { key: 'team',           label: 'Team' },
  { key: 'division',       label: 'Division',    type: 'division' },
  { key: 'time',           label: 'Time',        type: 'time' },
  { key: 'age_grade',      label: 'Age Grade' },
  { key: 'age_grade_rank', label: 'AG Rank',     type: 'rank' },
  { key: 'open_rank',      label: 'Open Rank',   type: 'rank' },
  { key: 'gender_rank',    label: 'Gender Rank', type: 'rank' },
  { key: 'event_name',     label: 'Event' },
]

/**
 * Division filter checks eligibility (a 55-yr-old IS a Masters runner too).
 */
function matchesDivision(row, divFilter) {
  if (!divFilter) return true
  const age = Number(row.age)
  if (isNaN(age)) return false
  switch (divFilter) {
    case 'Open':          return age >= 16
    case 'Masters':       return age >= 40
    case 'Grandmasters':  return age >= 50
    case 'Seniors':       return age >= 60
    case 'Veteran':       return age >= 70
    default:              return true
  }
}

export default function Individual() {
  const { data, loading, error, reload }               = useData(fetchIndividual)
  const { data: pointsData, loading: pointsLoading }   = useData(fetchIndividualPoints)

  // --- standings filters ---
  const [filters, setFilters] = useState({})
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))

  // --- points grid filters / search / expand ---
  const [pFilters, setPFilters] = useState({})
  const [pSearch,  setPSearch]  = useState('')
  const [expanded, setExpanded] = useState(false)
  const setPFilter = (key, value) => setPFilters(f => ({ ...f, [key]: value }))

  const filteredPoints = useMemo(() => {
    const q = pSearch.trim().toLowerCase()
    return pointsData.filter(row => {
      if (pFilters.event_name && row.event_name !== pFilters.event_name) return false
      if (pFilters.division  && String(row.division).toLowerCase() !== String(pFilters.division).toLowerCase()) return false
      if (pFilters.gender    && String(row.gender).toLowerCase()   !== String(pFilters.gender).toLowerCase())   return false
      if (pFilters.team      && row.team !== pFilters.team) return false
      if (q) {
        const hay = [row.runner, row.team, row.event_name, row.division].join(' ').toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [pointsData, pFilters, pSearch])

  const filteredPointsVisible = expanded
    ? filteredPoints
    : filteredPoints.slice(0, POINTS_EXPAND_LIMIT)

  const filtered = useMemo(() => {
    return data.filter(row => {
      if (filters.event_name && row.event_name !== filters.event_name) return false
      if (!matchesDivision(row, filters.division)) return false
      if (filters.gender &&
          String(row.gender).toLowerCase() !== String(filters.gender).toLowerCase()) return false
      if (filters.team && row.team !== filters.team) return false
      return true
    })
  }, [data, filters])

  const columns = useMemo(() => {
    const key = getDivRankKey(filters.division, filters.gender)
    const divCol = key ? [{ key, label: DIV_RANK_META[key] ?? key, type: 'rank' }] : []
    return [...COLS_BEFORE_RUNNER, ...divCol, ...COLS_AFTER_RUNNER]
  }, [filters.division, filters.gender])

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="font-display font-extrabold text-4xl text-brand-navy tracking-wide uppercase">
          Individual Standings
        </h1>
        <p className="text-brand-muted mt-1">
          Per-runner standings with age grade and division ranks.
          Division filter shows all runners eligible for that age group.
        </p>
      </div>

      {/* ── Individual Points grid ── */}
      <div className="card mb-8">
        <h2 className="section-header text-xl mb-4">Individual Points</h2>

        {pointsLoading && <Spinner message="Loading points…" />}

        {!pointsLoading && (
          <>
            <FilterBar
              filters={POINTS_FILTER_DEFS}
              values={pFilters}
              onChange={setPFilter}
              searchValue={pSearch}
              onSearch={setPSearch}
              data={pointsData}
            />

            <DataGrid
              data={filteredPointsVisible}
              columns={POINTS_COLUMNS}
              rowCount={filteredPoints.length}
            />

            {filteredPoints.length > POINTS_EXPAND_LIMIT && (
              <button
                onClick={() => setExpanded(e => !e)}
                className="mt-3 flex items-center gap-1.5 text-sm font-semibold text-brand-blue
                           hover:text-brand-navy transition-colors mx-auto"
              >
                {expanded
                  ? <><ChevronUp className="w-4 h-4" /> Show less</>
                  : <><ChevronDown className="w-4 h-4" /> Show all {filteredPoints.length} rows</>
                }
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Full Standings grid ── */}
      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {!loading && !error && (
        <>
          <h2 className="section-header text-xl mb-4">Race Standings</h2>
          <FilterBar
            filters={FILTER_DEFS}
            values={filters}
            onChange={setFilter}
            data={data}
          />
          <DataGrid data={filtered} columns={columns} rowCount={data.length} />
        </>
      )}
    </div>
  )
}
