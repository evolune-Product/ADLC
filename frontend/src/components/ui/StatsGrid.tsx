/**
 * StatsGrid
 * ---------
 * A row of stat cards used on every resource list page (Skills, Agents, Pods, etc.).
 *
 * Usage:
 *   <StatsGrid stats={[
 *     { label: 'Total',   value: items.length },
 *     { label: 'Active',  value: activeCount },
 *     { label: 'Inactive', value: items.length - activeCount },
 *   ]} />
 */

interface Stat {
  label: string
  value: number
}

const GRID_COLS: Record<number, string> = {
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
}

interface StatsGridProps {
  stats: Stat[]
  /** Defaults to the number of stats provided (max 4). */
  columns?: 2 | 3 | 4
}

export function StatsGrid({ stats, columns }: StatsGridProps) {
  const cols = columns ?? Math.min(stats.length, 4)
  return (
    <div className={`grid ${GRID_COLS[cols] ?? 'grid-cols-3'} gap-4`}>
      {stats.map(({ label, value }) => (
        <div key={label} className="rounded-lg border p-4">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-2xl font-semibold mt-1">{value}</p>
        </div>
      ))}
    </div>
  )
}
