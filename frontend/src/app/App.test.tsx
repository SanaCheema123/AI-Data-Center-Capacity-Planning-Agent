import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { App } from './App'

describe('App routes', () => {
  it('renders the lazy-loaded landing page', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/']}>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/Infrastructure pulse/i)
    expect(screen.getAllByRole('link', { name: /Sign In/i }).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Open Platform/i })).toBeInTheDocument()
  })
})
