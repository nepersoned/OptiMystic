import { useNavigate, useParams } from 'react-router-dom'
import ReactECharts from 'echarts-for-react'
import { ChevronLeft, TrendingUp, TrendingDown, Minus, Clock, Target, Cpu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useDatasetStore } from '@/store/datasetStore'

type ChartData = Record<string, unknown>
type ExecutiveSummary = Record<string, unknown>

const STATUS_VARIANT: Record<string, 'success' | 'destructive' | 'warning' | 'secondary'> = {
  Optimal: 'success', optimal: 'success',
  ok: 'success', OK: 'success',
  Infeasible: 'destructive', infeasible: 'destructive',
  Error: 'destructive', error: 'destructive',
}

function KpiCard({
  label, value, unit, delta, icon: Icon,
}: {
  label: string; value: string | number | null; unit?: string; delta?: number | null; icon?: React.ElementType
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted-foreground">{label}</span>
          {Icon && <Icon className="w-4 h-4 text-muted-foreground" />}
        </div>
        <div className="text-2xl font-bold">
          {value ?? 'N/A'}
          {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
        </div>
        {delta != null && (
          <div className={`flex items-center gap-1 text-xs mt-1 ${delta < 0 ? 'text-green-600' : delta > 0 ? 'text-red-500' : 'text-slate-400'}`}>
            {delta < 0 ? <TrendingDown className="w-3 h-3" /> : delta > 0 ? <TrendingUp className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
            {delta !== 0 ? `${Math.abs(delta).toFixed(1)}% vs 이전` : '이전과 동일'}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function BarChart({ data, title }: { data: { categories: string[]; series: { name: string; data: number[] }[] }; title: string }) {
  const option = {
    title: { text: title, textStyle: { fontSize: 13, fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: data.categories, axisLabel: { fontSize: 11, rotate: data.categories.length > 6 ? 30 : 0 } },
    yAxis: { type: 'value' },
    series: data.series.map((s) => ({ name: s.name, type: 'bar', data: s.data })),
  }
  return <ReactECharts option={option} style={{ height: 240 }} />
}

function PieChart({ data, title }: { data: { name: string; value: number }[]; title: string }) {
  const option = {
    title: { text: title, textStyle: { fontSize: 13, fontWeight: 600 } },
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{ type: 'pie', radius: '60%', data, label: { fontSize: 11 } }],
  }
  return <ReactECharts option={option} style={{ height: 240 }} />
}

function GaugeChart({ value, title }: { value: number; title: string }) {
  const option = {
    title: { text: title, textStyle: { fontSize: 13, fontWeight: 600 } },
    series: [{
      type: 'gauge',
      progress: { show: true },
      detail: { valueAnimation: true, formatter: '{value}%', fontSize: 18 },
      data: [{ value: Math.round(value) }],
    }],
  }
  return <ReactECharts option={option} style={{ height: 200 }} />
}

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { lastResult: storeResult, datasetName } = useDatasetStore()
  const lastResult = storeResult ?? (() => {
    try { const s = sessionStorage.getItem('om_last_result'); return s ? JSON.parse(s) : null } catch { return null }
  })()

  if (!lastResult) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-slate-500">최적화 결과가 없습니다.</p>
        <Button onClick={() => navigate(`/datasets/${id}`)}>데이터셋으로 돌아가기</Button>
      </div>
    )
  }

  const chart = lastResult.chart_data as ChartData | undefined
  const summary = lastResult.executive_summary as ExecutiveSummary | undefined
  const domain = lastResult.domain_used
  const kpi = chart?.kpi as Record<string, unknown> | undefined
  const deltaPct = summary?.delta_pct as number | null | undefined

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Header */}
      <header className="bg-slate-900 text-white px-4 py-3 flex items-center gap-3 shrink-0">
        <button onClick={() => navigate(`/datasets/${id}`)} className="text-slate-400 hover:text-white">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center font-bold text-xs">O</div>
        <span className="font-medium">{datasetName}</span>
        <span className="text-slate-400 text-sm">— 최적화 결과</span>
        <Badge variant={STATUS_VARIANT[lastResult.status] ?? 'secondary'} className="ml-1">
          {lastResult.status}
        </Badge>
      </header>

      <main className="flex-1 p-6 max-w-6xl mx-auto w-full space-y-6">
        {/* Executive summary headline */}
        {summary?.headline && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm text-blue-800">
            {String(summary.headline)}
          </div>
        )}

        {/* KPI cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label="Status" value={lastResult.status} icon={Target} />
          <KpiCard
            label="Objective"
            value={lastResult.objective != null ? lastResult.objective.toFixed(4) : null}
            delta={deltaPct ?? null}
            icon={TrendingUp}
          />
          <KpiCard label="Solve Time" value={lastResult.solve_time.toFixed(2)} unit="s" icon={Clock} />
          <KpiCard label="Domain" value={`${lastResult.domain_used} / ${lastResult.solver_used}`} icon={Cpu} />
        </div>

        {/* Domain-specific KPIs */}
        {kpi && Object.keys(kpi).length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(kpi).map(([k, v]) => (
              <KpiCard key={k} label={k.replace(/_/g, ' ')} value={v != null ? String(v) : 'N/A'} />
            ))}
          </div>
        )}

        {/* Charts row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Bar chart (route, shift coverage, items, waste, variables) */}
          {chart?.route_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.route_bar as Parameters<typeof BarChart>[0]['data']} title="경로별 거리" />
            </CardContent></Card>
          )}
          {chart?.shift_coverage_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.shift_coverage_bar as Parameters<typeof BarChart>[0]['data']} title="시프트 커버리지" />
            </CardContent></Card>
          )}
          {chart?.items_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.items_bar as Parameters<typeof BarChart>[0]['data']} title="아이템 가치" />
            </CardContent></Card>
          )}
          {chart?.waste_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.waste_bar as Parameters<typeof BarChart>[0]['data']} title="패턴별 낭비" />
            </CardContent></Card>
          )}
          {chart?.resource_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.resource_bar as Parameters<typeof BarChart>[0]['data']} title="리소스 사용률" />
            </CardContent></Card>
          )}
          {chart?.variables_bar && (
            <Card><CardContent className="p-4">
              <BarChart data={chart.variables_bar as Parameters<typeof BarChart>[0]['data']} title="활성 변수" />
            </CardContent></Card>
          )}

          {/* Pie chart */}
          {chart?.coverage_pie && (
            <Card><CardContent className="p-4">
              <PieChart data={chart.coverage_pie as Parameters<typeof PieChart>[0]['data']} title="커버리지" />
            </CardContent></Card>
          )}
          {chart?.cost_waste_pie && (
            <Card><CardContent className="p-4">
              <PieChart data={chart.cost_waste_pie as Parameters<typeof PieChart>[0]['data']} title="소재 활용" />
            </CardContent></Card>
          )}

          {/* Gauge */}
          {chart?.utilization_gauge && (
            <Card><CardContent className="p-4">
              <GaugeChart value={(chart.utilization_gauge as { value: number }).value} title="용량 활용률" />
            </CardContent></Card>
          )}

          {/* Sensitivity */}
          {(chart?.sensitivity as ChartData | undefined)?.shadow_price_bar && (
            <Card><CardContent className="p-4">
              <BarChart
                data={(chart!.sensitivity as ChartData).shadow_price_bar as Parameters<typeof BarChart>[0]['data']}
                title="민감도 분석 (Shadow Price)"
              />
            </CardContent></Card>
          )}
        </div>

        {/* Summary details */}
        {summary && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">실행 요약</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2 text-slate-700">
              {summary.domain_kpi_line && <p>{String(summary.domain_kpi_line)}</p>}
              {summary.bottleneck && (
                <p>병목: <span className="font-medium text-red-600">{String(summary.bottleneck)}</span></p>
              )}
              {summary.recommendation && <p className="text-slate-500">{String(summary.recommendation)}</p>}
              {summary.feasible_rate != null && (
                <p>Feasible rate: <span className="font-medium">{(Number(summary.feasible_rate) * 100).toFixed(1)}%</span> ({Number(summary.run_count)}회 실행 기준)</p>
              )}
            </CardContent>
          </Card>
        )}

        <div className="flex gap-3">
          <Button variant="outline" onClick={() => navigate(`/datasets/${id}`)}>
            다시 편집
          </Button>
          <Button onClick={() => navigate('/')}>새 데이터 업로드</Button>
        </div>
      </main>
    </div>
  )
}
