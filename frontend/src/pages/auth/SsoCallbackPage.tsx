import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'
import api from '@/lib/api'

/**
 * Where the identity provider's round trip lands.
 *
 * The interesting work already happened on the API: the code exchange, the
 * ID-token signature check against the provider's JWKS, the nonce comparison,
 * the domain re-check, and just-in-time provisioning into the organisation.
 * All this page receives is a finished ADLC token — the client secret never
 * comes near a browser.
 *
 * Failures never reach here; they redirect straight to /login with a reason,
 * which that page turns into a sentence.
 */
export default function SsoCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuthStore()

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      navigate('/login?error=sso_invalid', { replace: true })
      return
    }

    // Stored first so the axios interceptor can attach it to the /auth/me call
    // that follows.
    localStorage.setItem('access_token', token)

    api
      .get('/auth/me')
      .then((res) => {
        login(token, res.data)
        navigate('/dashboard', { replace: true })
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        toast.error('Single sign-on failed. Please try again.')
        navigate('/login', { replace: true })
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <p className="text-sm text-muted-foreground">Signing you in…</p>
    </div>
  )
}
