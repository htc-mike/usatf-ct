import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useData } from '../hooks/useData'
import { fetchResults } from '../services/api'
import FilterBar from '../components/FilterBar'
import DataGrid from '../components/DataGrid'
import { Spinner, ErrorState } from '../components/LoadingState'

const FILTER_DEFS = [
  { key: 'event_name', label: 'Event' },
  { key: 'division',   label: 'Division' },
  { key: 'sex',        label: 'Gender' },
  { key: 'team',       label: 'Team' },
]

const COLUMNS = [
  { key: 'place',      label: 'Place',   type: 'rank' },
  { key: 'name',       label: 'Name' },
  { key: 'sex',        label: 'Gender',  type: 'gender' },
  { key: 'age',        label: 'Age' },
  { key: 'time',       label: 'Time',    type: 'time' },
  { key: 'pace',       label: 'Pace/mi', type: 'time' },
  { key: 'team',       label: 'Team' },
  { key: 'division',   label: 'Division', type: 'division' },
  { key: 'event_name', label: 'Event' },
]

export default function Results() {
  const { data, loading, error, reload } = useData(fetchResults)
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState(() => {
    const event = searchParams.get('event')
    return event ? { event_name: event } : {}
  })
  const [search, setSearch] = useState('')

  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return data.filter(row => {
      if (filters.event_name && row.event_name !== filters.event_name) return false
      if (filters.division  && String(row.division).toLowerCase() !== String(filters.division).toLowerCase()) return false
      if (filters.sex       && String(row.sex).toLowerCase()      !== String(filters.sex).toLowerCase())      return false
      if (filters.team      && row.team !== filters.team) return false
      if (q) {
        const haystack = [row.name, row.team, row.event_name, row.division]
          .join(' ').toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [data, filters, search])

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="font-display font-extrabold text-4xl text-brand-navy tracking-wide uppercase">
          Race Results
        </h1>
        <p className="text-brand-muted mt-1">
          Full finisher results for each Grand Prix event.
        </p>
      </div>

      {loading && <Spinner />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {!loading && !error && (
        <>
          <FilterBar
            filters={FILTER_DEFS}
            values={filters}
            onChange={setFilter}
            searchValue={search}
            onSearch={setSearch}
            data={data}
          />
          <DataGrid data={filtered} columns={COLUMNS} rowCount={data.length} />
        </>
      )}
    </div>
  )
}
