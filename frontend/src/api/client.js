/**
 * API client — thin wrapper over fetch proxied through Vite to FastAPI.
 * All requests are prefixed with /api. Supports VITE_API_URL in production,
 * Render private-host expansion, automatic cold-start retry, and client override.
 */

function resolveApiHost() {
  // 1. Manual user override in browser localStorage (if configured)
  try {
    const custom = localStorage.getItem('CASECOMPILER_API_URL')
    if (custom && custom.trim()) {
      return custom.trim().replace(/\/$/, '')
    }
  } catch (_) {}

  // 2. Build-time environment variable VITE_API_URL
  let host = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '')

  // If host is just a hostname without domain (e.g. 'casecompiler-backend' from Render private net)
  if (host && !host.includes('.')) {
    host = `${host}.onrender.com`
  }

  // Ensure scheme
  if (host && !host.startsWith('http://') && !host.startsWith('https://')) {
    host = `https://${host}`
  }

  // 3. Fallback for Render static sites if VITE_API_URL was empty or missing at build time
  if (!host && typeof window !== 'undefined' && window.location?.hostname?.includes('onrender.com')) {
    const fHost = window.location.hostname
    // If frontend is named casecompiler-frontend[-xxx].onrender.com
    const bHost = fHost.replace('casecompiler-frontend', 'casecompiler-backend')
    host = `https://${bHost}`
  }

  return host
}

let API_HOST = resolveApiHost()

export function getApiBase() {
  return API_HOST ? `${API_HOST}/api` : '/api'
}

export function setApiHost(newHost) {
  API_HOST = (newHost || '').trim().replace(/\/$/, '')
  try {
    if (API_HOST) {
      localStorage.setItem('CASECOMPILER_API_URL', API_HOST)
    } else {
      localStorage.removeItem('CASECOMPILER_API_URL')
    }
  } catch (_) {}
}

export function getCurrentApiHost() {
  return API_HOST || (typeof window !== 'undefined' ? `${window.location.origin} (Vite Proxy)` : 'Localhost Proxy')
}

// Sleep helper
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function request(method, path, body, isFormData = false, maxRetries = 2) {
  const base = getApiBase()
  const opts = {
    method,
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    body: body
      ? isFormData
        ? body
        : JSON.stringify(body)
      : undefined,
  }

  let lastErr = null

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${base}${path}`, opts)

      // If Render free tier is waking up, proxy may return 502/503/504
      if ([502, 503, 504].includes(res.status) && attempt < maxRetries) {
        await sleep(2500 * (attempt + 1))
        continue
      }

      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const err = await res.json()
          detail = err.detail || JSON.stringify(err)
        } catch (_) {}
        throw new Error(detail)
      }

      return await res.json()
    } catch (err) {
      lastErr = err
      const isNetworkError =
        err?.name === 'TypeError' ||
        err?.message?.includes('Failed to fetch') ||
        err?.message?.includes('NetworkError') ||
        err?.message?.includes('HTTP 502') ||
        err?.message?.includes('HTTP 503') ||
        err?.message?.includes('HTTP 504')

      if (isNetworkError && attempt < maxRetries) {
        await sleep(2500 * (attempt + 1))
        continue
      }
      break
    }
  }

  // Provide high-clarity error message if connection failed
  const msg = lastErr?.message || 'Network error'
  if (msg.includes('Failed to fetch') || lastErr?.name === 'TypeError') {
    throw new Error(
      `Unable to connect to backend server (${base}). If this is hosted on Render free tier, the backend may take 30–50 seconds to wake up from idle sleep. Please wait a moment and try again.`
    )
  }
  throw lastErr
}

export const api = {
  health: () => request('GET', '/health'),
  getCurrentHost: getCurrentApiHost,
  setCustomHost: setApiHost,

  // Session
  createSession: () => request('POST', '/session'),
  getSession: (id) => request('GET', `/session/${id}`),
  deleteSession: (id) => request('DELETE', `/session/${id}`),
  getPhase: (id) => request('GET', `/session/${id}/phase`),

  // Extraction — multipart form
  extract: (sessionId, description, files) => {
    const form = new FormData()
    form.append('description', description)
    files.forEach((f) => form.append('files', f))
    return request('POST', `/session/${sessionId}/extract`, form, true)
  },

  // Interview
  postAnswer: (sessionId, answer) =>
    request('POST', `/session/${sessionId}/answer`, { answer }),

  // Compile
  compile: (sessionId) => request('GET', `/session/${sessionId}/compile`),

  // PDF Export
  downloadPDF: async (sessionId, filename) => {
    const base = getApiBase()
    const res = await fetch(`${base}/session/${sessionId}/pdf`)
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const err = await res.json()
        detail = err.detail || JSON.stringify(err)
      } catch (_) {}
      throw new Error(detail)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `case-file-${sessionId.slice(0, 8)}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  },

  // Corpus indexing
  indexCorpus: (forceRebuild = false) =>
    request('POST', `/index-corpus?force_rebuild=${forceRebuild}`),
}
