import { create } from 'zustand'
import type { OptimizeResult, CellChange } from '@/api/datasets'

interface DatasetStore {
  datasetId: number | null
  datasetName: string
  currentVersion: number
  columns: string[]
  pendingChanges: CellChange[]
  lastResult: OptimizeResult | null

  setDataset: (id: number, name: string, version: number, columns: string[]) => void
  setVersion: (v: number) => void
  addChange: (change: CellChange) => void
  clearChanges: () => void
  setResult: (r: OptimizeResult) => void
}

export const useDatasetStore = create<DatasetStore>((set) => ({
  datasetId: null,
  datasetName: '',
  currentVersion: 1,
  columns: [],
  pendingChanges: [],
  lastResult: null,

  setDataset: (id, name, version, columns) =>
    set({ datasetId: id, datasetName: name, currentVersion: version, columns }),

  setVersion: (v) => set({ currentVersion: v }),

  addChange: (change) =>
    set((s) => ({
      pendingChanges: [
        ...s.pendingChanges.filter((c) => !(c.row === change.row && c.col === change.col)),
        change,
      ],
    })),

  clearChanges: () => set({ pendingChanges: [] }),

  setResult: (r) => {
    try { sessionStorage.setItem('om_last_result', JSON.stringify(r)) } catch {}
    set({ lastResult: r })
  },
}))
