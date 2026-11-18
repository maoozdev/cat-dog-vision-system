import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

/** Page frame for logged-in pages: navbar on top, the current page below. */
export default function Layout() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Outlet />
      </main>
    </>
  )
}
