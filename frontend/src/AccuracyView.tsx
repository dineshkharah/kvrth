import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  type Accuracy,
  CUTOFFS,
  mw,
  mwh,
  pct,
  signed,
  type SweepRow,
  useApi,
} from './api'
import { Failed, Field, Loading, Panel, Select, StatTile } from './ui'

const DELIVERED = '#2a78d6'
const FORECAST = '#eb6834'
const CORRECTED = '#1baf7a'

export default function AccuracyView() {
  const [cutoff, setCutoff] = useState('09:20')

  const accuracy = useApi<Accuracy>(`/api/accuracy?cutoff=${cutoff}`)
  const sweep = useApi<SweepRow[]>('/api/accuracy/cutoff-sweep')

  if (accuracy.error) return <Failed error={accuracy.error} />
  if (sweep.error) return <Failed error={sweep.error} />
  if (!accuracy.data || !sweep.data) return <Loading what="the accuracy figures" />

  const { raw, corrected, correction_factor, raw_by_horizon, corrected_by_horizon, histogram } =
    accuracy.data

  const sweepPoints = sweep.data.map((row) => ({
    cutoff: row.cutoff,
    label: row.label,
    mae: row.mae ?? 0,
    hindsight: row.cutoff === 'final',
  }))

  const horizonPoints = raw_by_horizon.map((band, index) => ({
    band: band.band.replace(' hours ahead', 'h'),
    raw: band.mae ?? 0,
    corrected: corrected_by_horizon[index]?.mae ?? 0,
  }))

  const histogramPoints = histogram.map((bin) => ({
    label: `${bin.from_mw}`,
    midpoint: (bin.from_mw + bin.to_mw) / 2,
    hours: bin.hours,
  }))

  return (
    <div className="flex flex-col gap-5">
      <Field label="Decision cutoff">
        <Select value={cutoff} onChange={setCutoff}>
          {CUTOFFS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </Field>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Mean absolute error" value={mw(raw.mae)} note="typical miss in any hour" />
        <StatTile
          label="Bias"
          value={signed(raw.bias)}
          note="positive means the forecast ran high, so too little gas was bought"
        />
        <StatTile label="WAPE" value={pct(raw.wape)} note="total miss over total delivered" />
        <StatTile
          label="Exposure"
          value={mwh(raw.mwh_exposure)}
          note={`across ${raw.hours} scored hours`}
        />
      </div>

      <Panel
        title="How much the choice of cutoff matters"
        note="Each bar scores the same January using only forecasts that existed at that moment. The final bar is hindsight, which the desk never had, and it is the number a careless analysis would report."
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={sweepPoints}
              layout="vertical"
              margin={{ top: 8, right: 56, bottom: 8, left: 8 }}
            >
              <CartesianGrid stroke="var(--border)" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                label={{
                  value: 'Mean absolute error, MW',
                  position: 'insideBottom',
                  offset: -4,
                  style: { fontSize: 12, fill: 'var(--text-muted)' },
                }}
              />
              <YAxis
                type="category"
                dataKey="cutoff"
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                width={56}
              />
              <Tooltip
                formatter={(value) => [mw(typeof value === 'number' ? value : null), 'MAE']}
                labelFormatter={(label) =>
                  sweepPoints.find((point) => point.cutoff === label)?.label ?? String(label)
                }
                contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', fontSize: 13 }}
              />
              <Bar dataKey="mae" radius={[0, 4, 4, 0]} label={{
                position: 'right',
                formatter: (value) => (typeof value === 'number' ? Math.round(value) : ''),
                style: { fontSize: 12, fill: 'var(--text-secondary)' },
              }}>
                {sweepPoints.map((point) => (
                  <Cell key={point.cutoff} fill={point.hindsight ? CORRECTED : DELIVERED} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">
          Scoring against the final forecast would make the forecast look{' '}
          <strong>
            {Math.round(
              (1 - (sweep.data.find((r) => r.cutoff === 'final')?.mae ?? 0) /
                (sweep.data.find((r) => r.cutoff === '09:20')?.mae ?? 1)) * 100,
            )}
            % better
          </strong>{' '}
          than it was at the moment the desk had to buy.
        </p>
      </Panel>

      <Panel
        title="Most of the error is a level gap you can simply remove"
        note={`The forecast sits consistently above delivered wind, most likely because it predicts available wind while the meter records what survived curtailment. Scaling every forecast by ${correction_factor.toFixed(3)} removes it.`}
      >
        <table className="w-full text-sm">
          <thead className="text-left text-[var(--text-muted)]">
            <tr>
              <th className="py-2 font-medium">Measure</th>
              <th className="py-2 text-right font-medium">Raw</th>
              <th className="py-2 text-right font-medium">After the correction</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Mean absolute error', mw(raw.mae), mw(corrected.mae)],
              ['Root mean square error', mw(raw.rmse), mw(corrected.rmse)],
              ['Bias', signed(raw.bias), signed(corrected.bias)],
              ['WAPE', pct(raw.wape), pct(corrected.wape)],
              ['p90 absolute error', mw(raw.p90_absolute_error), mw(corrected.p90_absolute_error)],
            ].map(([measure, rawValue, correctedValue]) => (
              <tr key={measure} className="border-t border-[var(--border)]">
                <td className="py-2">{measure}</td>
                <td className="py-2 text-right">{rawValue}</td>
                <td className="py-2 text-right font-medium">{correctedValue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel
        title="Error against how far ahead the forecast reached"
        note="Raw error looks like it shrinks the further ahead you look, which cannot be right. Every delivery day shares one cutoff, so a lead band is also a block of the clock, and the raw figures are really showing curtailment being worst overnight. Remove the level gap and the expected shape appears."
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={horizonPoints} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="band"
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                width={64}
                label={{
                  value: 'MAE, MW',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 12, fill: 'var(--text-muted)' },
                }}
              />
              <Tooltip
                formatter={(value, name) => [mw(typeof value === 'number' ? value : null), String(name)]}
                contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', fontSize: 13 }}
              />
              <Legend wrapperStyle={{ fontSize: 13 }} />
              <Bar dataKey="raw" name="Raw" fill={FORECAST} radius={[4, 4, 0, 0]} />
              <Bar dataKey="corrected" name="After correction" fill={CORRECTED} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <table className="mt-4 w-full text-sm">
          <thead className="text-left text-[var(--text-muted)]">
            <tr>
              <th className="py-2 font-medium">Lead time</th>
              <th className="py-2 text-right font-medium">Raw MAE</th>
              <th className="py-2 text-right font-medium">Corrected MAE</th>
              <th className="py-2 text-right font-medium">Hours</th>
            </tr>
          </thead>
          <tbody>
            {raw_by_horizon.map((band, index) => (
              <tr key={band.band} className="border-t border-[var(--border)]">
                <td className="py-2">{band.band}</td>
                <td className="py-2 text-right">{mw(band.mae)}</td>
                <td className="py-2 text-right">{mw(corrected_by_horizon[index]?.mae)}</td>
                <td className="py-2 text-right">{band.hours}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <Panel
        title="How the misses are spread"
        note="Each bar counts the hours whose error fell in that 500 MW band. A spread centred well to the right of zero is the level gap showing up again."
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramPoints} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="midpoint"
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                label={{
                  value: 'Error, MW (forecast minus delivered)',
                  position: 'insideBottom',
                  offset: -4,
                  style: { fontSize: 12, fill: 'var(--text-muted)' },
                }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--text-secondary)' }}
                stroke="var(--border)"
                width={48}
                label={{
                  value: 'Hours',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 12, fill: 'var(--text-muted)' },
                }}
              />
              <Tooltip
                formatter={(value) => [`${String(value)} hours`, 'Count']}
                labelFormatter={(label) => `around ${signed(typeof label === 'number' ? label : null)}`}
                contentStyle={{ borderRadius: 8, border: '1px solid var(--border)', fontSize: 13 }}
              />
              <Bar dataKey="hours" fill={DELIVERED} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>
    </div>
  )
}
