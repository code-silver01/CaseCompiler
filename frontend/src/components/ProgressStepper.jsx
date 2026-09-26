import React from 'react'
import { CheckCircle, Circle, Loader2, Sparkles } from 'lucide-react'

const STEPS = [
  { id: 'describe', label: 'Describe Case' },
  { id: 'extract', label: 'AI Extraction' },
  { id: 'interview', label: 'Interview' },
  { id: 'compile', label: 'Case File' },
]

const EXTRACTION_SUB_STEPS = [
  { id: 'extraction', label: 'Multimodal Extraction' },
  { id: 'self_critique', label: 'AI Self-Critique' },
  { id: 'rag_query', label: 'RAG Query Generation' },
  { id: 'retrieval', label: 'Statutory Retrieval' },
]

const PHASE_ORDER = ['extraction', 'self_critique', 'rag_query', 'retrieval', 'complete']

export default function ProgressStepper({ currentStep, activePhase = 'extraction' }) {
  const currentIndex = STEPS.findIndex((s) => s.id === currentStep)
  const currentPhaseIndex = PHASE_ORDER.indexOf(activePhase) !== -1
    ? PHASE_ORDER.indexOf(activePhase)
    : 0

  return (
    <div className="mb-8">
      {/* Primary Stepper Bar */}
      <div className="flex items-center justify-center gap-0">
        {STEPS.map((step, i) => {
          const done = i < currentIndex
          const active = i === currentIndex
          const pending = i > currentIndex

          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${
                    active ? 'step-active shadow-lg shadow-gold-500/20' : done ? 'step-done' : 'step-pending'
                  }`}
                >
                  {done ? (
                    <CheckCircle size={16} />
                  ) : active ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <span className="text-xs font-mono font-semibold">{i + 1}</span>
                  )}
                </div>
                <span
                  className={`text-xs font-medium whitespace-nowrap transition-colors ${
                    active ? 'text-gold-400' : done ? 'text-emerald-400' : 'text-slate-500'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`h-px w-12 mx-1 mb-5 transition-all duration-500 ${
                    done ? 'bg-emerald-500/50' : 'bg-navy-700'
                  }`}
                />
              )}
            </React.Fragment>
          )
        })}
      </div>

      {/* Live sub-step checklist under 'AI Extraction' */}
      {currentStep === 'extract' && (
        <div className="mt-5 p-4 bg-navy-900/90 border border-gold-500/30 rounded-2xl shadow-xl max-w-sm mx-auto animate-slide-up backdrop-blur-md">
          <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-white/[0.08]">
            <span className="text-[11px] font-mono uppercase tracking-wider text-gold-400 font-bold flex items-center gap-1.5">
              <Sparkles size={13} className="text-gold-400" />
              Live Extraction Phases
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {Math.min(4, Math.max(1, currentPhaseIndex + 1))} of 4
            </span>
          </div>

          <div className="space-y-1.5">
            {EXTRACTION_SUB_STEPS.map((sub, idx) => {
              const isSubDone = currentPhaseIndex > idx || activePhase === 'complete'
              const isSubActive = currentPhaseIndex === idx && activePhase !== 'complete'
              const isSubPending = currentPhaseIndex < idx

              return (
                <div
                  key={sub.id}
                  className={`flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition-all ${
                    isSubActive
                      ? 'bg-gold-500/10 text-gold-300 font-semibold border border-gold-500/30'
                      : isSubDone
                      ? 'text-emerald-400 font-medium'
                      : 'text-slate-500'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {isSubDone ? (
                      <CheckCircle size={14} className="text-emerald-400 shrink-0" />
                    ) : isSubActive ? (
                      <Loader2 size={14} className="text-gold-400 animate-spin shrink-0" />
                    ) : (
                      <Circle size={14} className="text-slate-600 shrink-0" />
                    )}
                    <span>{sub.label}</span>
                  </div>
                  <span className="font-mono text-[10px] uppercase font-bold">
                    {isSubDone ? '✓' : isSubActive ? 'In progress' : 'Pending'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
