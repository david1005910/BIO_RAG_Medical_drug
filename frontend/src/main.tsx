import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { SearchProvider } from './context/SearchContext'
import { MemoryProvider } from './context/MemoryContext'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5분
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MemoryProvider>
          <SearchProvider>
            <App />
          </SearchProvider>
        </MemoryProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
