import React, { useState } from 'react'
import {
  Users,
  Clock,
  FileText,
  AlertTriangle,
  HelpCircle,
  BookOpen,
  Scale,
  Download,
  CheckCircle,
  XCircle,
  AlertCircle,
  Shield,
  Loader2,
  DollarSign,
  Briefcase,
  Search,
  Sparkles
} from 'lucide-react'
import { api } from '../api/client'

// ---- Confidence Chip ----
function Chip({ level }) {
  const cls = {
    high: 'chip-high',
    medium: 'chip-medium',
    low: 'chip-low',
    unverified: 'chip-unverified',
  }[level?.toLowerCase()] || 'chip-unverified'
  return <span className={cls}>{level || 'unverified'}</span>
}

// ---- Source-Type Badge (Requirement 2) ----
function SourceTypeBadge({ type }) {
  const isDoc = type === 'document'
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
        isDoc
          ? 'bg-blue-500/15 text-blue-300 border border-blue-500/30'
          : 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
      }`}
    >
      <span>{isDoc ? '📄 Document' : '💬 Stated'}</span>
    </span>
  )
}

// ---- Source Tag ----
function SourceTag({ source }) {
  const isDoc = source?.type === 'document'
  return (
    <div className="flex items-center gap-2 mt-1.5">
      <SourceTypeBadge type={source?.type} />
      {source?.reference && (
        <span className="text-xs text-slate-400 italic truncate max-w-xs">
          Ref: {source.reference}
        </span>
      )}
    </div>
  )
}

// ---- Evidence Quality Badge 🟢/🟡/🔴 (Requirement 5) ----
function EvidenceQualityBadge({ score, confidence }) {
  const numScore = score != null ? Math.round(score) : null
  const isHigh = (numScore != null && numScore >= 75) || confidence?.toLowerCase() === 'high'
  const isMedium = (numScore != null && numScore >= 50 && numScore < 75) || confidence?.toLowerCase() === 'medium'

  if (isHigh) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/35">
        <span className="text-[11px]">🟢</span>
        <span>High Quality</span>
        {numScore != null && <span className="opacity-80 font-normal">({numScore}/100)</span>}
      </span>
    )
  }
  if (isMedium) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/35">
        <span className="text-[11px]">🟡</span>
        <span>Medium Quality</span>
        {numScore != null && <span className="opacity-80 font-normal">({numScore}/100)</span>}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-red-500/15 text-red-300 border border-red-500/35">
      <span className="text-[11px]">🔴</span>
      <span>Low Quality</span>
      {numScore != null && <span className="opacity-80 font-normal">({numScore}/100)</span>}
    </span>
  )
}

// ---- Triage Urgency Header Card ----
function TriageBanner({ level, score, reasons }) {
  const isHigh = level === 'HIGH'
  const isMedium = level === 'MEDIUM'

  const borderCls = isHigh
    ? 'border-red-500/40 bg-red-500/10'
    : isMedium
    ? 'border-amber-500/40 bg-amber-500/10'
    : 'border-emerald-500/40 bg-emerald-500/10'

  const textCls = isHigh ? 'text-red-400' : isMedium ? 'text-amber-400' : 'text-emerald-400'

  return (
    <div className={`rounded-xl p-5 border ${borderCls} mb-6 transition-all`}>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-navy-950/60 ${textCls}`}>
            <Shield size={22} />
          </div>
          <div>
            <span className="text-xs uppercase font-mono tracking-widest text-slate-400 block">Matter Urgency Level</span>
            <span className={`text-xl font-bold font-display ${textCls}`}>Priority: {level || 'UNSCORED'}</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs uppercase font-mono text-slate-400 block">Triage Score</span>
          <span className={`text-2xl font-mono font-bold ${textCls}`}>{score ?? 0}<span className="text-sm font-normal text-slate-500">/100</span></span>
        </div>
      </div>

      {reasons?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-white/[0.06]">
          <span className="text-xs font-semibold text-slate-400 block mb-1.5">Triage Determination Factors:</span>
          <ul className="space-y-1">
            {reasons.map((r, i) => (
              <li key={i} className="text-xs text-slate-300 flex items-start gap-2">
                <span className={`shrink-0 mt-0.5 ${textCls}`}>•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ---- Clean Top-down Section Header ----
function SectionHeader({ number, title, icon: Icon, badge, count }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 pb-3 mb-4 border-b border-white/[0.08]">
      <div className="flex items-center gap-3">
        <span className="section-tag font-mono">{number}</span>
        {Icon && <Icon size={18} className="text-gold-400" />}
        <h3 className="font-display font-bold text-lg text-slate-100">{title}</h3>
      </div>
      <div className="flex items-center gap-2">
        {count !== undefined && (
          <span className="px-2 py-0.5 rounded-full bg-navy-800 text-xs font-mono text-slate-400 border border-navy-700">
            {count} {count === 1 ? 'item' : 'items'}
          </span>
        )}
        {badge && (
          <span className="px-2.5 py-0.5 rounded-full bg-gold-400/10 text-gold-400 text-xs font-semibold border border-gold-400/25">
            {badge}
          </span>
        )}
      </div>
    </div>
  )
}

// ---- Download JSON Helper ----
function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function CaseFileOutput({ caseFile, onReset }) {
  if (!caseFile) return null

  const s1 = caseFile.section_1_executive_summary
  const s2 = caseFile.section_2_parties
  const s3 = caseFile.section_3_chronology
  const s4 = caseFile.section_4_user_reported_facts
  const s5 = caseFile.section_5_document_supported_facts
  const s6 = caseFile.section_6_claims
  const s7 = caseFile.section_7_evidence_map
  const s8 = caseFile.section_8_inconsistencies
  const s9 = caseFile.section_9_missing_information
  const s10 = caseFile.section_10_legal_areas
  const s11 = caseFile.section_11_lawyer_questions
  const meta = caseFile.meta

  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [pdfError, setPdfError] = useState(null)

  const handleDownloadPDF = async () => {
    if (!meta?.session_id) return
    setDownloadingPdf(true)
    setPdfError(null)
    try {
      await api.downloadPDF(meta.session_id, `case-file-${meta.session_id.slice(0, 8)}.pdf`)
    } catch (err) {
      console.error('PDF download error:', err)
      setPdfError(err.message || 'Failed to download PDF')
    } finally {
      setDownloadingPdf(false)
    }
  }

  const scrollToSection = (id) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  // Find search query from RAG results if available
  const sampleQuery = s10?.rag_results?.find((r) => r.potentially_relevant_query)?.potentially_relevant_query

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl mx-auto pb-16">
      {/* Sticky Document Control Header */}
      <div className="sticky top-20 z-20 bg-navy-950/90 backdrop-blur-md rounded-2xl p-4 border border-white/[0.08] shadow-2xl flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h2 className="text-base font-bold font-display text-white">Compiled Case Dossier</h2>
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-navy-800 text-slate-400 border border-navy-700">
              Ref: {meta?.session_id ? meta.session_id.slice(0, 8) : 'Brief'}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Standardized 11-Section Executive Brief · Generated {meta?.compiled_at ? new Date(meta.compiled_at).toLocaleTimeString() : ''}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleDownloadPDF}
            id="download-pdf-btn"
            disabled={downloadingPdf}
            aria-label={downloadingPdf ? 'Exporting court-ready PDF brief' : 'Download court-ready PDF brief'}
            className="btn-gold flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold cursor-pointer disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-gold-400"
          >
            {downloadingPdf ? (
              <Loader2 size={14} className="animate-spin" role="status" aria-label="Exporting PDF brief" />
            ) : (
              <FileText size={14} aria-hidden="true" />
            )}
            <span>{downloadingPdf ? 'Exporting PDF…' : 'Download PDF Report'}</span>
          </button>

          <button
            onClick={() => downloadJSON(caseFile, `case-file-${meta?.session_id?.slice(0, 8)}.json`)}
            id="download-case-btn"
            aria-label="Download raw case brief JSON data"
            className="btn-glass flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer focus:outline-none focus:ring-2 focus:ring-gold-400"
          >
            <Download size={13} aria-hidden="true" />
            <span>JSON</span>
          </button>

          {onReset && (
            <button
              onClick={onReset}
              aria-label="Start new case analysis"
              className="text-xs px-3 py-2 rounded-xl bg-navy-900 border border-navy-700 hover:border-slate-500 text-slate-300 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-gold-400"
            >
              New Case
            </button>
          )}
        </div>
      </div>

      {/* PDF Error Alert */}
      {pdfError && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <AlertCircle size={15} className="shrink-0" />
          <span>PDF Export failed: {pdfError}. Please verify ReportLab is installed in the backend.</span>
        </div>
      )}

      {/* Quick Jump Anchor Strip */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none text-xs text-slate-400">
        <span className="text-[11px] font-mono text-slate-500 uppercase shrink-0 mr-1">Quick Jump:</span>
        {[
          { label: '01 Summary', target: 'section-1' },
          { label: '02 Parties', target: 'section-2' },
          { label: '03 Timeline', target: 'section-3' },
          { label: '04 Facts', target: 'section-4' },
          { label: '06 Claims', target: 'section-6' },
          { label: '07 Evidence', target: 'section-7' },
          { label: '08 Self-Review', target: 'section-8' },
          { label: '10 Statutes', target: 'section-10' },
          { label: '11 Questions', target: 'section-11' },
        ].map((item) => (
          <button
            key={item.target}
            onClick={() => scrollToSection(item.target)}
            className="shrink-0 px-2.5 py-1 rounded-lg bg-navy-900/60 border border-white/[0.06] hover:border-gold-500/30 hover:text-gold-400 transition-colors font-mono text-[11px]"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Disclaimer Banner */}
      <div className="disclaimer-banner rounded-xl p-4">
        <div className="flex gap-3 items-start">
          <Scale size={16} className="text-gold-400 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-300 leading-relaxed">{meta?.disclaimer}</p>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 1 — Executive Summary */}
      {/* ============================================================ */}
      <div id="section-1" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="01" title="Executive Summary" icon={Shield} badge={s1?.triage_level} />
        
        <TriageBanner level={s1?.triage_level} score={s1?.triage_score} reasons={s1?.triage_reasons} />

        <p className="text-sm text-slate-200 mb-5 leading-relaxed bg-navy-950/40 p-4 rounded-xl border border-navy-800/80">
          {s1?.summary_note}
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            { label: 'Parties Identified', value: s1?.parties_count },
            { label: 'Chronology Events', value: s1?.events_count },
            { label: 'Legal Claims', value: s1?.claims_count },
            { label: 'Evidence Docs', value: s1?.evidence_count },
            { label: 'Information Gaps', value: s1?.missing_info_count },
            { label: 'Contradictions Flagged', value: s1?.contradictions_count },
          ].map(({ label, value }) => (
            <div key={label} className="bg-navy-950/60 rounded-xl p-3.5 text-center border border-navy-800/80">
              <p className="text-2xl font-bold font-mono text-gold-400">{value ?? 0}</p>
              <p className="text-[11px] text-slate-400 mt-1 uppercase font-medium">{label}</p>
            </div>
          ))}
        </div>

        {/* Static Capabilities Used Chip Row (Requirement 6) */}
        <div className="mt-5 pt-4 border-t border-white/[0.06]">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2.5">
            Capabilities Used:
          </span>
          <div className="flex flex-wrap gap-2 text-xs">
            {[
              { label: 'Gemini 3.8 Multimodal Extraction', icon: '⚡' },
              { label: 'XGBoost 21-Feature Evidence Reliability Model', icon: '🌲' },
              { label: 'Statutory Vector RAG (Karnataka Rent Act & MTA)', icon: '⚖️' },
              { label: 'Adversarial Self-Critique Verification', icon: '🛡️' },
              { label: 'Deterministic Urgent Triage Scoring', icon: '🎯' },
              { label: 'Court-Ready Document Synthesis', icon: '📄' },
            ].map((cap, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy-950/80 border border-navy-800 text-slate-300 text-[11px] font-medium"
              >
                <span>{cap.icon}</span>
                <span>{cap.label}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 2 — Parties */}
      {/* ============================================================ */}
      <div id="section-2" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="02" title="Parties" icon={Users} count={s2?.parties?.length} />
        
        {s2?.parties?.length === 0 && (
          <p className="text-sm text-slate-500 italic py-2">No parties identified.</p>
        )}

        <div className="space-y-3">
          {s2?.parties?.map((p, i) => (
            <div key={i} className="bg-navy-950/60 border border-navy-800/80 rounded-xl p-4 transition-colors hover:border-navy-700">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-slate-100 text-base">{p.name}</p>
                    <span className="text-[11px] text-gold-400 font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-gold-400/10 border border-gold-400/20">
                      {p.role}
                    </span>
                    {/* Requirement 2: Source-type badge */}
                    <SourceTypeBadge type={p.source?.type} />
                  </div>
                  {p.contact && <p className="text-xs text-slate-300 mt-1.5 flex items-center gap-1.5">📞 <span>{p.contact}</span></p>}
                  {p.address && <p className="text-xs text-slate-300 mt-1 flex items-center gap-1.5">📍 <span>{p.address}</span></p>}
                  <div className="mt-2">
                    <SourceTag source={p.source} />
                  </div>
                </div>
                <Chip level={p.confidence} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 3 — Chronology */}
      {/* ============================================================ */}
      <div id="section-3" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="03" title="Chronology" icon={Clock} count={s3?.events?.length} />
        <p className="text-xs text-slate-500 italic mb-4">{s3?.note}</p>

        {s3?.events?.length === 0 && (
          <p className="text-sm text-slate-500 italic py-2">No events extracted.</p>
        )}

        <div className="relative pl-2">
          {s3?.events?.map((ev, i) => (
            <div key={i} className="relative pl-7 pb-6 last:pb-2">
              {i < s3.events.length - 1 && <div className="timeline-line" />}
              <div className="absolute left-0 top-1 w-5 h-5 rounded-full border-2 border-gold-400/50 bg-navy-950 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-gold-400" />
              </div>
              <div className="bg-navy-950/50 border border-navy-800/80 rounded-xl p-4">
                <div className="flex items-start justify-between gap-3 mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-gold-400">
                      {ev.date_parsed || ev.date_raw || 'Date unknown'}
                    </span>
                    {/* Requirement 2: Source-type badge */}
                    <SourceTypeBadge type={ev.source?.type} />
                  </div>
                  <Chip level={ev.confidence} />
                </div>
                <p className="text-sm text-slate-200 leading-relaxed mb-2">{ev.description}</p>
                <SourceTag source={ev.source} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 4 — User-Reported Facts */}
      {/* ============================================================ */}
      <div id="section-4" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="04" title="Facts Reported by User (Unverified)" icon={FileText} count={s4?.facts?.length} />
        <p className="text-xs text-slate-500 italic mb-4">{s4?.note}</p>

        {s4?.facts?.length === 0 && (
          <p className="text-sm text-slate-500 italic py-2">No user-reported facts recorded.</p>
        )}

        <ul className="space-y-2.5">
          {s4?.facts?.map((f, i) => (
            <li key={i} className="flex gap-3 items-start text-sm text-slate-200 bg-navy-950/60 rounded-xl px-4 py-3 border border-navy-800/80">
              <span className="text-gold-400 font-mono text-xs font-bold mt-0.5">{String(i + 1).padStart(2, '0')}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {f.date && <span className="text-xs font-mono text-gold-400/90 font-semibold">[{f.date}]</span>}
                  {/* Requirement 2: Source-type badge */}
                  <SourceTypeBadge type="user_statement" />
                </div>
                <span>{f.fact}</span>
              </div>
              <Chip level={f.confidence} />
            </li>
          ))}
        </ul>
      </div>

      {/* ============================================================ */}
      {/* SECTION 5 — Document-Supported Facts */}
      {/* ============================================================ */}
      <div id="section-5" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="05" title="Document-Supported Facts" icon={FileText} count={s5?.facts?.length} />
        <p className="text-xs text-slate-500 italic mb-4">{s5?.note}</p>

        {(!s5?.facts || s5.facts.length === 0) && (
          <div className="p-4 rounded-xl bg-navy-950/40 border border-navy-800 text-center">
            <p className="text-xs text-slate-500 italic">No document-supported facts extracted yet. Upload agreement contracts or bank receipts to corroborate user facts.</p>
          </div>
        )}

        <ul className="space-y-2.5">
          {s5?.facts?.map((f, i) => (
            <li key={i} className="flex gap-3 items-start text-sm text-slate-200 bg-navy-950/60 rounded-xl px-4 py-3 border border-navy-800/80">
              <span className="text-emerald-400 font-mono text-xs font-bold mt-0.5">{String(i + 1).padStart(2, '0')}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {f.date && <span className="text-xs font-mono text-gold-400 font-semibold">[{f.date}]</span>}
                  {/* Requirement 2: Source-type badge */}
                  <SourceTypeBadge type="document" />
                </div>
                <span>{f.fact}</span>
                {f.source_document && (
                  <p className="text-xs text-slate-400 mt-1 italic flex items-center gap-1 font-mono">
                    <span>📄 Source:</span> <span className="text-slate-300">{f.source_document}</span>
                  </p>
                )}
              </div>
              <Chip level={f.confidence} />
            </li>
          ))}
        </ul>
      </div>

      {/* ============================================================ */}
      {/* SECTION 6 — Claims & Assertions */}
      {/* ============================================================ */}
      <div id="section-6" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="06" title="Claims and Assertions" icon={Scale} count={s6?.claims?.length} />
        <p className="text-xs text-slate-500 italic mb-4">{s6?.note}</p>

        {s6?.claims?.length === 0 && <p className="text-sm text-slate-500 italic py-2">No claims identified.</p>}

        <div className="space-y-3">
          {s6?.claims?.map((c, i) => (
            <div key={i} className="bg-navy-950/60 border border-navy-800/80 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-slate-100 flex-1 font-medium leading-relaxed">{c.description}</p>
                <Chip level={c.confidence} />
              </div>
              {c.legal_basis_mentioned && (
                <div className="mt-2.5 p-2.5 rounded-lg bg-navy-900/80 border border-navy-800 text-xs text-slate-300">
                  <span className="text-gold-400 font-semibold block mb-0.5">Legal Basis Asserted:</span>
                  <span className="italic">{c.legal_basis_mentioned}</span>
                </div>
              )}
              <div className="mt-2.5">
                <SourceTag source={c.source} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 7 — Evidence Map & ML Forensics */}
      {/* ============================================================ */}
      <div id="section-7" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="07" title="Evidence Map &amp; ML Forensics" icon={FileText} count={s7?.evidence?.length} />

        {(!s7?.evidence || s7.evidence.length === 0) && (
          <p className="text-sm text-slate-500 italic py-2">No evidence uploaded.</p>
        )}

        {/* Evidence List with Requirement 5: Quality Badge (🟢/🟡/🔴) */}
        <div className="space-y-4 mb-6">
          {s7?.evidence?.map((e, i) => (
            <div key={i} className="bg-navy-950/60 border border-navy-800/80 rounded-xl p-5 hover:border-navy-700 transition-colors">
              <div className="flex flex-wrap items-center justify-between gap-2.5 mb-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-300 uppercase font-semibold border border-navy-700">
                    {e.detected_type || e.type}
                  </span>
                  <p className="font-semibold text-slate-100 text-sm">{e.filename}</p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Requirement 5: Evidence Quality Badge */}
                  <EvidenceQualityBadge score={e.quality_score} confidence={e.confidence} />
                  <Chip level={e.confidence} />
                </div>
              </div>

              <p className="text-xs text-slate-300 mb-3 leading-relaxed">{e.description}</p>

              {/* Machine Learning Feature Signals */}
              {e.feature_signals && (
                <div className="pt-3 border-t border-white/[0.06]">
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="text-slate-500 font-medium mr-1 font-mono">21-Feature Signals:</span>
                    {e.feature_signals.ocr_quality && (
                      <span className="px-2 py-0.5 rounded bg-navy-800 text-slate-300 border border-navy-700">
                        OCR: {e.feature_signals.ocr_quality}
                      </span>
                    )}
                    {e.feature_signals.has_date && (
                      <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                        ✓ Date Verified
                      </span>
                    )}
                    {e.feature_signals.has_parties && (
                      <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                        ✓ Parties Matched
                      </span>
                    )}
                    {e.feature_signals.has_financials && (
                      <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                        ✓ Financials
                      </span>
                    )}
                    {e.feature_signals.timeline_aligned && (
                      <span className="px-2 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800/40">
                        ✓ Timeline Aligned
                      </span>
                    )}
                    {e.feature_signals.contradiction_flagged && (
                      <span className="px-2 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-800/40">
                        ⚠ Contradiction Flagged
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Financials Sub-block */}
        {s7?.financials?.length > 0 && (
          <div className="pt-4 border-t border-white/[0.06]">
            <h4 className="text-xs font-semibold text-gold-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <DollarSign size={14} />
              <span>Extracted Financial Figures</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {s7?.financials?.map((f, i) => (
                <div key={i} className="flex items-center justify-between bg-navy-950/60 rounded-xl px-4 py-3 border border-navy-800/80">
                  <div className="pr-2">
                    <span className="text-xs text-slate-300 block">{f.label}</span>
                    {f.date && <span className="text-[10px] text-slate-500 font-mono">Date: {f.date}</span>}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="font-mono font-bold text-gold-400 text-sm">
                      {f.amount_inr != null ? `₹${Number(f.amount_inr).toLocaleString('en-IN')}` : 'Unknown'}
                    </span>
                    <Chip level={f.confidence} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ============================================================ */}
      {/* SECTION 8 — Inconsistencies & Critique Findings */}
      {/* ============================================================ */}
      <div id="section-8" className="dossier-section p-6 sm:p-7">
        <SectionHeader
          number="08"
          title="Potential Inconsistencies"
          icon={AlertTriangle}
          count={(s8?.inconsistencies?.length || 0) + (s8?.critique_findings?.length || 0)}
        />

        {/* Requirement 3: Always-visible "AI Self-Review" Header */}
        <div
          className={`rounded-xl p-4 mb-4 border transition-all ${
            (!s8?.critique_findings || s8.critique_findings.length === 0)
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              {(!s8?.critique_findings || s8.critique_findings.length === 0) ? (
                <CheckCircle size={18} className="text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle size={18} className="text-amber-400 shrink-0" />
              )}
              <span className="font-semibold text-sm">
                AI Self-Review: {(!s8?.critique_findings || s8.critique_findings.length === 0) ? 'No issues detected' : `${s8.critique_findings.length} issue(s) detected`}
              </span>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-navy-950/60 font-semibold border border-white/10">
              {(!s8?.critique_findings || s8.critique_findings.length === 0) ? 'Passed' : 'Review Required'}
            </span>
          </div>

          {/* Show findings when not empty */}
          {s8?.critique_findings && s8.critique_findings.length > 0 && (
            <div className="mt-3 pt-3 border-t border-amber-500/20 space-y-2">
              {s8.critique_findings.map((f, i) => (
                <div key={i} className="text-xs text-slate-200 flex items-start gap-2">
                  <span className="text-amber-400 font-bold shrink-0">•</span>
                  <div>
                    <span className="font-semibold uppercase text-amber-300 mr-1.5">{f.type?.replace('_', ' ')}:</span>
                    <span>{f.description}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <p className="text-xs text-slate-500 italic mb-4">{s8?.scope_note}</p>

        {(!s8?.inconsistencies || s8.inconsistencies.length === 0) &&
          (!s8?.critique_findings || s8.critique_findings.length === 0) && (
            <div className="p-4 rounded-xl bg-navy-950/40 border border-navy-800 text-center">
              <p className="text-sm text-emerald-400/80 font-medium">✓ No material inconsistencies or date/amount mismatches detected.</p>
            </div>
          )}

        {s8?.inconsistencies?.map((c, i) => (
          <div key={i} className="mb-3 bg-amber-500/10 border border-amber-500/25 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle size={15} className="text-amber-400" />
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">{c.type?.replace('_', ' ')}</span>
            </div>
            <p className="text-sm text-slate-200 mb-3">{c.description}</p>
            <div className="flex flex-wrap gap-2 text-xs text-slate-400 font-mono">
              <span className="bg-navy-900 px-2.5 py-1 rounded border border-navy-700">Source A: {c.item_a}</span>
              <span className="bg-navy-900 px-2.5 py-1 rounded border border-navy-700">Source B: {c.item_b}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ============================================================ */}
      {/* SECTION 9 — Missing Information */}
      {/* ============================================================ */}
      <div id="section-9" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="09" title="Missing Information" icon={HelpCircle} count={s9?.missing?.length} />

        {(!s9?.missing || s9.missing.length === 0) && (
          <p className="text-sm text-slate-500 italic py-2">No critical missing information gaps identified.</p>
        )}

        <div className="space-y-2.5">
          {s9?.missing?.map((m, i) => (
            <div key={i} className="flex gap-3 items-start bg-navy-950/60 border border-navy-800/80 rounded-xl px-4 py-3">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-400 uppercase font-semibold shrink-0">
                {m.category}
              </span>
              <p className="text-sm text-slate-200 flex-1 leading-relaxed">{m.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 10 — Legal Areas (RAG Grounding) */}
      {/* ============================================================ */}
      <div id="section-10" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="10" title="Potentially Relevant Legal Areas" icon={BookOpen} count={s10?.rag_results?.length} />

        <div className="disclaimer-banner rounded-xl p-3.5 mb-4">
          <p className="text-xs text-slate-300 leading-relaxed italic">{s10?.disclaimer}</p>
        </div>

        {/* Requirement 4: Visible labeled query line before RAG results */}
        {sampleQuery && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-navy-950/80 border border-gold-500/25 flex items-center gap-2.5 text-xs">
            <Search size={14} className="text-gold-400 shrink-0" />
            <div className="flex-1 truncate">
              <span className="text-slate-400 font-semibold mr-1.5 uppercase font-mono text-[10px]">
                RAG Search Query:
              </span>
              <span className="text-gold-300 font-mono italic">"{sampleQuery}"</span>
            </div>
          </div>
        )}

        {(!s10?.rag_results || s10.rag_results.length === 0) && (
          <p className="text-sm text-slate-500 italic py-2">
            No statutory RAG results retrieved — ensure corpus/ directory has legal txt files and FAISS index is active.
          </p>
        )}

        {/* RAG Results with Requirement 4 Percentage Progress Bar */}
        <div className="space-y-3.5">
          {s10?.rag_results?.map((r, i) => {
            const pct = Math.round((r.relevance_score || 0) * 100)
            const queryLine = r.potentially_relevant_query || sampleQuery

            return (
              <div key={i} className="bg-navy-950/60 border border-navy-800/80 rounded-xl p-4 hover:border-navy-700 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-2.5">
                  <span className="text-xs font-bold text-gold-400 tracking-wide">{r.legal_area}</span>
                  
                  {/* Requirement 4: Relevance score as percentage and progress bar */}
                  <div className="flex items-center gap-2 bg-navy-900 px-3 py-1 rounded-lg border border-navy-800">
                    <span className="text-[10px] text-slate-400 uppercase font-mono font-medium">Relevance:</span>
                    <div className="w-20 bg-navy-950 rounded-full h-2 overflow-hidden border border-navy-700">
                      <div
                        className="bg-gradient-to-r from-gold-500 to-emerald-400 h-full rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(5, pct))}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono font-bold text-emerald-400">{pct}%</span>
                  </div>
                </div>

                {/* Requirement 4: Visible labeled query line per item if specific */}
                {queryLine && (
                  <p className="text-[11px] text-slate-400 font-mono mb-2 flex items-center gap-1.5">
                    <span className="text-slate-500 uppercase">Query:</span>
                    <span className="text-slate-300 italic">"{queryLine}"</span>
                  </p>
                )}

                <p className="text-xs text-slate-400 font-mono mb-2">Source: {r.source_document}</p>
                <div className="bg-navy-900/60 rounded-lg p-3 border border-navy-800 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-mono">
                  {r.excerpt}
                </div>
                <p className="text-xs text-amber-400/80 italic mt-2.5 flex items-center gap-1.5">
                  <span>⚠️ {r.hedging_note}</span>
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* ============================================================ */}
      {/* SECTION 11 — Questions for Legal Practitioner */}
      {/* ============================================================ */}
      <div id="section-11" className="dossier-section p-6 sm:p-7">
        <SectionHeader number="11" title="Questions for a Human Legal Practitioner" icon={HelpCircle} count={s11?.questions?.length} />
        <p className="text-xs text-slate-500 italic mb-4">{s11?.note}</p>

        {(!s11?.questions || s11.questions.length === 0) && (
          <p className="text-sm text-slate-500 italic py-2">No specific questions generated.</p>
        )}

        <ul className="space-y-2.5">
          {s11?.questions?.map((q, i) => (
            <li key={i} className="flex gap-3 items-start text-sm text-slate-200 bg-navy-950/60 rounded-xl px-4 py-3.5 border border-navy-800/80">
              <span className="text-gold-400 font-bold font-mono shrink-0 text-xs px-2 py-0.5 rounded bg-gold-400/10 border border-gold-400/20 mt-0.5">
                Q{i + 1}
              </span>
              <span className="leading-relaxed">{q}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Footer Details */}
      <div className="text-center pt-6 pb-8 border-t border-white/[0.06] text-xs text-slate-500">
        <p>
          Case File Document · Session {meta?.session_id} · Model: {meta?.model_used}
        </p>
        <p className="text-[11px] text-slate-600 mt-1">
          Compiled on {meta?.compiled_at ? new Date(meta.compiled_at).toUTCString() : ''}
        </p>
      </div>
    </div>
  )
}
