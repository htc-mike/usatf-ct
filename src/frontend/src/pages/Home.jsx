import { Link } from 'react-router-dom'
import { Users, User, Flag, ChevronRight, Trophy } from 'lucide-react'
import { useData } from '../hooks/useData'
import { fetchEvents, fetchTeamTotals, fetchIndividualSeasonTotals } from '../services/api'
import { Spinner, ErrorState } from '../components/LoadingState'
import DataGrid from '../components/DataGrid'

const LOGO_URL = `${import.meta.env.BASE_URL}usatf-ct-logo.png`

const EVENT_COLUMNS = [
  { key: 'date',     label: 'Date' },
  { key: 'name',     label: 'Event',    type: 'link', hrefKey: 'url' },
  { key: 'location', label: 'Location' },
  { key: 'dist_mi',  label: 'Distance' },
  { key: 'status',   label: 'Status', type: 'routerLink', hrefKey: 'results_path' },
]

const sections = [
  {
    to: '/team',
    icon: Users,
    label: 'Team',
    description: 'Team standings, scoring members, and points by event, division, and gender.',
    accent: 'from-brand-navy to-brand-blue',
    badge: 'bg-blue-100 text-brand-blue',
  },
  {
    to: '/individual',
    icon: User,
    label: 'Individual',
    description: 'Per-runner standings with age grade, division ranks, and overall placement.',
    accent: 'from-purple-800 to-purple-600',
    badge: 'bg-purple-100 text-purple-700',
  },
  {
    to: '/results',
    icon: Flag,
    label: 'Results',
    description: 'Full race results for every Grand Prix event. Searchable and filterable.',
    accent: 'from-emerald-800 to-emerald-600',
    badge: 'bg-emerald-100 text-emerald-700',
  },
]

function SectionCard({ to, icon: Icon, label, description, accent, badge }) {
  return (
    <Link
      to={to}
      className="group relative bg-white rounded-2xl border border-gray-100 shadow-sm
                 hover:shadow-md transition-all duration-200 overflow-hidden flex flex-col"
    >
      <div className={`h-2 w-full bg-gradient-to-r ${accent}`} />
      <div className="p-6 flex flex-col gap-3 flex-1">
        <div className={`${badge} self-start rounded-xl p-2.5`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-display text-xl font-bold text-brand-navy tracking-wide uppercase">
            {label}
          </h3>
          <p className="text-sm text-gray-500 mt-1 leading-relaxed">{description}</p>
        </div>
        <div className="mt-auto flex items-center gap-1 text-sm font-semibold text-brand-blue
                        group-hover:gap-2 transition-all">
          View {label}
          <ChevronRight className="w-4 h-4" />
        </div>
      </div>
    </Link>
  )
}

function EventRow({ event }) {
  const inner = (
    <div className={[
      'flex items-center justify-between py-2.5 border-b border-gray-50 last:border-0 group',
      event.has_results ? 'cursor-pointer hover:bg-gray-50 -mx-4 px-4 sm:-mx-6 sm:px-6 transition-colors rounded-lg' : '',
    ].join(' ')}>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-brand-navy/10 flex items-center justify-center shrink-0 group-hover:bg-brand-navy/20 transition-colors">
          <Calendar className="w-4 h-4 text-brand-navy" />
        </div>
        <div>
          <p className={[
            'font-semibold text-sm',
            event.has_results ? 'text-brand-blue group-hover:underline' : 'text-gray-800',
          ].join(' ')}>{event.name}</p>
          <p className="text-xs text-gray-400">{event.date}&nbsp;·&nbsp;{event.location}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 ml-4 shrink-0">
        <span className="text-xs text-gray-400 font-mono">
          {event.dist_mi ? `${event.dist_mi} mi` : ''}
        </span>
        {event.has_results
          ? <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700
                             bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3" />Results
            </span>
          : <span className="flex items-center gap-1 text-xs text-gray-300">
              <Clock className="w-3 h-3" />Pending
            </span>
        }
      </div>
    </div>
  )

  return event.has_results
    ? <Link to={`/results?event=${encodeURIComponent(event.name)}`}>{inner}</Link>
    : inner
}

function RankMark({ rank }) {
  if (rank === 1) return <span className="rank-badge rank-1">{rank}</span>
  if (rank === 2) return <span className="rank-badge rank-2">{rank}</span>
  if (rank === 3) return <span className="rank-badge rank-3">{rank}</span>
  return <span className="font-mono text-sm font-medium text-gray-500 w-7 text-center inline-block">{rank}</span>
}

function LeaderRow({ rank, team, points }) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
      <RankMark rank={rank} />
      <span className="flex-1 text-sm font-medium text-gray-800">{team}</span>
      <span className="font-mono text-sm font-semibold text-brand-blue">{points} pts</span>
    </div>
  )
}

function IndividualLeaderRow({ index, row }) {
  const rank = index + 1
  return (
    <div className="flex items-center gap-3 py-2 border-b border-gray-50 last:border-0">
      <RankMark rank={rank} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{row.runner}</p>
        <p className="text-xs text-gray-400">{row.division}&nbsp;·&nbsp;{row.team}</p>
      </div>
      <div className="text-right shrink-0">
        <span className="font-mono text-sm font-semibold text-brand-blue block">{row.total_points} pts</span>
        <span className="text-xs text-gray-400">{row.events} ev</span>
      </div>
    </div>
  )
}

export default function Home() {
  const { data: events, loading: eventsLoading, error: eventsError } = useData(fetchEvents)
  const { data: totals, loading: totalsLoading } = useData(fetchTeamTotals)
  const { data: indTotals, loading: indLoading } = useData(fetchIndividualSeasonTotals)

  const menTotals = indTotals.filter(r => r.gender === 'M')
  const womenTotals = indTotals.filter(r => r.gender === 'F')

  return (
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-br from-brand-navy via-brand-navy to-brand-blue text-white">
        <div className="max-w-screen-xl mx-auto px-4 sm:px-6 py-7 sm:py-9">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 sm:gap-8">

            {/* Logo */}
            <img
              src={LOGO_URL}
              alt="USATF-CT"
              className="h-14 sm:h-16 w-auto object-contain shrink-0"
              style={{ filter: 'brightness(0) invert(1)' }}
            />

            {/* Vertical divider — desktop only */}
            <div className="hidden sm:block w-px self-stretch bg-white/20" />

            {/* Text block */}
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Trophy className="w-4 h-4 text-brand-gold" />
                <span className="font-display font-semibold tracking-widest uppercase text-blue-300 text-xs">
                  2026 Season
                </span>
              </div>
              <h1 className="font-display font-extrabold text-4xl sm:text-5xl tracking-wide uppercase leading-none mb-2">
                <span className="text-brand-gold">Grand Prix</span>
              </h1>
              <p className="text-blue-200 text-sm sm:text-base leading-relaxed max-w-lg">
                Connecticut's premier road racing series — team and individual
                standings across Open, Masters, Grandmasters, and Seniors divisions.
              </p>
            </div>

          </div>
        </div>
      </div>

      <div className="page-container">
        {/* Navigation cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">
          {sections.map(s => <SectionCard key={s.to} {...s} />)}
        </div>

        {/* Season leaders — 3 columns */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">

          {/* Team */}
          <div className="card">
            <h2 className="section-header text-lg mb-4">Team</h2>
            {totalsLoading && <Spinner message="Loading…" />}
            {!totalsLoading && totals.length === 0 && (
              <p className="text-sm text-gray-400">No standings data yet.</p>
            )}
            {totals.slice(0, 10).map((row, i) => (
              <LeaderRow key={i} rank={row.team_rank ?? i + 1} team={row.team} points={row.total_points} />
            ))}
          </div>

          {/* Individual Men */}
          <div className="card">
            <h2 className="section-header text-lg mb-4">Individual — Men</h2>
            {indLoading && <Spinner message="Loading…" />}
            {!indLoading && menTotals.length === 0 && (
              <p className="text-sm text-gray-400">No standings data yet.</p>
            )}
            {menTotals.slice(0, 10).map((row, i) => (
              <IndividualLeaderRow key={i} index={i} row={row} />
            ))}
          </div>

          {/* Individual Women */}
          <div className="card">
            <h2 className="section-header text-lg mb-4">Individual — Women</h2>
            {indLoading && <Spinner message="Loading…" />}
            {!indLoading && womenTotals.length === 0 && (
              <p className="text-sm text-gray-400">No standings data yet.</p>
            )}
            {womenTotals.slice(0, 10).map((row, i) => (
              <IndividualLeaderRow key={i} index={i} row={row} />
            ))}
          </div>

        </div>

        {/* Events — full width */}
        <div className="card">
          <h2 className="section-header text-xl mb-4">Events</h2>
          {eventsLoading && <Spinner message="Loading events…" />}
          {eventsError && <ErrorState message={eventsError} />}
          {!eventsLoading && !eventsError && (
            <DataGrid
              data={[...events]
                .sort((a, b) => (a.date ?? '').localeCompare(b.date ?? ''))
                .map(ev => ({ ...ev, dist_mi: ev.dist_mi ? `${ev.dist_mi} mi` : '', status: ev.has_results ? 'Results' : 'Pending', results_path: ev.has_results ? `/results?event=${encodeURIComponent(ev.name)}` : null }))}
              columns={EVENT_COLUMNS}
            />
          )}
        </div>

      </div>
    </div>
  )
}
