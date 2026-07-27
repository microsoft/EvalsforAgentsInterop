import { createRoot } from 'react-dom/client'
import { ErrorBoundary } from "react-error-boundary";
import "@github/spark/spark"

import App from './App.tsx'
import { ErrorFallback } from './ErrorFallback.tsx'
import { fixAriaHiddenFocus } from './lib/a11y-fix'

import "./main.css"
import "./styles/theme.css"
import "./index.css"

// Fix aria-hidden elements that are focusable (accessibility issue)
fixAriaHiddenFocus()

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary FallbackComponent={ErrorFallback}>
    <App />
   </ErrorBoundary>
)
