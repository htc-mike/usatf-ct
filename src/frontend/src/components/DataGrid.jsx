import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, ChevronDown as ExpandIcon } from 'lucide-react'
import { EmptyState } from './LoadingState'

/**
 * Render a rank as a colored badge (gold/silver/bronze for 1-3).
 */
function RankBadge({ value }) {
  const n = Number(value)
  if (n === 1) return <span className="rank-badge rank-1">{value}</span>
  if (n === 2) return <span className="rank-badge rank-2">{value}</span>
  if (n === 3) return <span className="rank-badge rank-3">{value}</span>
  return <span className="font-mono text-sm font-medium text-gray-600">{value}</span>
}

/**
 * Division pill with colour coding.
 */
function DivisionPill({ value }) {
  const map = {
    open:         'division-open',
    masters:      'division-masters',
    grandmasters: 'division-grandmasters',
    seniors:      'division-seniors',
    veteran:      'division-veteran',
  }
  const key = String(value).toLowerCase()
  const cls = map[key] ?? 'pill bg-gray-100 text-gray-700'
  return <span className={cls}>{value}</span>
}

/**
 * Gender pill.
 */
function GenderPill({ value }) {
  const v = String(value).toLowerCase()
  if (v === 'm' || v === 'male')   return <span className="gender-m">M</span>
  if (v === 'f' || v === 'female') return <span className="gender-f">F</span>
  return <span>{value}</span>
}

/**
 * Cell renderer — picks display style based on column type.
 *
 * @param {'rank'|'division'|'gender'|'time'|'points'|'text'} type
 */
function Cell({ type, value }) {
  if (value === '' || value === null || value === undefined) {
    return <span className="text-gray-300">—</span>
  }
  switch (type) {
    case 'rank':     return <RankBadge value={value} />
    case 'division': return <DivisionPill value={value} />
    case 'gender':   return <GenderPill value={value} />
    case 'time':     return <span className="time-cell">{value}</span>
    case 'points':   return <span className="font-mono font-semibold text-brand-blue">{value}</span>
    default:         return <span>{String(value)}</span>
  }
}

function sortRows(rows, key, dir) {
  if (!key) return rows
  return [...rows].sort((a, b) => {
    const av = a[key], bv = b[key]
    const aEmpty = av === '' || av === null || av === undefined
    const bEmpty = bv === '' || bv === null || bv === undefined
    if (aEmpty && bEmpty) return 0
    if (aEmpty) return 1   // empties always last
    if (bEmpty) return -1
    const aNum = typeof av === 'number', bNum = typeof bv === 'number'
    let cmp
    if (aNum && bNum) {
      cmp = av - bv
    } else {
      cmp = String(av).toLowerCase().localeCompare(String(bv).toLowerCase())
    }
    return dir === 'desc' ? -cmp : cmp
  })
}

function SortIcon({ col, sortKey, sortDir }) {
  if (sortKey !== col) return <ChevronsUpDown className="w-3 h-3 opacity-30 shrink-0" />
  return sortDir === 'asc'
    ? <ChevronUp className="w-3 h-3 text-brand-gold shrink-0" />
    : <ChevronDown className="w-3 h-3 text-brand-gold shrink-0" />
}

/**
 * DataGrid
 *
 * @param {object[]} data       Filtered rows to display
 * @param {object[]} columns    [{ key, label, type? }]  type defaults to 'text'
 * @param {number}   rowCount   Total unfiltered row count (for display in header)
 * @param {number}   limit      Collapse to this many rows by default (null = show all)
 */
export default function DataGrid({ data = [], columns = [], rowCount, limit = null }) {
  const total = rowCount ?? data.length
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')
  const [expanded, setExpanded] = useState(false)

  function handleSort(key) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => sortRows(data, sortKey, sortDir), [data, sortKey, sortDir])
  const isLimited = limit !== null && !expanded && sorted.length > limit
  const displayRows = isLimited ? sorted.slice(0, limit) : sorted

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-brand-muted font-medium">
          {data.length.toLocaleString()}
          {total !== data.length ? ` of ${total.toLocaleString()}` : ''}
          {' '}row{data.length !== 1 ? 's' : ''}
        </span>
        {sortKey && (
          <button
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
            onClick={() => { setSortKey(null); setSortDir('asc') }}
          >
            Clear sort
          </button>
        )}
      </div>

      <div className="table-container">
        {data.length === 0 ? (
          <EmptyState />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="cursor-pointer select-none hover:bg-gray-100 transition-colors"
                  >
                    <span className="flex items-center gap-1">
                      {col.label}
                      <SortIcon col={col.key} sortKey={sortKey} sortDir={sortDir} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <td key={col.key}>
                      <Cell type={col.type ?? 'text'} value={row[col.key]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {limit !== null && sorted.length > limit && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="mt-2 flex items-center gap-1 text-xs font-medium text-brand-blue
                     hover:text-brand-navy transition-colors"
        >
          {expanded ? (
            <><ChevronUp className="w-3.5 h-3.5" /> Show less</>
          ) : (
            <><ChevronDown className="w-3.5 h-3.5" /> Show all {sorted.length.toLocaleString()} rows</>
          )}
        </button>
      )}
    </div>
  )
}
