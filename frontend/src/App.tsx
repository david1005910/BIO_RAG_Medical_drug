import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import SearchResultsPage from './pages/SearchResultsPage'
import DrugDetailPage from './pages/DrugDetailPage'
import AdminPage from './pages/AdminPage'
import VectorSpacePage from './pages/VectorSpacePage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/search" element={<SearchResultsPage />} />
        <Route path="/drugs/:drugId" element={<DrugDetailPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/vector-space" element={<VectorSpacePage />} />
      </Routes>
    </Layout>
  )
}

export default App
