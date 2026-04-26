import Layout from '../components/Layout'

export default function EndGame() {
  return (
    <Layout>
      <p>This will end the game. Are you sure you want to do this? It will add reverse and final scores to grid and be done</p>
      <form action="/end_game" method="post">
        <fieldset>
          <div className="form-group">
            <input autoComplete="off" autoFocus className="form-control" name="boxid" placeholder="boxid" type="text" size="5" /><br />
            <input className="form-control" name="home" placeholder="TB Final" type="text" size="10" />
            <input className="form-control" name="away" placeholder="KC Final" type="text" size="10" /><br />
            <button className="btn btn-default" type="submit">End Game</button>
          </div>
        </fieldset>
      </form>
      <h4><p>OR - click here to end all games automatically</p></h4>
      <form action="/end_games" method="POST">
        <button className="btn btn-default" type="submit">End ALL ES Games</button>
      </form>
    </Layout>
  )
}
