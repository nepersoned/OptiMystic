import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import UploadPage from '@/pages/UploadPage'
import DatasetPage from '@/pages/DatasetPage'
import ResultsPage from '@/pages/ResultsPage'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/datasets/:id" element={<DatasetPage />} />
          <Route path="/datasets/:id/results" element={<ResultsPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
