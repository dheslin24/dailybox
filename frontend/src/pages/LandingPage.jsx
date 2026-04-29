import Layout from '../components/Layout'

export default function LandingPage() {
  return (
    <Layout>
      <h1><p>Choose Your Game</p></h1>
      <table align="center" cellPadding="10">
        <tbody>
          <tr>
            <td className="landing" style={{textAlign:'center', cursor:'pointer'}} onClick={() => window.location.href = '/app/view_all_picks'}>
              <img src="https://www.wmse.org/wp-content/uploads/2017/12/ralph.gif" style={{display:'block', width:'90%', height:'auto', margin:'auto'}} alt="" />
              <br />PLAYOFF PICKEM
            </td>
            <td className="landing" style={{textAlign:'center', cursor:'pointer'}} onClick={() => window.location.href = '/app/custom_game_list'}>
              <img src="https://c.tenor.com/LuMmZd2WpjcAAAAC/super-bowl-simpsons.gif" style={{display:'block', width:'120%', height:'60%'}} alt="" />
              <br /><br /><br /><br />Click Here for Super Bowl Boxes
            </td>
          </tr>
          <tr style={{background:'#fff'}}>
            <td colSpan="2" style={{textAlign:'center', cursor:'pointer', padding:'24px 0', background:'#fff'}} onClick={() => window.location.href = '/app/survivor_pool'}>
              <img src="/static/simpsons_survivor.png" alt="Survivor Pools" style={{display:'block', margin:'auto', width:'90%', maxWidth:'900px', height:'auto', borderRadius:'8px'}} />
              <div style={{fontSize:'1.5em', fontWeight:'bold', marginTop:'12px'}}>Survivor Pools</div>
            </td>
          </tr>
          <tr style={{background:'#fff'}}>
            <td colSpan="2" style={{textAlign:'center', cursor:'pointer', padding:'24px 0', background:'#fff'}} onClick={() => window.location.href = '/app/horse_racing'}>
              <img src="/static/simpsons_horse.gif" alt="Derby Pool" style={{display:'block', margin:'auto', width:'90%', maxWidth:'900px', height:'auto', borderRadius:'8px'}} />
              <div style={{fontSize:'1.5em', fontWeight:'bold', marginTop:'12px'}}>Kentucky Derby Pool</div>
            </td>
          </tr>
          <tr>
            <td className="landing" style={{textAlign:'center', cursor:'pointer'}} onClick={() => window.location.href = '/app/private_pswd'}>
              <img src="https://pbs.twimg.com/media/ECkwxxLX4AE_btl.jpg" style={{display:'block', width:'auto', height:'auto', margin:'auto'}} alt="" />
              <br />Register for Private Event<br />(password required)
            </td>
            <td className="landing" style={{textAlign:'center', cursor:'pointer'}} onClick={() => window.location.href = '/app/private_game_list'}>
              <img src="https://static.simpsonswiki.com/images/9/98/Flaming_Moe%27s_%28location%29.png" style={{display:'block', width:'auto', height:'70%', margin:'auto'}} alt="" />
              <br />Access Your Existing Private Events
            </td>
          </tr>
        </tbody>
      </table>
    </Layout>
  )
}
