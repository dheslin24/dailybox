import { Routes, Route } from 'react-router-dom'
import UserDetails from './pages/UserDetails.jsx'
import Admin from './pages/Admin.jsx'
import AdminSummary from './pages/AdminSummary.jsx'
import MyGames from './pages/MyGames.jsx'
import GameList from './pages/GameList.jsx'
import CompletedGames from './pages/CompletedGames.jsx'
import PaymentStatus from './pages/PaymentStatus.jsx'
import CustomGameList from './pages/CustomGameList.jsx'
import PrivateGameList from './pages/PrivateGameList.jsx'
import CurrentWinners from './pages/CurrentWinners.jsx'
import LandingPage from './pages/LandingPage.jsx'
import ResetPassword from './pages/ResetPassword.jsx'
import EmailUsers from './pages/EmailUsers.jsx'
import EndGame from './pages/EndGame.jsx'
import EnterCustomScores from './pages/EnterCustomScores.jsx'
import EnterEveryScore from './pages/EnterEveryScore.jsx'
import EsPayoutDetails from './pages/EsPayoutDetails.jsx'
import NcaabGames from './pages/NcaabGames.jsx'
import PrivatePswd from './pages/PrivatePswd.jsx'
import SvCreatePool from './pages/SvCreatePool.jsx'
import TeamSelected from './pages/TeamSelected.jsx'
import CreateAlias from './pages/CreateAlias.jsx'
import PickemAdmin from './pages/PickemAdmin.jsx'
import PickemGameList from './pages/PickemGameList.jsx'
import PickemRules from './pages/PickemRules.jsx'
import PickemPaymentStatus from './pages/PickemPaymentStatus.jsx'
import EnterPickemScores from './pages/EnterPickemScores.jsx'
import BowlPaymentStatus from './pages/BowlPaymentStatus.jsx'
import PickemAllPicks from './pages/PickemAllPicks.jsx'
import SurvivorPool from './pages/SurvivorPool.jsx'
import SurvivorTeamsSelected from './pages/SurvivorTeamsSelected.jsx'
import SurvivorWeekDisplay from './pages/SurvivorWeekDisplay.jsx'
import SurvivorPoolPicks from './pages/SurvivorPoolPicks.jsx'

function App() {
  return (
    <Routes>
      <Route path="/user_details" element={<UserDetails />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/admin_summary" element={<AdminSummary />} />
      <Route path="/my_games" element={<MyGames />} />
      <Route path="/game_list" element={<GameList />} />
      <Route path="/completed_games" element={<CompletedGames />} />
      <Route path="/payment_status" element={<PaymentStatus />} />
      <Route path="/custom_game_list" element={<CustomGameList />} />
      <Route path="/private_game_list" element={<PrivateGameList />} />
      <Route path="/current_winners/:boxid" element={<CurrentWinners />} />
      <Route path="/landing_page" element={<LandingPage />} />
      <Route path="/reset_password" element={<ResetPassword />} />
      <Route path="/email_users" element={<EmailUsers />} />
      <Route path="/end_game" element={<EndGame />} />
      <Route path="/enter_custom_scores" element={<EnterCustomScores />} />
      <Route path="/enter_every_score" element={<EnterEveryScore />} />
      <Route path="/es_payout_details" element={<EsPayoutDetails />} />
      <Route path="/ncaab_games" element={<NcaabGames />} />
      <Route path="/private_pswd" element={<PrivatePswd />} />
      <Route path="/sv_create_pool" element={<SvCreatePool />} />
      <Route path="/team_selected" element={<TeamSelected />} />
      <Route path="/create_alias" element={<CreateAlias />} />
      <Route path="/pickem_admin" element={<PickemAdmin />} />
      <Route path="/pickem_game_list" element={<PickemGameList />} />
      <Route path="/pickem_rules" element={<PickemRules />} />
      <Route path="/pickem_payment_status" element={<PickemPaymentStatus />} />
      <Route path="/enter_pickem_scores" element={<EnterPickemScores />} />
      <Route path="/bowl_payment_status" element={<BowlPaymentStatus />} />
      <Route path="/pickem_all_picks" element={<PickemAllPicks />} />
      <Route path="/survivor_pool" element={<SurvivorPool />} />
      <Route path="/survivor_teams_selected" element={<SurvivorTeamsSelected />} />
      <Route path="/survivor_week_display" element={<SurvivorWeekDisplay />} />
      <Route path="/survivor_pool_picks" element={<SurvivorPoolPicks />} />
    </Routes>
  )
}

export default App
