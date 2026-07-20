/**
 * LoadingSkeleton
 * ---------------
 * Animated pulse skeleton shown while a list is loading.
 *
 * Usage:
 *   <LoadingSkeleton />              // 3 rows, h-24
 *   <LoadingSkeleton rows={5} height="h-16" />
 */

interface LoadingSkeletonProps {
  rows?: number
  height?: string
}

export function LoadingSkeleton({ rows = 3, height = 'h-24' }: LoadingSkeletonProps) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={`${height} rounded-lg border bg-muted/40 animate-pulse`} />
      ))}
    </div>
  )
}
