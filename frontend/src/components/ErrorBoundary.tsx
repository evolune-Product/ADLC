import React from 'react'

interface Props {
  children: React.ReactNode
  /** Optional custom fallback — if omitted, the built-in full-page fallback is shown. */
  fallback?: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught rendering error:', error, info.componentStack)
  }

  private reset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex min-h-screen items-center justify-center p-6 bg-background">
          <div className="max-w-sm w-full text-center space-y-5">
            <div className="text-5xl">⚠️</div>
            <div>
              <h1 className="text-xl font-semibold">Something went wrong</h1>
              <p className="text-sm text-muted-foreground mt-2">
                {this.state.error?.message ?? 'An unexpected error occurred in the application.'}
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={this.reset}
                className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
              >
                Try again
              </button>
              <button
                onClick={() => { window.location.href = '/dashboard' }}
                className="px-4 py-2 rounded-md bg-secondary text-secondary-foreground text-sm font-medium hover:bg-secondary/80 transition-colors"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
