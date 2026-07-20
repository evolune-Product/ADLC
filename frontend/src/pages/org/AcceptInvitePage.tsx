import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { useAcceptInvite } from '@/hooks/useOrgMembers'
import { isAuthenticated } from '@/lib/auth'
import { getApiError } from '@/lib/api'

export default function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const accept = useAcceptInvite()
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    if (!isAuthenticated()) {
      // Store the invitation token so we can redirect back after login
      sessionStorage.setItem('invite_token', token)
      navigate('/login', { replace: true })
      return
    }
    setStatus('loading')
    accept.mutateAsync(token)
      .then(() => setStatus('success'))
      .catch((err) => {
        setError(getApiError(err))
        setStatus('error')
      })
  }, [token])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-lg p-8 max-w-sm w-full text-center shadow">
        {status === 'loading' && (
          <>
            <Loader2 className="h-8 w-8 mx-auto mb-4 text-muted-foreground animate-spin" />
            <p className="text-sm text-muted-foreground">Accepting invitation...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="h-8 w-8 mx-auto mb-4 text-green-500" />
            <h1 className="text-lg font-semibold text-foreground mb-2">Invitation accepted</h1>
            <p className="text-sm text-muted-foreground mb-6">
              You have joined the organization. Switch to it from the org switcher in the sidebar.
            </p>
            <Link
              to="/dashboard"
              className="block w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity"
            >
              Go to dashboard
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="h-8 w-8 mx-auto mb-4 text-red-500" />
            <h1 className="text-lg font-semibold text-foreground mb-2">Invitation failed</h1>
            <p className="text-sm text-muted-foreground mb-6">{error}</p>
            <Link
              to="/dashboard"
              className="block w-full py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-85 transition-opacity"
            >
              Go to dashboard
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
