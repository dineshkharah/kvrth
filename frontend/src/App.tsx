import { useEffect, useState } from 'react'

type Health = {
  ok: boolean
  pandas: string
  rows: number
  first_generation_mw: number
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setHealth)
      .catch((err: unknown) => setError(String(err)))
  }, [])

  return (
    <main>
      <h1>Windsight</h1>
      {!health && !error && <p>Checking the backend...</p>}
      {error && <p>Backend unreachable: {error}</p>}
      {health && (
        <ul>
          <li>backend reachable: {String(health.ok)}</li>
          <li>pandas version: {health.pandas}</li>
          <li>rows read from the bundled csv: {health.rows}</li>
          <li>first generation value: {health.first_generation_mw} MW</li>
        </ul>
      )}
    </main>
  )
}

export default App
