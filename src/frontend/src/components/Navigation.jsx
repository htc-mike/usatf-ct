import { useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Menu, X } from 'lucide-react'

const LOGO_URL = `${import.meta.env.BASE_URL}usatf-ct-logo.png`

const links = [
  { to: '/',           label: 'Home' },
  { to: '/team',       label: 'Team' },
  { to: '/individual', label: 'Individual' },
  { to: '/results',    label: 'Results' },
]

function NavItem({ to, label, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      end={to === '/'}
      className={({ isActive }) =>
        [
          'font-display font-semibold tracking-wider uppercase text-sm transition-colors px-3 py-1.5 rounded-md',
          isActive
            ? 'bg-white/20 text-white'
            : 'text-blue-100 hover:text-white hover:bg-white/10',
        ].join(' ')
      }
    >
      {label}
    </NavLink>
  )
}

export default function Navigation() {
  const [open, setOpen] = useState(false)

  return (
    <nav className="bg-brand-navy shadow-lg sticky top-0 z-50">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3 shrink-0">
            <img
              src={LOGO_URL}
              alt="USATF-CT"
              className="h-8 w-auto object-contain"
              style={{ filter: 'brightness(0) invert(1)' }}
            />
            <div className="hidden sm:block w-px h-5 bg-white/25 self-center" />
            <span className="hidden sm:block font-display font-semibold text-blue-300
                             text-xs tracking-widest uppercase">
              Grand Prix
            </span>
          </Link>

          {/* Desktop nav */}
          <div className="hidden sm:flex items-center gap-1">
            {links.map(l => (
              <NavItem key={l.to} to={l.to} label={l.label} />
            ))}
          </div>

          {/* Mobile toggle */}
          <button
            className="sm:hidden text-white p-1.5 rounded-md hover:bg-white/10 transition-colors"
            onClick={() => setOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="sm:hidden bg-brand-navy/95 border-t border-white/10 px-4 pb-4 pt-2 flex flex-col gap-1">
          {links.map(l => (
            <NavItem key={l.to} to={l.to} label={l.label} onClick={() => setOpen(false)} />
          ))}
        </div>
      )}
    </nav>
  )
}
