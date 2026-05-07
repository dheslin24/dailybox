import Layout from '../components/Layout'

const CARDS = [
  {
    label: 'Playoff Pickem',
    href: '/app/view_all_picks',
    img: 'https://www.wmse.org/wp-content/uploads/2017/12/ralph.gif',
  },
  {
    label: 'Super Bowl Boxes',
    href: '/app/custom_game_list',
    img: 'https://c.tenor.com/LuMmZd2WpjcAAAAC/super-bowl-simpsons.gif',
  },
  {
    label: 'Survivor Pools',
    href: '/app/survivor_pool',
    img: '/static/simpsons_survivor.png',
    fit: 'contain',
  },
  {
    label: 'Triple Crown Horse Racing',
    href: '/app/horse_racing',
    img: '/static/simpsons_horse.gif',
  },
  {
    label: 'Golf Pools',
    href: '/app/golf_pool',
    img: '/static/homer_golf.gif',
  },
  {
    label: 'NCAA Hoops',
    href: '/app/ncaa_hoops',
    img: '/static/simpsons_globetrotters.webp',
  },
  {
    label: 'Register for Private Event',
    href: '/app/private_pswd',
    img: 'https://pbs.twimg.com/media/ECkwxxLX4AE_btl.jpg',
    sub: '(password required)',
  },
  {
    label: 'Access Existing Private Events',
    href: '/app/private_game_list',
    img: 'https://static.simpsonswiki.com/images/9/98/Flaming_Moe%27s_%28location%29.png',
  },
]

export default function LandingPage() {
  return (
    <Layout>
      <h1>Choose Your Game</h1>
      <div className="landing-grid">
        {CARDS.map(({ label, href, img, sub, fit }) => (
          <a key={href} href={href} className="landing-card">
            <div className="landing-card-img">
              <img src={img} alt={label} style={fit ? { objectFit: fit } : undefined} />
            </div>
            <div className="landing-card-label">
              {label}
              {sub && <div className="landing-card-sub">{sub}</div>}
            </div>
          </a>
        ))}
      </div>
    </Layout>
  )
}
