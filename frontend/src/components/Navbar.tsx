import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/predict', label: 'Predict' },
  { to: '/history', label: 'History' },
  { to: '/profile', label: 'Profile' },
]

export default function Navbar() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false) // mobile menu
  const close = () => setOpen(false)

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/dashboard" className="brand" onClick={close}>
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span>PawSense</span>
        </Link>

        <button
          className="menu-toggle"
          aria-label="Toggle menu"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={`nav-links ${open ? 'open' : ''}`}>
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-user" title={user?.email}>
            {user?.email}
          </span>
          <NavLink to="/logout" className="nav-logout" onClick={close}>
            Log out
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
