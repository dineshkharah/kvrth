import { useEffect, useState } from 'react'

type DaySummary = {
  delivery_day: string
  forecast_mwh: number | null
  actual_mwh: number | null
  mae: number | null
}

function App() {
  const [days, setDays] = useState<DaySummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/days')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then(setDays)
      .catch((err: unknown) => setError(String(err)))
  }, [])

  return (
    <main>
      <h1>Windsight</h1>
      {!days && !error && <p>Loading January 2026...</p>}
      {error && <p>Backend unreachable: {error}</p>}
      {days && <p>{days.length} delivery days loaded</p>}
    </main>
  )
}

export default App
