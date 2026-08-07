import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Self-hosted variable fonts. Bundled rather than fetched from a font CDN:
// this platform is meant to run inside an air-gapped perimeter, and a
// marketing page that loses its typeface behind a firewall is a bad first
// impression on exactly the buyer who most needs it to work.
import '@fontsource-variable/archivo'
import '@fontsource-variable/jetbrains-mono'

import './index.css'
import './styles/marketing.css'
import '@uiw/react-md-editor/markdown-editor.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
