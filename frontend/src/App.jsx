import { Routes, Route } from 'react-router-dom'
import UserDetails from './pages/UserDetails.jsx'
import Admin from './pages/Admin.jsx'
import MyGames from './pages/MyGames.jsx'
import GameList from './pages/GameList.jsx'
import CompletedGames from './pages/CompletedGames.jsx'
import PaymentStatus from './pages/PaymentStatus.jsx'
import CustomGameList from './pages/CustomGameList.jsx'
import PrivateGameList from './pages/PrivateGameList.jsx'
import CurrentWinners from './pages/CurrentWinners.jsx'
import LandingPage from './pages/LandingPage.jsx'
import ResetPassword from './pages/ResetPassword.jsx'

function App() {
  return (
    <Routes>
      <Route path="/user_details" element={<UserDetails />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/my_games" element={<MyGames />} />
      <Route path="/game_list" element={<GameList />} />
      <Route path="/completed_games" element={<CompletedGames />} />
      <Route path="/payment_status" element={<PaymentStatus />} />
      <Route path="/custom_game_list" element={<CustomGameList />} />
      <Route path="/private_game_list" element={<PrivateGameList />} />
      <Route path="/current_winners/:boxid" element={<CurrentWinners />} />
      <Route path="/landing_page" element={<LandingPage />} />
      <Route path="/reset_password" element={<ResetPassword />} />
    </Routes>
  )
}

export default App
