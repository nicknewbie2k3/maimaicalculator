import { createInertiaApp } from '@inertiajs/react'
import axios from 'axios'
import { createRoot } from 'react-dom/client'
import './app.css'

axios.defaults.xsrfHeaderName = 'X-CSRFToken'
axios.defaults.xsrfCookieName = 'csrftoken'

createInertiaApp({
  resolve: name => {
    const pages = import.meta.glob('./pages/**/*.tsx', { eager: true })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return pages[`./pages/${name}.tsx`] as any
  },
  setup({ el, App, props }) {
    createRoot(el).render(<App {...props} />)
  },
})
