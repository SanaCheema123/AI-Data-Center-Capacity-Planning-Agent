import React from 'react'
import ReactDOM from 'react-dom/client'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

import { App } from './app/App'
import { GlobalFeedback } from './components/GlobalFeedback'
import { emitAppError } from './events/appError'
import './styles/index.css'

const queryClient = new QueryClient({
  mutationCache: new MutationCache({ onError: (error) => emitAppError(error) }),
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
        <GlobalFeedback />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
