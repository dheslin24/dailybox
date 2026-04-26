import { Routes, Route } from 'react-router-dom'
import UserDetails from './pages/UserDetails.jsx'
import Admin from './pages/Admin.jsx'

function App() {
  return (
    <Routes>
      <Route path="/user_details" element={<UserDetails />} />
      <Route path="/admin" element={<Admin />} />
    </Routes>
  )
}

export default App
