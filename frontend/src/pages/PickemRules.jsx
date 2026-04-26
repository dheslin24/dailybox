import Layout from '../components/Layout'

const PAST_WINNERS = [
  ['2010/11', 'Rob Cannella'],
  ['2011/12', 'Jin Kye / Chris Greenfield'],
  ['2012/13', 'Kevin Murphy'],
  ['2013/14', 'Orlando Ferguson'],
  ['2014/15', 'Rob Gorozdi / Dan Heslin'],
  ['2015/16', 'Harrison Katz'],
  ['2016/17', 'Orlando Furguson'],
  ['2017/18', 'Matt Mignone'],
  ['2018/19', 'Gerard Grecco'],
  ['2019/20', 'Nick Laveglia'],
  ['2020/21', 'Carlos Santiago'],
  ['2021/22', 'Gerard Grecco'],
  ['2022/23', 'Carlos Santiago'],
  ['2023/24', 'Brent Uttz'],
  ['2024/25', 'Brian Jakubowski'],
  ['2025/26', 'Gerard Grecco'],
]

export default function PickemRules() {
  return (
    <Layout>
      <h1><p>Rules and Past Winners</p></h1>
      <h4>
        <p>
          The Holy Grail of gambling is going <del>11-0</del> 13-0 in the NFL playoffs. Can you do it?<br />
          None of these past winners below have come within even 3 games of it.
        </p>
      </h4>
      <h4>
        <table align="center" cellPadding="10">
          <thead>
            <tr><th>Year</th><th>Winner</th></tr>
          </thead>
          <tbody>
            {PAST_WINNERS.map(([year, winner]) => (
              <tr key={year}><td>{year}</td><td>{winner}</td></tr>
            ))}
          </tbody>
        </table>
        <br />
      </h4>
      <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTIivcmI8dJ5R7q4RXPu_y1su3xFo_73cjnWQ&usqp=CAU" alt="" />
      <br />
      <h2>Rules</h2>
      <div className="rules">
        <p><del>Pool is limited to 40 people</del> No longer limited.</p>
        <p>Pick each team versus spread, most correct throughout entire playoffs takes all</p>
        <p>Lines lock 1 hour prior to scheduled kickoff</p>
        <p>To prevent pushes, if even number spread in Super Bowl .5 will be added to the favorite</p>
        <p>If Super Bowl line is 'pickem' the 'home' team will be a .5 favorite</p>
        <p>Tie breaker will be the Superbowl overall point total. Closest to overall score wins (NOT "price is right" rules)</p>
        <p>Detailed tie break scenarios will be sent out the week before the Superbowl (the site auto-calculates the winner)</p>
        <p>If you do not enter picks prior to scheduled kickoff, the site locks and you will not accumulate wins for that game, sorry (but not sorry)</p>
        <p>Entry is 50</p>
      </div>
    </Layout>
  )
}
