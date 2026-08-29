import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'
import api from '@/lib/api'
import { getApiError } from '@/lib/api'

const schema = z.object({
  name:     z.string().min(2, 'Name must be at least 2 characters'),
  email:    z.string().email('Invalid email'),
  org_name: z.string().optional(),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})
type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const { login } = useAuthStore()

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    try {
      const res = await api.post('/auth/register', data)
      login(res.data.access_token, res.data.user)
      // Company OS's onboarding wizard (org + departments + invites) is kept
      // in the codebase but not exposed as a feature yet — see
      // pages/onboarding/OnboardingPage.tsx. Straight to the dashboard, same
      // as before that wizard existed.
      navigate('/dashboard')
    } catch (err) {
      toast.error(getApiError(err, 'Registration failed'))
    }
  }

  const field = (
    id: string,
    label: string,
    type = 'text',
    placeholder = '',
    optional = false,
  ) => (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-medium text-foreground uppercase tracking-wide">
        {label}{optional && <span className="text-muted-foreground normal-case font-normal ml-1">(optional)</span>}
      </label>
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        {...register(id as keyof FormData)}
        className="w-full px-3 py-2 text-sm bg-card border border-border rounded text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-foreground/20 focus:border-foreground/40 transition-colors"
      />
    </div>
  )

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Create account</h1>
        <p className="text-sm text-muted-foreground mt-1">Set up your ADLC workspace.</p>
      </div>

      {/* Social OAuth */}
      <div className="flex flex-col gap-2">
        <a
          href={`${apiUrl}/auth/google`}
          className="flex items-center justify-center gap-2.5 w-full px-4 py-2.5 bg-card border border-border rounded text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
            <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
            <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
            <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </a>
        <a
          href={`${apiUrl}/auth/github`}
          className="flex items-center justify-center gap-2.5 w-full px-4 py-2.5 bg-card border border-border rounded text-sm font-medium text-foreground hover:bg-muted transition-colors"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
          </svg>
          Continue with GitHub
        </a>
      </div>

      <div className="flex items-center gap-3 my-5">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground">or</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {field('name', 'Full name', 'text', 'Jane Smith')}
        {errors.name && <p className="text-xs text-destructive -mt-2">{errors.name.message}</p>}

        {field('email', 'Email', 'email', 'you@example.com')}
        {errors.email && <p className="text-xs text-destructive -mt-2">{errors.email.message}</p>}

        {field('org_name', 'Organization', 'text', 'Acme Corp', true)}

        {field('password', 'Password', 'password', 'Min. 8 characters')}
        {errors.password && <p className="text-xs text-destructive -mt-2">{errors.password.message}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 px-4 py-2.5 bg-foreground text-background text-sm font-semibold rounded hover:opacity-90 disabled:opacity-50 transition-opacity"
        >
          {isSubmitting ? 'Creating account…' : 'Create account →'}
        </button>
      </form>

      <p className="text-sm text-muted-foreground text-center mt-6">
        Already have an account?{' '}
        <Link to="/login" className="text-foreground font-medium hover:underline underline-offset-2">
          Sign in
        </Link>
      </p>
    </div>
  )
}
