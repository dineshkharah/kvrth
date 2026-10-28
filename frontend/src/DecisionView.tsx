import { useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  CUTOFFS,
  type DayDetail,
  type DaySummary,
  mw,
  mwh,
  signed,
  ukDate,
  ukTime,
  useApi,
} from './api'
import { Failed, Field, Loading, Panel, Select, StatTile } from './ui'

const DELIVERED = '#2a78d6'
const FORECAST = '#eb6834'

export default function DecisionView() {
  const [cutoff, setCutoff] = useState('09:20')
  const [day, setDay] = useState('2026-01-15')

  const days = useApi<DaySummary[]>(`/api/days?cutoff=${cutoff}`)
  const detail = useApi<DayDetail>(`/api/days/${day}?cutoff=${cutoff}`)

  if (days.error) return <Failed error={days.error} />
  if (detail.error) return <Failed error={detail.error} />
  if (!days.data || !detail.data) return <Loading what="the delivery day" />

  const { hours, purchase, summary, published } = detail.data
  const points = hours.map((row) => ({
    label: ukTime(row.hour),
    forecast: row.forecast,
    delivered: row.actual,
    error: row.error,
  }))

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-4">
        <Field label="Delivery day">
          <Select value={day} onChange={setDay}>
            {days.data.map((row) => (
              <option key={row.delivery_day} value={row.delivery_day}>
                {ukDate(row.delivery_day)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Decision cutoff">
          <Select value={cutoff} onChange={setCutoff}>
            {CUTOFFS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <p className="rounded-lg border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3 text-sm">
        Showing only what was knowable at{' '}
        <strong>{cutoff === 'final' ? 'any time, including after delivery' : cutoff}</strong> on the
        day before delivery.{' '}
        {published ? (
          <>
            The newest forecast available then was published{' '}
            <strong>
              {ukDate(published)} at {ukTime(published)}
            </strong>
            .
          </>
        ) : (
          'No forecast had been published by this cutoff.'
        )}
      </p>

      {purchase && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Raw forecast"
            value={mwh(purchase.forecast_mwh)}
            note="what Elexon published, uncorrected"
            accent={FORECAST}
          />
          <StatTile
            label="Expected wind"
            value={mwh(purchase.expected_mwh)}
            note={`after scaling by ${purchase.correction_factor.toFixed(3)} for the known level gap`}
          />
          <StatTile
            label="Plan between"
            value={`${Math.round(purchase.low_mwh).toLocaleString()} and ${Math.round(purchase.high_mwh).toLocaleString()} MWh`}
            note="p10 to p90 band, buy thermal to cover the rest"
          />
          <StatTile
            label="Actually delivered"
            value={mwh(summary.mean_actual == null ? null : summary.mean_actual * hours.length)}
            note={`day average miss ${mw(summary.mae)}`}
            accent={DELIVERED}
          />
        </div>
      )}

      <Panel
        title="Hour by hour"
        note="Forecast against what was actually delivered. Positive error means the forecast was high, so too little gas was bought."
      >
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                interval={2}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                width={64}
                label={{
                  value: 'MW',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 12, fill: 'var(--text-muted)' },
                }}
              />
              <Tooltip
                formatter={(value, name) => [mw(typeof value === 'number' ? value : null), String(name)]}
                contentStyle={{
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  fontSize: 13,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 13 }} />
              <Line
                type="monotone"
                dataKey="delivered"
                name="Delivered"
                stroke={DELIVERED}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="forecast"
                name="Forecast at cutoff"
                stroke={FORECAST}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <Panel title="The same numbers as a table">
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[var(--surface-2)] text-left text-[var(--text-muted)]">
              <tr>
                <th className="py-2 font-medium">Hour</th>
                <th className="py-2 text-right font-medium">Forecast</th>
                <th className="py-2 text-right font-medium">Delivered</th>
                <th className="py-2 text-right font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {hours.map((row) => (
                <tr key={row.hour} className="border-t border-[var(--border)]">
                  <td className="py-1.5">{ukTime(row.hour)}</td>
                  <td className="py-1.5 text-right">{mw(row.forecast)}</td>
                  <td className="py-1.5 text-right">{mw(row.actual)}</td>
                  <td className="py-1.5 text-right">{signed(row.error)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
