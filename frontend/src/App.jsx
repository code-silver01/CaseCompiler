import React, { useState, useCallback } from 'react'
import { Scale, Gavel, RefreshCw, AlertCircle, Loader2, ChevronRight, ArrowLeft } from 'lucide-react'
import { api } from './api/client'
import LandingPage from './components/LandingPage'
import ProgressStepper from './components/ProgressStepper'
import CaseInput from './components/CaseInput'
import InterviewPanel from './components/InterviewPanel'
import CaseFileOutput from './components/CaseFileOutput'

// ---- Steps: landing → describe → extract → interview → compile ----
const STEP_LANDING = 'landing'
const STEP_DESCRIBE = 'describe'
const STEP_EXTRACT = 'extract'
const STEP_INTERVIEW = 'interview'
const STEP_COMPILE = 'compile'

function ErrorBanner({ message, onDismiss }) {
  return (
    <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-5 py-4 mb-6 animate-slide-up">
      <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm text-red-300 font-medium">Something went wrong</p>
        <p className="text-xs text-red-400/80 mt-1">{message}</p>
      </div>
      <button onClick={onDismiss} className="text-red-500 hover:text-red-300 transition-colors text-xs">✕</button>
    </div>
  )
}

function LoadingOverlay({ message, subtext }) {
  return (
    <div className="glass-card rounded-2xl p-12 text-center animate-fade-in border border-gold-400/20 shadow-2xl">
      <div className="relative inline-flex mb-6">
        <div className="w-16 h-16 rounded-full border-2 border-navy-700 flex items-center justify-center bg-navy-900">
          <Scale size={28} className="text-gold-400" />
        </div>
        <div className="absolute inset-0 rounded-full border-2 border-gold-400/30 animate-ping" />
      </div>
      <p className="text-base font-semibold text-slate-100 mb-2 font-display">{message}</p>
      <p className="text-xs text-slate-400 max-w-sm mx-auto">{subtext || 'Extracting legal entities, scoring evidence reliability, and querying statutory knowledge base…'}</p>
      <div className="flex justify-center gap-1.5 mt-5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="dot-bounce w-2 h-2 rounded-full bg-gold-400"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </div>
    </div>
  )
}

export default function App() {
  const [step, setStep] = useState(STEP_LANDING)
  const [prefilledDescription, setPrefilledDescription] = useState('')
  const [prefilledFiles, setPrefilledFiles] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [caseState, setCaseState] = useState(null)
  const [caseFile, setCaseFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [error, setError] = useState(null)
  const [activePhase, setActivePhase] = useState('extraction')

  // Poll live sub-phase during extraction
  React.useEffect(() => {
    let timer = null
    if (step === STEP_EXTRACT && sessionId) {
      timer = setInterval(async () => {
        try {
          const res = await api.getPhase(sessionId)
          if (res?.phase) {
            setActivePhase(res.phase)
          }
        } catch (_) {}
      }, 400)
    } else {
      setActivePhase('extraction')
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [step, sessionId])

  const setErr = (e) => setError(typeof e === 'string' ? e : e?.message || 'Unknown error')
  const clearErr = () => setError(null)

  // ---- Navigation Handlers ----
  const handleStartCase = () => {
    setPrefilledDescription('')
    setPrefilledFiles([])
    setStep(STEP_DESCRIBE)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleStartWithTemplate = (templateText, templateFiles = []) => {
    setPrefilledDescription(templateText)
    setPrefilledFiles(templateFiles)
    setStep(STEP_DESCRIBE)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleBackToLanding = () => {
    setStep(STEP_LANDING)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // ---- Step 1 → 2: Submit case description + files ----
  const handleSubmit = useCallback(async (description, files) => {
    clearErr()
    setLoading(true)
    setStep(STEP_EXTRACT)
    setLoadingMsg('Creating secure session…')
    try {
      const session = await api.createSession()
      setSessionId(session.session_id)

      setLoadingMsg('Extracting legal entities and scoring evidence with ML…')
      const state = await api.extract(session.session_id, description, files)
      setCaseState(state)
      setStep(STEP_INTERVIEW)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      setErr(e)
      setStep(STEP_DESCRIBE)
    } finally {
      setLoading(false)
      setLoadingMsg('')
    }
  }, [])

  // ---- Step 3: Post interview answer ----
  const handleAnswer = useCallback(async (answer) => {
    if (!sessionId) return
    clearErr()
    setLoading(true)
    try {
      const state = await api.postAnswer(sessionId, answer)
      setCaseState(state)
    } catch (e) {
      setErr(e)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  // ---- Skip interview / compile ----
  const handleCompile = useCallback(async () => {
    if (!sessionId) return
    clearErr()
    setLoading(true)
    setLoadingMsg('Synthesizing 11-section executive case brief…')
    setStep(STEP_COMPILE)
    try {
      const file = await api.compile(sessionId)
      setCaseFile(file)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    } catch (e) {
      setErr(e)
      setStep(STEP_INTERVIEW)
    } finally {
      setLoading(false)
      setLoadingMsg('')
    }
  }, [sessionId])

  // ---- Reset ----
  const handleReset = () => {
    setStep(STEP_DESCRIBE)
    setSessionId(null)
    setCaseState(null)
    setCaseFile(null)
    setError(null)
    setLoadingMsg('')
    setPrefilledDescription('')
    setPrefilledFiles([])
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // 1. Render Landing Page when at STEP_LANDING
  if (step === STEP_LANDING) {
    return (
      <LandingPage
        onStartCase={handleStartCase}
        onStartWithTemplate={handleStartWithTemplate}
      />
    )
  }

  // 2. Render App Studio (Describe / Extract / Interview / Compile)
  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 selection:bg-gold-400/20 selection:text-gold-300">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-navy-600/20 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -right-40 w-96 h-96 bg-gold-500/5 rounded-full blur-3xl" />
      </div>

      {/* Studio Navigation Bar */}
      <nav className="relative z-20 border-b border-white/[0.06] bg-navy-950/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <button
            onClick={handleBackToLanding}
            className="flex items-center gap-2.5 text-slate-300 hover:text-white transition-colors cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-lg bg-navy-800 border border-navy-700 flex items-center justify-center text-slate-400 group-hover:text-gold-400 group-hover:border-gold-500/40 transition-all">
              <ArrowLeft size={16} />
            </div>
            <div className="text-left">
              <div className="flex items-center gap-1.5">
                <span className="font-display font-bold text-sm text-slate-100">CaseCompiler</span>
                <span className="text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-navy-800 text-gold-400 border border-gold-400/20">Studio</span>
              </div>
              <span className="text-[10px] text-slate-500 block leading-none">← Back to Overview</span>
            </div>
          </button>

          <div className="flex items-center gap-3">
            {step !== STEP_DESCRIBE && (
              <button
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors px-3 py-1.5 rounded-lg bg-navy-900 border border-navy-800 cursor-pointer"
              >
                <RefreshCw size={12} />
                <span>Start over</span>
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Main Studio Container */}
      <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 py-8">
        {/* Progress Stepper (hidden on final compile step to maximize document view) */}
        {step !== STEP_COMPILE && (
          <div className="mb-8">
            <ProgressStepper currentStep={step} activePhase={activePhase} />
          </div>
        )}

        {/* Global Error Alert */}
        {error && <ErrorBanner message={error} onDismiss={clearErr} />}

        {/* STEP 1: DESCRIBE */}
        {step === STEP_DESCRIBE && (
          <div className="glass-card p-6 sm:p-8 border border-white/[0.08] shadow-2xl">
            <div className="mb-6">
              <h2 className="font-display text-2xl font-bold text-white mb-1.5">
                Describe Your Legal Situation
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Provide as much context as you have — key dates, names, amounts in dispute, notices, and attach any contracts or screenshots.
              </p>
            </div>
            <CaseInput
              onSubmit={handleSubmit}
              loading={loading}
              initialDescription={prefilledDescription}
              initialFiles={prefilledFiles}
            />
          </div>
        )}

        {/* STEP 2: EXTRACT (Loading state) */}
        {step === STEP_EXTRACT && (
          <LoadingOverlay
            message={loadingMsg || 'Analyzing case facts with Gemini AI…'}
            subtext="Extracting parties, mapping chronology, evaluating evidence reliability with XGBoost model, and checking Karnataka/Model Tenancy Act provisions…"
          />
        )}

        {/* STEP 3: INTERVIEW */}
        {step === STEP_INTERVIEW && caseState && (
          <>
            {/* Extraction Quick Metrics Bar */}
            <div className="glass-card p-4 mb-4 animate-slide-up border border-white/[0.08]">
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <span className="text-xs uppercase font-mono font-bold text-gold-400 tracking-wider">
                  Initial Extraction Complete:
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-navy-900 border border-navy-800 text-slate-300 font-mono">
                    Parties: {caseState.parties?.length ?? 0}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-navy-900 border border-navy-800 text-slate-300 font-mono">
                    Events: {caseState.events?.length ?? 0}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-navy-900 border border-navy-800 text-slate-300 font-mono">
                    Claims: {caseState.claims?.length ?? 0}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-navy-900 border border-navy-800 text-slate-300 font-mono">
                    Evidence: {caseState.evidence?.length ?? 0}
                  </span>
                  {caseState.triage?.level && (
                    <span
                      className={`px-2.5 py-0.5 rounded font-mono font-bold ${
                        caseState.triage.level === 'HIGH'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                          : caseState.triage.level === 'MEDIUM'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      }`}
                    >
                      Urgency: {caseState.triage.level}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <InterviewPanel
              state={caseState}
              onAnswer={handleAnswer}
              onSkip={handleCompile}
              loading={loading}
              error={error}
              onClearError={clearErr}
            />
          </>
        )}

        {/* STEP 4: COMPILE (Loading state) */}
        {step === STEP_COMPILE && loading && (
          <LoadingOverlay
            message="Synthesizing Final 11-Section Executive Legal Brief…"
            subtext="Deduplicating party records, structuring chronological facts, calculating statutory grounding, and compiling court-ready dossier…"
          />
        )}

        {/* STEP 5: FINAL REPORT OUTPUT (Top-down aesthetic list) */}
        {step === STEP_COMPILE && !loading && caseFile && (
          <CaseFileOutput caseFile={caseFile} onReset={handleReset} />
        )}
      </div>
    </div>
  )
}
