import { Routes, Route } from 'react-router-dom'
import UserDetails from './pages/UserDetails.jsx'
import Admin from './pages/Admin.jsx'
import MyGames from './pages/MyGames.jsx'
import GameList from './pages/GameList.jsx'
import CompletedGames from './pages/CompletedGames.jsx'
import PaymentStatus from './pages/PaymentStatus.jsx'

function App() {
  return (
    <Routes>
      <Route path="/user_details" element={<UserDetails />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/my_games" element={<MyGames />} />
      <Route path="/game_list" element={<GameList />} />
      <Route path="/completed_games" element={<CompletedGames />} />
      <Route path="/payment_status" element={<PaymentStatus />} />
    </Routes>
  )
}

export default App
