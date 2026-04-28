import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/Layout/Header'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'
import ValidationPage from './pages/ValidationPage'
import JobsPage from './pages/JobsPage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Header />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/validation/:jobId" element={<ValidationPage />} />
            <Route path="/jobs" element={<JobsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
