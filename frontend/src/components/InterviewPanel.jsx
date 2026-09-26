import React, { useEffect, useRef, useState } from 'react'
import { MessageSquare, ChevronRight, CheckCircle2, Loader2, FileCheck, FileText, Sparkles, AlertCircle, ArrowDown } from 'lucide-react'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="dot-bounce w-2 h-2 rounded-full bg-gold-400/70"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
      <span className="text-xs text-gold-400/80 ml-2 font-medium">Thinking…</span>
    </div>
  )
}

function ChatBubble({ role, content }) {
  const isAssistant = role === 'assistant'
  return (
    <div className={`flex gap-3 ${isAssistant ? '' : 'flex-row-reverse'} animate-fade-in`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
          isAssistant
            ? 'bg-gradient-to-br from-gold-400 to-gold-600 text-navy-950 shadow-sm'
            : 'bg-navy-700 text-slate-300'
        }`}
      >
        {isAssistant ? 'AI' : 'You'}
      </div>
      <div
        className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isAssistant
            ? 'bg-navy-800 border border-navy-700/80 text-slate-200 rounded-tl-sm'
            : 'bg-gradient-to-r from-navy-700 to-navy-750 text-slate-100 rounded-tr-sm border border-navy-600/50'
        }`}
      >
        {content}
      </div>
    </div>
  )
}

export default function InterviewPanel({ state, onAnswer, onSkip, loading, error, onClearError }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  const question = state?.current_question
  const history = state?.interview_history || []
  const isComplete = state?.interview_complete

  // Count user responses
  const userResponsesCount = history.filter((m) => m.role === 'user').length
  const reachedThreeMilestone = userResponsesCount >= 3

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    if (!isComplete && !loading) inputRef.current?.focus()
  }, [history, loading, isComplete])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    if (onClearError) onClearError()
    onAnswer(input.trim())
    setInput('')
  }

  const handleContinueDescribing = () => {
    inputRef.current?.focus()
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="flex flex-col h-[640px] glass-card overflow-hidden animate-slide-up shadow-2xl">
      {/* Header */}
      <div className="px-5 py-4 border-b border-navy-700/80 flex items-center gap-3 bg-navy-900/40">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center">
          <MessageSquare size={15} className="text-navy-950" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
            AI Intake Interview
            <span className="text-[11px] font-normal text-slate-400 bg-navy-800 px-2 py-0.5 rounded-full border border-navy-700">
              {userResponsesCount} / 3 recommended turns
            </span>
          </h3>
          <p className="text-xs text-slate-500">Clarifying gaps in your case</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-medium text-emerald-400">Live</span>
        </div>
      </div>

      {/* Chat scroll area */}
      <div
        className="flex-1 overflow-y-auto px-5 py-4 space-y-4"
        aria-live="polite"
        aria-label="AI intake conversation messages"
      >
        {/* Render past history */}
        {history.map((msg, i) => (
          <ChatBubble key={i} role={msg.role} content={msg.content} />
        ))}

        {/* Current question (not yet in history) */}
        {!isComplete && question && (
          <div className="space-y-1.5 animate-fade-in">
            <ChatBubble role="assistant" content={question.question} />
            {question.rationale && (
              <p className="text-xs text-slate-500 ml-11 italic flex items-center gap-1">
                <span aria-hidden="true">↳</span> {question.rationale}
              </p>
            )}
          </div>
        )}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 animate-fade-in" role="status" aria-live="polite">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center shrink-0">
              <span className="text-navy-950 text-xs font-bold" aria-hidden="true">AI</span>
            </div>
            <div className="bg-navy-800 border border-navy-700/80 rounded-2xl rounded-tl-sm">
              <TypingIndicator />
            </div>
            <span className="sr-only">AI assistant is thinking...</span>
          </div>
        )}

        {/* Error notification banner within chat */}
        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-xs animate-slide-up flex items-start gap-3">
            <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-red-200">Chat response notice</p>
              <p className="text-red-300/90 mt-0.5 leading-relaxed">{error}</p>
              <div className="flex flex-wrap items-center gap-3 mt-3">
                <button
                  type="button"
                  onClick={onSkip}
                  className="px-3 py-1.5 rounded-lg bg-gold-400 hover:bg-gold-300 text-navy-950 font-semibold text-xs transition-colors flex items-center gap-1 shadow-sm"
                >
                  <FileCheck size={13} />
                  Generate Report Now with Current Details →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Complete state */}
        {isComplete && (
          <div className="flex flex-col items-center py-8 gap-3 text-center animate-fade-in">
            <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <CheckCircle2 size={28} className="text-emerald-400" />
            </div>
            <p className="text-sm font-semibold text-emerald-400">Intake interview complete</p>
            <p className="text-xs text-slate-400 max-w-sm">
              Sufficient facts and chronology have been gathered for lawyer review.
            </p>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 3-Responses Milestone Prompt */}
      {reachedThreeMilestone && !isComplete && (
        <div className="mx-4 mb-2 p-3.5 rounded-xl bg-navy-800/95 border border-gold-400/40 shadow-lg shadow-gold-500/5 animate-slide-up">
          <div className="flex items-center gap-2 mb-1.5">
            <Sparkles size={15} className="text-gold-400" />
            <span className="text-xs font-bold text-gold-300 uppercase tracking-wider">
              Report Ready ({userResponsesCount} Responses Provided)
            </span>
          </div>
          <p className="text-xs text-slate-300 mb-3 leading-relaxed">
            You've provided {userResponsesCount} responses. You have enough details to generate your structured case report now, or continue describing further details below.
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <button
              type="button"
              onClick={onSkip}
              disabled={loading}
              id="generate-report-milestone-btn"
              className="flex-1 py-2.5 px-3.5 rounded-lg font-bold text-navy-950 text-xs
                         bg-gradient-to-r from-gold-400 to-gold-500 hover:from-gold-300 hover:to-gold-400
                         transition-all flex items-center justify-center gap-1.5 shadow-md shadow-gold-500/10"
            >
              <FileCheck size={14} />
              Generate Report Now
            </button>
            <button
              type="button"
              onClick={handleContinueDescribing}
              disabled={loading}
              className="py-2.5 px-3.5 rounded-lg font-medium text-slate-300 hover:text-white text-xs
                         bg-navy-700/80 hover:bg-navy-700 border border-navy-600 transition-all flex items-center justify-center gap-1"
            >
              Continue Describing Further Details
              <ArrowDown size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Input area */}
      {!isComplete && (
        <form onSubmit={handleSubmit} className="px-5 py-4 border-t border-navy-700/80 bg-navy-900/30">
          <div className="flex gap-3">
            <input
              ref={inputRef}
              id="interview-answer-input"
              aria-label="Your response to clarification question"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={reachedThreeMilestone ? "Type more details, or click 'Generate Report Now' above…" : "Type your answer…"}
              disabled={loading}
              className="flex-1 input-legal py-2.5 focus:outline-none focus:ring-2 focus:ring-gold-400"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              id="send-answer-btn"
              aria-label="Send clarification answer"
              className="px-4 py-2.5 rounded-lg bg-gold-500 hover:bg-gold-400 text-navy-950
                         font-semibold text-sm transition-all disabled:opacity-40
                         disabled:cursor-not-allowed flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-gold-400"
            >
              {loading ? (
                <Loader2 size={15} className="animate-spin" role="status" aria-label="Sending answer" />
              ) : (
                <ChevronRight size={15} aria-hidden="true" />
              )}
            </button>
          </div>
          <div className="mt-2.5 flex items-center justify-between text-xs text-slate-500">
            <span>Press Enter to send</span>
            <button
              type="button"
              onClick={onSkip}
              disabled={loading}
              className="text-slate-400 hover:text-gold-400 transition-colors underline font-medium"
            >
              Skip directly to case file →
            </button>
          </div>
        </form>
      )}

      {/* Compile button when complete */}
      {isComplete && (
        <div className="px-5 py-4 border-t border-navy-700/80 bg-navy-900/40">
          <button
            onClick={onSkip}
            id="compile-case-btn"
            className="w-full py-3 rounded-xl font-bold text-navy-950 text-sm
                       bg-gradient-to-r from-gold-400 to-gold-500 hover:from-gold-300 hover:to-gold-400
                       transition-all flex items-center justify-center gap-2 shadow-lg shadow-gold-500/10"
          >
            <FileCheck size={16} />
            Compile Case File
          </button>
        </div>
      )}
    </div>
  )
}

