import { create } from 'zustand'
import type { Run, RunStep } from '@/types'

interface RunState {
  activeRun: Run | null
  liveSteps: RunStep[]
  setActiveRun: (run: Run) => void
  appendStep: (step: RunStep) => void
  updateStepLog: (stepName: string, log: string) => void
  clearActiveRun: () => void
}

export const useRunStore = create<RunState>((set) => ({
  activeRun: null,
  liveSteps: [],
  setActiveRun: (run) => set({ activeRun: run, liveSteps: run.steps }),
  appendStep: (step) => set((state) => ({ liveSteps: [...state.liveSteps, step] })),
  updateStepLog: (stepName, log) =>
    set((state) => ({
      liveSteps: state.liveSteps.map((s) =>
        s.step_name === stepName ? { ...s, log: (s.log ?? '') + log } : s
      ),
    })),
  clearActiveRun: () => set({ activeRun: null, liveSteps: [] }),
}))
