import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { datasetsApi, type UploadResult } from '@/api/datasets'
import { useDatasetStore } from '@/store/datasetStore'

const DOMAIN_LABELS: Record<string, string> = {
  vrp: 'Vehicle Routing',
  packing: 'Bin Packing',
  cutting: 'Cutting Stock',
  scheduling: 'Shift Scheduling',
  resourcing: 'Resource Allocation',
  nlp: 'Nonlinear Opt.',
  generic: 'Generic',
}

export default function UploadPage() {
  const navigate = useNavigate()
  const setDataset = useDatasetStore((s) => s.setDataset)

  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<UploadResult | null>(null)

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.match(/\.(xlsx|xls|csv)$/i)) {
        setError('xlsx, xls, csv 파일만 지원합니다.')
        return
      }
      setLoading(true)
      setError(null)
      try {
        const res = await datasetsApi.upload(file)
        setResult(res)
        setDataset(res.dataset_id, res.name, res.version, res.columns)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : '업로드 실패')
      } finally {
        setLoading(false)
      }
    },
    [setDataset],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    },
    [handleFile],
  )

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-slate-900 text-white px-6 py-4 flex items-center gap-3">
        <div className="w-7 h-7 bg-blue-500 rounded flex items-center justify-center font-bold text-sm">O</div>
        <span className="font-semibold text-lg">OptiMystic</span>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-8 gap-6 max-w-2xl mx-auto w-full">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900">데이터 업로드</h1>
          <p className="text-slate-500 mt-1 text-sm">xlsx, xls, csv 파일을 올리면 자동으로 도메인을 추론합니다</p>
        </div>

        {/* Drop zone */}
        {!result && (
          <label
            className={`w-full border-2 border-dashed rounded-xl p-12 flex flex-col items-center gap-4 cursor-pointer transition-colors ${
              dragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-300'
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <Upload className={`w-10 h-10 ${dragging ? 'text-blue-500' : 'text-slate-400'}`} />
            <div className="text-center">
              <p className="font-medium text-slate-700">파일을 드래그하거나 클릭해서 선택</p>
              <p className="text-xs text-slate-400 mt-1">xlsx · xls · csv</p>
            </div>
            <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={onInputChange} />
          </label>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-slate-600">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">분석 중...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-3 rounded-lg w-full">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Result card */}
        {result && (
          <Card className="w-full">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <CardTitle className="text-base">{result.name}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Stats */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: '행', value: result.row_count },
                  { label: '열', value: result.col_count },
                  { label: '버전', value: `v${result.version}` },
                ].map((s) => (
                  <div key={s.label} className="bg-slate-50 rounded-lg p-3 text-center">
                    <div className="text-lg font-bold text-slate-900">{s.value}</div>
                    <div className="text-xs text-slate-500">{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Inferred domain */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">추론 도메인</span>
                <Badge variant="default">{DOMAIN_LABELS[result.inferred_domain] ?? result.inferred_domain}</Badge>
                <Badge variant="secondary">{result.inferred_solver.toUpperCase()}</Badge>
              </div>

              {/* Columns */}
              <div>
                <p className="text-xs text-slate-500 mb-2">감지된 컬럼</p>
                <div className="flex flex-wrap gap-1">
                  {result.columns.map((c) => (
                    <span key={c} className="bg-slate-100 text-slate-700 text-xs px-2 py-0.5 rounded">
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button className="flex-1" onClick={() => navigate(`/datasets/${result.dataset_id}`)}>
                  <FileSpreadsheet className="w-4 h-4" />
                  그리드 편집기로 이동
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setResult(null); setError(null) }}
                >
                  다시 업로드
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
