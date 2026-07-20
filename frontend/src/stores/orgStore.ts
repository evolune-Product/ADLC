import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Organization } from '@/types'

interface OrgState {
  activeOrg: Organization | null
  setActiveOrg: (org: Organization | null) => void
  clearActiveOrg: () => void
}

export const useOrgStore = create<OrgState>()(
  persist(
    (set) => ({
      activeOrg: null,
      setActiveOrg: (org) => set({ activeOrg: org }),
      clearActiveOrg: () => set({ activeOrg: null }),
    }),
    {
      name: 'active-org',
    }
  )
)
