import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AIContextProvider } from './context/AIContext'

const originalFetch = window.fetch;
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
  
  if (url.startsWith('/api/')) {
    init = init || {};
    init.headers = {
      ...init.headers,
      'X-User-ID': localStorage.getItem('user_id') || 'test_user_1'
    };
  }
  return originalFetch(input, init);
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AIContextProvider>
      <App />
    </AIContextProvider>
  </StrictMode>,
)
