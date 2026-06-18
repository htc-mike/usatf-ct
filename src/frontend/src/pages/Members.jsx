import { useState, useMemo } from 'react'
import { useData } from '../hooks/useData'
import { fetchMembers } from '../services/api'
import FilterBar from '../components/FilterBar'
import DataGrid from '../components/DataGrid'
import { Spinner, ErrorState } from '../components/LoadingState'

const FILTER_DEFS = [
  { key: 'division', label: 'Division' },
  { key: 'sex',      label: 'Gender' },
  { key: 'team',     label: 'Team' },
]

const COLUMNS = [
  { key: 'last_name',          label: 'Last Name' },
  { key: 'first_name',         label: 'First Name' },
  { key: 'sex',                label: 'Gender',   type: 'gender' },
  { key: 'age',                label: 'Age' },
  { key: 'division',           label: 'Division', type: 'division' },
  { key: 'team',               label: 'Team' },
  { key: 'races_participated', label: 'Races' },
]

export default function Members() {
  const { data, loading, error, reload } = useData(fetchMembers)

  const [filters, setFilters] = useState({})
  const [search, setSearch]   = useState('')
  const setFilter = (key, value) => setFilters(f => ({ ...f, [key]: value }))

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return data.filter(row => {
      if (filters.division && String(row.division).toLowerCase() !== String(filters.division).toLowerCase()) return false
      if (filters.sex      && String(row.sex).toLowerCase()      !== String(filters.sex).toLowerCase())      return false
      if (filters.team     && row.team !== filters.team)  return false
      if (q) {
        const hay = [row.first_name, row.last_name, row.full_name, row.team, row.division]
          .join(' ')
          .toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
  }, [data, filters, search])

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="font-display font-extrabold text-4xl text-brand-navy tracking-wide uppercase">
          Members
        </h1>
        <p className="text-brand-muted mt-1">
          Registered Grand Prix members with team and division information.
        </p>
      </div>

      {loading && <Spinner message="Loading members…" />}
      {error   && <ErrorState message={error} onRetry={reload} />}

      {!loading && !error && (
        <div className="card">
          <FilterBar
            filters={FILTER_DEFS}
            values={filters}
            onChange={setFilter}
            searchValue={search}
            onSearch={setSearch}
            data={data}
          />
          <DataGrid
            data={filtered}
            columns={COLUMNS}
            rowCount={data.length}
          />
        </div>
      )}
    </div>
  )
}
