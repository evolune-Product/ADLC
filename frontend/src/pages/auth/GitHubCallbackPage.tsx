import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'
import api from '@/lib/api'

export default function GitHubCallbackPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login } = useAuthStore()

  useEffect(() => {
    const token = searchParams.get('token')
    const error = searchParams.get('error')

    if (error || !token) {
      toast.error('GitHub sign-in failed. Please try again.')
      navigate('/login')
      return
    }

    localStorage.setItem('access_token', token)

    api.get('/auth/me')
      .then((res) => {
        login(token, res.data)
        navigate('/dashboard')
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        toast.error('GitHub sign-in failed. Please try again.')
        navigate('/login')
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <p className="text-sm text-muted-foreground">Signing you in…</p>
    </div>
  )
}
