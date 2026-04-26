import { createContext, useContext, useEffect, useState } from 'react'

const SessionContext = createContext(null)

export function SessionProvider({ children }) {
  const [session, setSession] = useState(null)

  useEffect(() => {
    fetch('/api/me')
      .then(res => res.json())
      .then(setSession)
      .catch(() => setSession({ logged_in: false }))
  }, [])

  return (
    <SessionContext.Provider value={session}>
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  return useContext(SessionContext)
}
