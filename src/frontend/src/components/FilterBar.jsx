import { useMemo } from 'react'
import { Search, X } from 'lucide-react'

/**
 * FilterBar — renders dropdowns for each filter key + optional search input.
 *
 * @param {object[]} filters      e.g. [{ key: 'event_name', label: 'Event' }, ...]
 * @param {object}   values       current filter values keyed by filter.key
 * @param {function} onChange     (key, value) => void
 * @param {string}   searchValue  current search text (pass null to hide search)
 * @param {function} onSearch     (value) => void
 * @param {any[]}    data         full dataset — used to derive unique options per key
 */
export default function FilterBar({
  filters = [],
  values = {},
  onChange,
  searchValue,
  onSearch,
  data = [],
}) {
  const options = useMemo(() => {
    const out = {}
    for (const f of filters) {
      const unique = [...new Set(
        data
          .map(row => row[f.key])
          .filter(v => v !== '' && v !== null && v !== undefined)
      )].sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true }))
      out[f.key] = unique
    }
    return out
  }, [data, filters])

  const hasActiveFilters = filters.some(f => values[f.key]) || (searchValue !== null && searchValue !== undefined && searchValue !== '')

  const clearAll = () => {
    filters.forEach(f => onChange(f.key, ''))
    if (onSearch) onSearch('')
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      {/* Search bar */}
      {onSearch !== undefined && (
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search…"
            value={searchValue ?? ''}
            onChange={e => onSearch(e.target.value)}
            className="search-input w-44 sm:w-56"
          />
        </div>
      )}

      {/* Filter dropdowns */}
      {filters.map(f => (
        <select
          key={f.key}
          value={values[f.key] ?? ''}
          onChange={e => onChange(f.key, e.target.value)}
          className="filter-select"
        >
          <option value="">All {f.label}s</option>
          {(options[f.key] ?? []).map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ))}

      {/* Clear all */}
      {hasActiveFilters && (
        <button
          onClick={clearAll}
          className="flex items-center gap-1 text-xs text-brand-muted hover:text-brand-navy
                     px-2.5 py-2 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
          Clear
        </button>
      )}
    </div>
  )
}
