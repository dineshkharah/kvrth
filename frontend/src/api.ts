import { useEffect, useState } from 'react'

export type Summary = {
  hours: number
  coverage: number
  mean_actual: number | null
  mean_forecast: number | null
  mae: number | null
  rmse: number | null
  rmse_over_mae: number | null
  bias: number | null
  wape: number | null
  p90_absolute_error: number | null
  p10_error: number | null
  p90_error: number | null
  mwh_exposure: number | null
}

export type DaySummary = {
  delivery_day: string
  forecast_mwh: number | null
  actual_mwh: number | null
  mae: number | null
  bias: number | null
  coverage: number
}

export type HourRow = {
  hour: string
  forecast: number | null
  actual: number | null
  error: number | null
  lead_hours: number
  published: string | null
}

export type Purchase = {
  forecast_mwh: number
  expected_mwh: number
  low_mwh: number
  high_mwh: number
  correction_factor: number
}

export type DayDetail = {
  delivery_day: string
  cutoff: string
  published: string | null
  hours: HourRow[]
  summary: Summary
  purchase: Purchase | null
}

export type HorizonBand = Summary & { band: string }
export type SweepRow = Summary & { label: string; cutoff: string }
export type HistogramBin = { from_mw: number; to_mw: number; hours: number }

export type Accuracy = {
  cutoff: string
  correction_factor: number
  raw: Summary
  corrected: Summary
  raw_by_horizon: HorizonBand[]
  corrected_by_horizon: HorizonBand[]
  histogram: HistogramBin[]
}

export const CUTOFFS = [
  { value: '07:30', label: '07:30, the last run before the gate' },
  { value: '09:20', label: '09:20, EPEX gate closure' },
  { value: '09:50', label: '09:50, N2EX gate closure' },
  { value: '11:30', label: '11:30, after the gate has shut' },
  { value: 'final', label: 'Final forecast, hindsight only' },
]

type Settled<T> = { path: string; data: T | null; error: string | null }

// loading is derived from whether the settled path matches the one asked for,
// so switching day or cutoff never shows the previous answer
export function useApi<T>(path: string) {
  const [settled, setSettled] = useState<Settled<T>>({ path: '', data: null, error: null })

  useEffect(() => {
    let cancelled = false

    fetch(path)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<T>
      })
      .then((data) => {
        if (!cancelled) setSettled({ path, data, error: null })
      })
      .catch((err: unknown) => {
        if (!cancelled) setSettled({ path, data: null, error: String(err) })
      })

    return () => {
      cancelled = true
    }
  }, [path])

  const current = settled.path === path
  return {
    data: current ? settled.data : null,
    error: current ? settled.error : null,
    loading: !current,
  }
}

export const mw = (value: number | null | undefined) =>
  value == null ? 'n/a' : `${Math.round(value).toLocaleString()} MW`

export const mwh = (value: number | null | undefined) =>
  value == null ? 'n/a' : `${Math.round(value).toLocaleString()} MWh`

export const pct = (value: number | null | undefined) =>
  value == null ? 'n/a' : `${(value * 100).toFixed(1)}%`

export const signed = (value: number | null | undefined) =>
  value == null ? 'n/a' : `${value >= 0 ? '+' : ''}${Math.round(value).toLocaleString()} MW`

export const ukDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })

export const ukTime = (iso: string) =>
  new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  })
