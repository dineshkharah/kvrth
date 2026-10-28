import { useState } from 'react'

import AccuracyView from './AccuracyView'
import DecisionView from './DecisionView'

const TABS = [
  { id: 'decision', label: 'Decision support' },
  { id: 'accuracy', label: 'Forecast accuracy' },
] as const

type Tab = (typeof TABS)[number]['id']

export default function App() {
  const [tab, setTab] = useState<Tab>('decision')

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header>
        <h1 className="text-2xl font-semibold">Windsight</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          GB wind generation as the day ahead desk saw it. January 2026 pilot.
        </p>
      </header>

      <nav className="mt-6 flex gap-1 border-b border-[var(--border)]">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={
              tab === item.id
                ? 'border-b-2 border-[var(--delivered)] px-4 py-2 text-sm font-medium'
                : 'border-b-2 border-transparent px-4 py-2 text-sm text-[var(--text-secondary)]'
            }
          >
            {item.label}
          </button>
        ))}
      </nav>

      <main className="mt-6">
        {tab === 'decision' ? <DecisionView /> : <AccuracyView />}
      </main>

      <footer className="mt-10 border-t border-[var(--border)] pt-4 text-xs text-[var(--text-muted)]">
        Data from Elexon BMRS, datasets FUELHH and WINDFOR. Error is forecast minus delivered, so a
        positive number means the forecast ran high and too little thermal power was bought.
      </footer>
    </div>
  )
}
