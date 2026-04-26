import Layout from '../components/Layout'

export default function EnterCustomScores() {
  return (
    <Layout>
      <form action="/enter_custom_scores" method="post">
        <fieldset>
          <div className="form-group">
            <input autoComplete="off" autoFocus className="form-control" name="boxid" placeholder="boxid" type="text" size="5" /><br />
            <input className="form-control" name="x1" placeholder="x1 qtr" type="text" size="5" />
            <input className="form-control" name="y1" placeholder="y1 qtr" type="text" size="5" /><br />
            <input className="form-control" name="x2" placeholder="x2 qtr" type="text" size="5" />
            <input className="form-control" name="y2" placeholder="y2 qtr" type="text" size="5" /><br />
            <input className="form-control" name="x3" placeholder="x3 qtr" type="text" size="5" />
            <input className="form-control" name="y3" placeholder="y3 qtr" type="text" size="5" /><br />
            <input className="form-control" name="x4" placeholder="x final" type="text" size="5" />
            <input className="form-control" name="y4" placeholder="y final" type="text" size="5" /><br />
            <button className="btn btn-default" type="submit">Submit</button>
          </div>
        </fieldset>
      </form>
    </Layout>
  )
}
