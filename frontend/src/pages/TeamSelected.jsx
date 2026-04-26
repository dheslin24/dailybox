import { useSearchParams } from 'react-router-dom'

export default function TeamSelected() {
  const [searchParams] = useSearchParams()
  const team = searchParams.get('team')
  const logo = searchParams.get('logo')
  const week = searchParams.get('week')

  return (
    <div style={{position:'absolute', top:'32px', right:'48px', background:'#fff', padding:'18px 32px', borderRadius:'8px', boxShadow:'0 2px 8px rgba(0,0,0,0.10)', textAlign:'center'}}>
      <div style={{fontSize:'1.2em', fontWeight:'bold', marginBottom:'10px'}}>Team selected for week {week}</div>
      <div>{team}</div>
      {logo && <img src={logo} alt={team} style={{height:'80px', marginTop:'8px'}} />}
    </div>
  )
}
