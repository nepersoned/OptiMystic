import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, CellValueChangedEvent, GridReadyEvent } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import {
  Send, RotateCcw, Play, ChevronLeft, Check, X, History, Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { datasetsApi, type GridData, type ChatResult, type CellChange } from '@/api/datasets'
import { useDatasetStore } from '@/store/datasetStore'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  diffs?: CellChange[]
  pending?: boolean
}

export default function DatasetPage() {
  const { id } = useParams<{ id: string }>()
  const datasetId = Number(id)
  const navigate = useNavigate()

  const { setDataset, setVersion, addChange, clearChanges, pendingChanges, setResult } = useDatasetStore()

  const [grid, setGrid] = useState<GridData | null>(null)
  const [rowData, setRowData] = useState<Record<string, unknown>[]>([])
  const [colDefs, setColDefs] = useState<ColDef[]>([])
  const [versions, setVersions] = useState<{ version: number; note: string | null }[]>([])
  const [currentVersion, setCurrentVersionLocal] = useState(1)
  const [saving, setSaving] = useState(false)
  const [optimizing, setOptimizing] = useState(false)
  const [changedCells, setChangedCells] = useState<Set<string>>(new Set())

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [pendingDiffs, setPendingDiffs] = useState<CellChange[] | null>(null)
  const [optimizeError, setOptimizeError] = useState<string | null>(null)

  const chatBottomRef = useRef<HTMLDivElement>(null)
  const gridApiRef = useRef<import('ag-grid-community').GridApi | null>(null)
  const changedCellsRef = useRef(new Set<string>())

  const loadGrid = useCallback(
    async (version?: number) => {
      const data = await datasetsApi.getGrid(datasetId, version)
      setGrid(data)
      setRowData(data.rows)
      setDataset(datasetId, data.name, data.version, data.columns)
      setCurrentVersionLocal(data.version)
      changedCellsRef.current.clear()
      setChangedCells(new Set())
      clearChanges()
      setColDefs(
        data.columns.map((col) => ({
          field: col,
          headerName: col,
          editable: true,
          flex: 1,
          minWidth: 100,
          cellStyle: (params) => {
            const key = `${params.rowIndex}-${col}`
            return changedCellsRef.current.has(key) ? { backgroundColor: '#fef9c3' } : null
          },
        })),
      )
    },
    [datasetId, setDataset, clearChanges],
  )

  useEffect(() => {
    loadGrid()
    datasetsApi.listVersions(datasetId).then(setVersions)
  }, [datasetId, loadGrid])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    gridApiRef.current?.refreshCells({ force: true })
  }, [changedCells])

  const onCellValueChanged = (e: CellValueChangedEvent) => {
    const change: CellChange = { row: e.rowIndex ?? 0, col: e.colDef.field!, value: e.newValue }
    addChange(change)
    const key = `${change.row}-${change.col}`
    changedCellsRef.current.add(key)
    setChangedCells((prev) => new Set(prev).add(key))
  }

  const handleSave = async () => {
    if (!pendingChanges.length) return
    setSaving(true)
    try {
      const res = await datasetsApi.patchCells(datasetId, pendingChanges, 'manual edit')
      clearChanges()
      changedCellsRef.current.clear()
      setChangedCells(new Set())
      setCurrentVersionLocal(res.version)
      setVersion(res.version)
      await datasetsApi.listVersions(datasetId).then(setVersions)
    } finally {
      setSaving(false)
    }
  }

  const handleRestore = async (v: number) => {
    const res = await datasetsApi.restoreVersion(datasetId, v)
    await loadGrid(res.new_version)
    await datasetsApi.listVersions(datasetId).then(setVersions)
  }

  const handleOptimize = async () => {
    setOptimizing(true)
    setOptimizeError(null)
    try {
      const res = await datasetsApi.optimize(datasetId)
      setResult(res)
      navigate(`/datasets/${datasetId}/results`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: { message?: string } | string } }; message?: string }
      const detail = e?.response?.data?.detail
      const msg = typeof detail === 'object' ? detail?.message : (detail ?? e?.message ?? '알 수 없는 오류')
      setOptimizeError(msg ?? '최적화 오류')
    } finally {
      setOptimizing(false)
    }
  }

  const handleChat = async () => {
    if (!input.trim() || chatLoading) return
    const msg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setChatLoading(true)
    try {
      const res: ChatResult = await datasetsApi.chat(datasetId, msg)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.reply,
          diffs: res.suggested_diffs.length > 0 ? res.suggested_diffs : undefined,
        },
      ])
      if (res.suggested_diffs.length > 0) setPendingDiffs(res.suggested_diffs)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: { message?: string } | string } }; message?: string }
      const detail = e?.response?.data?.detail
      const errMsg = typeof detail === 'object' ? detail?.message : (detail ?? e?.message ?? '오류 발생')
      setMessages((prev) => [...prev, { role: 'assistant', content: `오류: ${errMsg}` }])
    } finally {
      setChatLoading(false)
    }
  }

  const applyDiffs = async (diffs: CellChange[]) => {
    diffs.forEach(addChange)
    await datasetsApi.patchCells(datasetId, diffs, 'agent suggestion')
    changedCellsRef.current.clear()
    await loadGrid()
    await datasetsApi.listVersions(datasetId).then(setVersions)
    setPendingDiffs(null)
  }

  if (!grid) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* Top bar */}
      <header className="bg-slate-900 text-white px-4 py-3 flex items-center gap-3 shrink-0">
        <button onClick={() => navigate('/')} className="text-slate-400 hover:text-white">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center font-bold text-xs">O</div>
        <span className="font-medium">{grid.name}</span>
        <Badge variant="secondary" className="text-xs">v{currentVersion}</Badge>
        {pendingChanges.length > 0 && (
          <Badge variant="warning" className="text-xs">{pendingChanges.length}개 변경</Badge>
        )}
        <div className="ml-auto flex items-center gap-2">
          {/* Version history */}
          <div className="relative group">
            <Button variant="ghost" size="sm" className="text-slate-300 hover:text-white">
              <History className="w-4 h-4" />
            </Button>
            <div className="absolute right-0 top-full mt-1 w-56 bg-white rounded-lg shadow-lg border z-10 hidden group-hover:block">
              <div className="p-2 text-xs text-slate-500 font-medium border-b">버전 기록</div>
              <div className="max-h-48 overflow-y-auto">
                {versions.map((v) => (
                  <button
                    key={v.version}
                    onClick={() => handleRestore(v.version)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 flex justify-between text-slate-700"
                  >
                    <span>v{v.version} — {v.note ?? '편집'}</span>
                    <RotateCcw className="w-3 h-3 text-slate-400" />
                  </button>
                ))}
              </div>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="text-slate-900 text-xs"
            onClick={handleSave}
            disabled={!pendingChanges.length || saving}
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
            저장
          </Button>
          <Button size="sm" className="text-xs" onClick={handleOptimize} disabled={optimizing}>
            {optimizing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
            최적화 실행
          </Button>
        </div>
      </header>

      {/* Body: grid + sidebar */}
      <div className="flex-1 flex overflow-hidden">
        {/* AG Grid */}
        <div className="flex-1 overflow-hidden ag-theme-alpine">
          {optimizeError && (
            <div className="bg-red-50 border-b border-red-200 text-red-700 text-xs px-4 py-2 flex items-center justify-between">
              <span>최적화 오류: {optimizeError}</span>
              <button onClick={() => setOptimizeError(null)} className="ml-2 text-red-400 hover:text-red-600">✕</button>
            </div>
          )}
          <AgGridReact
            rowData={rowData}
            columnDefs={colDefs}
            defaultColDef={{ resizable: true, sortable: true, filter: true }}
            onCellValueChanged={onCellValueChanged}
            onGridReady={(e: GridReadyEvent) => { gridApiRef.current = e.api }}
            animateRows
          />
        </div>

        {/* Agent sidebar */}
        <div className="w-80 border-l bg-white flex flex-col shrink-0">
          <div className="px-4 py-3 border-b flex items-center gap-2">
            <div className="w-2 h-2 bg-green-400 rounded-full" />
            <span className="text-sm font-medium text-slate-700">AI 에이전트</span>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.length === 0 && (
              <p className="text-xs text-slate-400 text-center mt-4">
                데이터에 대해 질문하거나 변경을 요청하세요
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[90%] rounded-lg px-3 py-2 text-xs ${
                    m.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.content}</p>
                  {m.diffs && m.diffs.length > 0 && (
                    <div className="mt-2 border-t border-slate-200 pt-2 space-y-1">
                      <p className="text-slate-500 font-medium">제안 변경 ({m.diffs.length}건)</p>
                      {m.diffs.slice(0, 3).map((d, j) => (
                        <div key={j} className="font-mono text-slate-600">
                          행{d.row} · {d.col} → {String(d.value)}
                        </div>
                      ))}
                      {m.diffs.length > 3 && (
                        <p className="text-slate-400">외 {m.diffs.length - 3}건...</p>
                      )}
                      <div className="flex gap-1 mt-2">
                        <button
                          onClick={() => applyDiffs(m.diffs!)}
                          className="flex-1 bg-green-600 text-white rounded px-2 py-1 text-xs flex items-center justify-center gap-1"
                        >
                          <Check className="w-3 h-3" /> 승인
                        </button>
                        <button
                          onClick={() => setPendingDiffs(null)}
                          className="flex-1 bg-slate-200 text-slate-700 rounded px-2 py-1 text-xs flex items-center justify-center gap-1"
                        >
                          <X className="w-3 h-3" /> 거절
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-lg px-3 py-2">
                  <Loader2 className="w-3 h-3 animate-spin text-slate-500" />
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Input */}
          <div className="border-t p-3 flex gap-2">
            <textarea
              className="flex-1 border rounded-lg px-3 py-2 text-xs resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="메시지 입력..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleChat()
                }
              }}
            />
            <Button size="icon" onClick={handleChat} disabled={chatLoading || !input.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
