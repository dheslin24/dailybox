import Layout from '../components/Layout'

export default function EmailUsers() {
  return (
    <Layout>
      <form action="/send_bygemail" method="POST">
        <label>Send E-Mail to Userid: <input type="text" name="userid" size="10" /></label>
        <label> Recipient <input type="email" name="rcpt" /></label>
        <label> Subject <input type="text" name="subject" size="100" /></label>
        <label> Body <textarea name="body" cols="100" rows="5" /></label>
        <input type="submit" value="Send" />
      </form>
    </Layout>
  )
}
