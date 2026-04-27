import { api } from './client'

export interface UploadResult {
  dataset_id: number
  name: string
  version: number
  row_count: number
  col_count: number
  columns: string[]
  inferred_domain: string
  inferred_solver: string
}

export interface GridData {
  dataset_id: number
  name: string
  version: number
  columns: string[]
  rows: Record<string, unknown>[]
  row_count?: number
}

export interface VersionSummary {
  version: number
  note: string | null
  created_at: string
}

export interface CellChange {
  row: number
  col: string
  value: unknown
}

export interface OptimizeResult {
  status: string
  objective: number | null
  solve_time: number
  dataset_id: number
  domain_used: string
  solver_used: string
  details?: unknown
  chart_data?: unknown
  executive_summary?: unknown
  error_msg?: string | null
}

export interface ChatResult {
  reply: string
  recommended_domain: string
  recommended_solver: string
  reason: string
  suggested_diffs: CellChange[]
}

export const datasetsApi = {
  upload: async (file: File): Promise<UploadResult> => {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  getGrid: async (id: number, version?: number): Promise<GridData> => {
    const params = version !== undefined ? { version } : {}
    const { data } = await api.get(`/datasets/${id}/grid`, { params })
    return data
  },

  patchCells: async (id: number, changes: CellChange[], note?: string) => {
    const { data } = await api.patch(`/datasets/${id}/cells`, { changes, note })
    return data
  },

  listVersions: async (id: number): Promise<VersionSummary[]> => {
    const { data } = await api.get(`/datasets/${id}/versions`)
    return data
  },

  restoreVersion: async (id: number, version: number) => {
    const { data } = await api.post(`/datasets/${id}/versions/${version}/restore`)
    return data
  },

  optimize: async (
    id: number,
    opts?: { domain?: string; solver?: string },
  ): Promise<OptimizeResult> => {
    const { data } = await api.post(`/datasets/${id}/optimize`, opts ?? {})
    return data
  },

  chat: async (
    id: number,
    message: string,
    version?: number,
    history?: { role: string; content: string }[],
  ): Promise<ChatResult> => {
    const { data } = await api.post(`/datasets/${id}/chat`, { message, version, history: history ?? [] })
    return data
  },
}
