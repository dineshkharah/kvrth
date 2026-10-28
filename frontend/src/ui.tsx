import type { ReactNode } from 'react'

export function Panel({
  title,
  note,
  children,
}: {
  title: string
  note?: string
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-5">
      <h2 className="text-sm font-semibold tracking-wide text-[var(--text-primary)]">{title}</h2>
      {note && <p className="mt-1 text-sm text-[var(--text-secondary)]">{note}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function StatTile({
  label,
  value,
  note,
  accent,
}: {
  label: string
  value: string
  note?: string
  accent?: string
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] p-4">
      <div className="flex items-center gap-2">
        {accent && (
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: accent }} aria-hidden />
        )}
        <span className="text-xs uppercase tracking-wide text-[var(--text-muted)]">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      {note && <div className="mt-1 text-xs text-[var(--text-secondary)]">{note}</div>}
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-[var(--text-muted)]">{label}</span>
      {children}
    </label>
  )
}

export function Select({
  value,
  onChange,
  children,
}: {
  value: string
  onChange: (value: string) => void
  children: ReactNode
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] px-3 py-2 text-sm"
    >
      {children}
    </select>
  )
}

export function Loading({ what }: { what: string }) {
  return <p className="text-sm text-[var(--text-secondary)]">Loading {what}...</p>
}

export function Failed({ error }: { error: string }) {
  return (
    <p className="rounded-md border border-[var(--border)] bg-[var(--surface-2)] p-4 text-sm">
      Could not reach the API. {error}
    </p>
  )
}
