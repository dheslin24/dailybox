import { Navigate, Outlet } from 'react-router-dom'
import { useSession } from '../SessionContext'

export default function ProtectedRoute() {
  const session = useSession()
  if (session === null) return null
  if (!session.logged_in) return <Navigate to="/login" replace />
  return <Outlet />
}
