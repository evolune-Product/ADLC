import { create } from 'zustand'
import type { User } from '@/types'
import { setToken, removeToken } from '@/lib/auth'
import { useOrgStore } from '@/stores/orgStore'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  login: (token: string, user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  setUser: (user) => set({ user, isAuthenticated: true }),
  login: (token, user) => {
    setToken(token)
    set({ user, isAuthenticated: true })
  },
  logout: () => {
    removeToken()
    useOrgStore.getState().clearActiveOrg()
    set({ user: null, isAuthenticated: false })
  },
}))
