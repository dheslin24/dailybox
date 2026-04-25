import { Routes, Route } from 'react-router-dom'
import UserDetails from './pages/UserDetails.jsx'

function App() {
  return (
    <Routes>
      <Route path="/user_details" element={<UserDetails />} />
    </Routes>
  )
}

export default App
