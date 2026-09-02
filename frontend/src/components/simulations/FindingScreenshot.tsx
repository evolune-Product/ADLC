import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface Props {
  simulationId: string
  findingId: string
}

/**
 * The screenshot endpoint requires the same Bearer auth as everything else,
 * so a plain <img src="/simulations/.../screenshot"> can't work — the browser
 * won't attach an Authorization header to an <img> request. Fetching through
 * the shared axios instance (which does) and turning the response into an
 * object URL is the standard workaround.
 */
export function FindingScreenshot({ simulationId, findingId }: Props) {
  const [src, setSrc] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false

    api
      .get(`/simulations/${simulationId}/findings/${findingId}/screenshot`, { responseType: 'blob' })
      .then((res) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(res.data)
        setSrc(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [simulationId, findingId])

  if (failed) return null
  if (!src) return <div className="h-40 rounded-md border border-border bg-muted animate-pulse" />

  return (
    <img
      src={src}
      alt="Screenshot at the moment this finding was flagged"
      className="rounded-md border border-border max-h-80 w-auto"
    />
  )
}
