/**
 * API client — thin wrapper over fetch proxied through Vite to FastAPI.
 * All requests are prefixed with /api. Supports VITE_API_URL in production.
 */

const API_HOST = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : ''
const BASE = `${API_HOST}/api`

async function request(method, path, body, isFormData = false) {
  const opts = {
    method,
    headers: isFormData ? {} : { 'Content-Type': 'application/json' },
    body: body
      ? isFormData
        ? body
        : JSON.stringify(body)
      : undefined,
  }

  const res = await fetch(`${BASE}${path}`, opts)

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const err = await res.json()
      detail = err.detail || JSON.stringify(err)
    } catch (_) {}
    throw new Error(detail)
  }

  return await res.json()
}

export const api = {
  health: () => request('GET', '/health'),

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
    const res = await fetch(`${BASE}/session/${sessionId}/pdf`)
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

