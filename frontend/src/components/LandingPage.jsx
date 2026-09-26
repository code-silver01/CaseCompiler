import React, { useState } from 'react'
import {
  Scale,
  Gavel,
  ArrowRight,
  Shield,
  FileText,
  Brain,
  CheckCircle,
  HelpCircle,
  Clock,
  Sparkles,
  ChevronRight,
  UploadCloud,
  FileCheck,
  AlertTriangle,
  Lock,
  ExternalLink,
  BookOpen,
  Loader2
} from 'lucide-react'
import { loadSampleImages } from './CaseInput'

// Exact sample Bangalore tenancy dispute text
const SAMPLE_DISPUTE = `I rented a 2BHK flat (Flat 302, HSR Layout Sector 2, Bangalore) from my landlord Suresh Kumar starting 1st April 2023. At the time of signing the agreement, I paid a refundable security deposit of Rs. 1,00,000 via bank transfer. My monthly rent was Rs. 22,000, which I paid regularly without default.

On 12th February 2024, Suresh Kumar sent me a WhatsApp notice asking me to vacate the flat by 15th February 2024. I vacated on 15th February and handed over keys in good condition. However, Suresh Kumar is refusing to refund my full deposit and is withholding Rs. 45,000 claiming bogus painting and deep-cleaning charges, which was never agreed to in our rental agreement (clause says normal wear and tear is landlord responsibility). He has only offered to return Rs. 55,000. I need my remaining Rs. 45,000 refunded immediately.`

export default function LandingPage({ onStartCase, onStartWithTemplate }) {
  const [loadingSample, setLoadingSample] = useState(false)

  const handleScrollToHowItWorks = () => {
    const el = document.getElementById('how-it-works')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const handleLaunchSample = async () => {
    setLoadingSample(true)
    try {
      const files = await loadSampleImages()
      if (onStartWithTemplate) {
        onStartWithTemplate(SAMPLE_DISPUTE, files)
      } else {
        onStartCase()
      }
    } catch (err) {
      console.warn('Failed to load sample images:', err)
      if (onStartWithTemplate) {
        onStartWithTemplate(SAMPLE_DISPUTE, [])
      } else {
        onStartCase()
      }
    } finally {
      setLoadingSample(false)
    }
  }

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 selection:bg-gold-400/20 selection:text-gold-300">
      {/* Ambient background glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-gradient-to-b from-gold-500/10 via-navy-600/10 to-transparent rounded-full blur-3xl" />
        <div className="absolute top-[35%] -left-48 w-96 h-96 bg-navy-600/20 rounded-full blur-3xl" />
        <div className="absolute top-[60%] -right-48 w-96 h-96 bg-gold-500/5 rounded-full blur-3xl" />
      </div>

      {/* ---- Navigation Bar ---- */}
      <nav className="relative z-20 border-b border-white/[0.06] bg-navy-950/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center shadow-lg shadow-gold-500/20 ring-1 ring-gold-400/30">
              <Scale size={20} className="text-navy-950" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-bold text-xl text-slate-100 tracking-tight">CaseCompiler</span>
                <span className="text-[10px] uppercase font-mono tracking-widest px-2 py-0.5 rounded-full bg-gold-400/10 text-gold-400 border border-gold-400/25">
                  AI Legal Tech
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide">Enterprise Case Dossier Intelligence</p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-300">
            <button onClick={handleScrollToHowItWorks} className="hover:text-gold-400 transition-colors">
              How It Works
            </button>
            <a href="#features" className="hover:text-gold-400 transition-colors">
              Legal Engine
            </a>
            <a href="#sample-case" className="hover:text-gold-400 transition-colors">
              Sample Brief
            </a>
            <a href="#compliance" className="hover:text-gold-400 transition-colors">
              Guardrails
            </a>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onStartCase}
              className="btn-gold px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 cursor-pointer"
            >
              <span>Build My Case</span>
              <ArrowRight size={15} />
            </button>
          </div>
        </div>
      </nav>

      {/* ---- HERO SECTION ---- */}
      <section className="relative z-10 pt-16 pb-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-4xl mx-auto mb-14">
          {/* Tag Pill */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-navy-900 border border-gold-500/30 text-xs text-gold-400 mb-6 shadow-inner animate-fade-in">
            <Sparkles size={13} className="text-gold-400" />
            <span className="font-semibold tracking-wide">Next-Generation AI Legal Case Organization</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ml-1" />
          </div>

          {/* Requested Hero Headline */}
          <h1 className="font-display text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.15] mb-6">
            CaseCompiler — <br className="hidden sm:inline" />
            <span className="gold-text">Turn your story into a lawyer-readable case file.</span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed mb-10 font-normal">
            No more unstructured emails or messy WhatsApp screenshots. CaseCompiler extracts legal entities, runs 21-feature ML evidence scoring, and compiles an authoritative 11-section legal dossier with statutory citations in seconds.
          </p>

          {/* Requested Two CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 max-w-md mx-auto">
            <button
              onClick={onStartCase}
              id="hero-cta-build"
              className="btn-gold w-full sm:w-auto px-8 py-3.5 rounded-xl text-base font-bold flex items-center justify-center gap-2 cursor-pointer shadow-xl shadow-gold-500/25"
            >
              <span>Build My Case</span>
              <ArrowRight size={18} />
            </button>
            <button
              onClick={handleScrollToHowItWorks}
              id="hero-cta-how-it-works"
              className="btn-glass w-full sm:w-auto px-7 py-3.5 rounded-xl text-base font-semibold flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>See How It Works</span>
              <ChevronRight size={17} className="text-gold-400" />
            </button>
          </div>

          {/* Trust strip */}
          <div className="mt-12 pt-8 border-t border-white/[0.06] flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs font-mono text-slate-400">
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-emerald-400" />
              <span>11 Standardized Sections</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-gold-400" />
              <span>XGBoost ML Evidence Scorer</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-emerald-400" />
              <span>Karnataka &amp; Central Tenancy Acts</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={14} className="text-blue-400" />
              <span>Court-Ready PDF Brief</span>
            </div>
          </div>
        </div>

        {/* ---- Interactive Dossier Mockup Preview ---- */}
        <div className="relative max-w-5xl mx-auto mt-6">
          <div className="absolute -inset-1.5 bg-gradient-to-r from-gold-500/20 via-navy-600/30 to-gold-400/20 rounded-3xl blur-xl opacity-75" />
          <div className="relative rounded-2xl bg-navy-900/90 border border-gold-400/25 shadow-2xl overflow-hidden backdrop-blur-xl">
            {/* Mock Window Top Bar */}
            <div className="bg-navy-950/80 px-6 py-3.5 border-b border-navy-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-3 text-xs font-mono text-slate-400">case-dossier-preview.pdf · Bangalore Tenancy Matter</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold">
                  Triage: MEDIUM (60/100)
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-navy-800 text-slate-400">11 Sections</span>
              </div>
            </div>

            {/* Dossier Mock Content */}
            <div className="p-6 sm:p-8 space-y-6">
              {/* Executive Summary Snippet */}
              <div className="bg-navy-950/60 rounded-xl p-5 border border-navy-800">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="section-tag">01</span>
                    <h3 className="font-semibold text-slate-100 text-sm">Executive Summary</h3>
                  </div>
                  <span className="text-xs text-gold-400 font-mono">₹1,00,000 Security Deposit Disputed</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed mb-4">
                  Case involves 2 identified parties, 1 claim(s), and 1 piece(s) of verified evidence. High financial stake: ₹1,00,000 (Refundable Security Deposit) withheld for painting contrary to lease covenants.
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="bg-navy-900/80 rounded-lg p-2.5 border border-navy-800">
                    <span className="text-xs text-slate-500 block">Parties</span>
                    <span className="text-base font-bold text-slate-100">2 Verified</span>
                  </div>
                  <div className="bg-navy-900/80 rounded-lg p-2.5 border border-navy-800">
                    <span className="text-xs text-slate-500 block">Withheld Sum</span>
                    <span className="text-base font-bold text-gold-400">₹45,000</span>
                  </div>
                  <div className="bg-navy-900/80 rounded-lg p-2.5 border border-navy-800">
                    <span className="text-xs text-slate-500 block">ML Evidence Score</span>
                    <span className="text-base font-bold text-emerald-400">64.3 / 100</span>
                  </div>
                  <div className="bg-navy-900/80 rounded-lg p-2.5 border border-navy-800">
                    <span className="text-xs text-slate-500 block">Statutory Grounding</span>
                    <span className="text-base font-bold text-blue-400">§16 Karn. Act</span>
                  </div>
                </div>
              </div>

              {/* Two columns: Parties & Evidence Map with ML */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-navy-950/60 rounded-xl p-5 border border-navy-800">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="section-tag">02</span>
                    <h4 className="text-sm font-semibold text-slate-200">Parties (Deduplicated)</h4>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-800 flex justify-between items-center">
                      <div>
                        <span className="font-semibold text-slate-200">Suresh Kumar</span>
                        <span className="text-gold-400 ml-2 font-mono text-[10px] uppercase">Landlord</span>
                      </div>
                      <span className="text-emerald-400 font-mono text-[10px]">HIGH CONFIDENCE</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-800 flex justify-between items-center">
                      <div>
                        <span className="font-semibold text-slate-200">Priya Sharma</span>
                        <span className="text-gold-400 ml-2 font-mono text-[10px] uppercase">Tenant</span>
                      </div>
                      <span className="text-emerald-400 font-mono text-[10px]">HIGH CONFIDENCE</span>
                    </div>
                  </div>
                </div>

                <div className="bg-navy-950/60 rounded-xl p-5 border border-navy-800">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="section-tag">07</span>
                      <h4 className="text-sm font-semibold text-slate-200">Evidence &amp; ML Forensics</h4>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Trained XGBoost
                    </span>
                  </div>
                  <div className="p-3 rounded-lg bg-navy-900/80 border border-navy-800 text-xs">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-semibold text-slate-200">rental_agreement.jpg</span>
                      <span className="text-emerald-400 font-mono font-bold">Quality: 64.3/100</span>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2 text-[10px]">
                      <span className="px-1.5 py-0.5 rounded bg-navy-800 text-slate-300">OCR: 100%</span>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">✓ Parties Matched</span>
                      <span className="px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">✓ Financials Extracted</span>
                      <span className="px-1.5 py-0.5 rounded bg-blue-950/60 text-blue-400 border border-blue-800/40">Type: Contract</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---- HOW IT WORKS (Requested Flow) ---- */}
      <section id="how-it-works" className="relative z-10 py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-white/[0.06]">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs uppercase font-mono tracking-widest text-gold-400 font-semibold mb-2 block">
            The 4-Step Pipeline
          </span>
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">
            How CaseCompiler Organizes Your Case
          </h2>
          <p className="text-slate-400 text-base">
            From raw, emotional narrative to a clean, court-ready 11-section case file in under 60 seconds.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            {
              step: '01',
              title: 'Tell Your Story & Drop Docs',
              desc: 'Provide your free-form description. Upload rental agreements, WhatsApp export screenshots, or bank receipts.',
              icon: UploadCloud,
              badge: 'Multimodal Input'
            },
            {
              step: '02',
              title: 'Extraction & ML Forensics',
              desc: 'Gemini function calling identifies claims, timelines, and amounts. Our trained XGBoost model evaluates 21 document quality signals.',
              icon: Brain,
              badge: '21-Signal Scorer'
            },
            {
              step: '03',
              title: 'Targeted Legal Interview',
              desc: 'The AI spots missing details, ambiguity, or timeline gaps and asks 2–3 specific questions to solidify the record.',
              icon: HelpCircle,
              badge: 'Gap Clarifier'
            },
            {
              step: '04',
              title: 'Lawyer Dossier & PDF',
              desc: 'Generates an 11-section structured file grounded in Indian tenancy statutes, ready for human legal practitioner review.',
              icon: FileCheck,
              badge: 'Executive PDF'
            }
          ].map((item, idx) => (
            <div key={idx} className="dossier-section p-6 flex flex-col justify-between group hover:border-gold-500/40">
              <div>
                <div className="flex items-center justify-between mb-5">
                  <span className="text-2xl font-mono font-extrabold text-gold-400/80 group-hover:text-gold-400 transition-colors">
                    {item.step}
                  </span>
                  <div className="w-10 h-10 rounded-xl bg-navy-800 border border-navy-700 flex items-center justify-center text-gold-400 group-hover:scale-110 transition-transform">
                    <item.icon size={20} />
                  </div>
                </div>
                <h3 className="font-semibold text-slate-100 text-lg mb-2">{item.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">{item.desc}</p>
              </div>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-navy-900 border border-navy-800 text-slate-400 w-fit">
                {item.badge}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ---- QUICK START SAMPLE CASE TEASER ---- */}
      <section id="sample-case" className="relative z-10 py-16 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto">
        <div className="bg-gradient-to-br from-navy-900 via-navy-850 to-navy-900 border border-gold-500/30 rounded-2xl p-8 sm:p-10 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-80 h-80 bg-gold-500/5 rounded-full blur-3xl pointer-events-none" />
          <div className="flex flex-col md:flex-row gap-8 items-start md:items-center justify-between relative z-10">
            <div className="max-w-xl">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-gold-400/10 border border-gold-400/20 text-[11px] font-mono text-gold-400 mb-3">
                <Sparkles size={12} />
                <span>Instant Evaluation Template</span>
              </div>
              <h3 className="text-2xl font-bold font-display text-white mb-2">
                Want to test the pipeline right now?
              </h3>
              <p className="text-sm text-slate-300 leading-relaxed">
                Launch with a pre-configured Bangalore Tenancy Dispute (unlawful ₹45,000 security deposit withholding, WhatsApp notice, and wear-and-tear clause).
              </p>
            </div>
            <button
              onClick={handleLaunchSample}
              className="btn-gold whitespace-nowrap px-6 py-3.5 rounded-xl text-sm font-bold flex items-center gap-2 cursor-pointer shadow-lg shadow-gold-500/20 shrink-0"
            >
              <span>Load Tenancy Sample</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </section>

      {/* ---- LEGAL ENGINE & COMPLIANCE SECTION ---- */}
      <section id="features" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs uppercase font-mono tracking-widest text-gold-400 font-semibold mb-2 block">
            Built for Real Legal Practice
          </span>
          <h2 className="font-display text-3xl sm:text-4xl font-bold text-white mb-4">
            Engineered with Rigorous Safeguards
          </h2>
          <p className="text-slate-400 text-sm">
            Not a generic chatbot. CaseCompiler enforces structured schema validation, deterministic triage, and statutory retrieval.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="dossier-section p-6">
            <div className="w-10 h-10 rounded-lg bg-navy-800 border border-navy-700 flex items-center justify-center text-gold-400 mb-4">
              <Shield size={20} />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">Non-Advisory Guardrails</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Strictly non-advisory. CaseCompiler assists in organizing facts, highlighting contradictions, and preparing questions for human advocates under the Advocates Act, 1961.
            </p>
          </div>

          <div className="dossier-section p-6">
            <div className="w-10 h-10 rounded-lg bg-navy-800 border border-navy-700 flex items-center justify-center text-gold-400 mb-4">
              <BookOpen size={20} />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">Curated Statutory RAG</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Vector search across verified statutes including the Karnataka Rent Act, 1999 and the Model Tenancy Act, 2021 with explicit hedging and practitioner review notes.
            </p>
          </div>

          <div className="dossier-section p-6">
            <div className="w-10 h-10 rounded-lg bg-navy-800 border border-navy-700 flex items-center justify-center text-gold-400 mb-4">
              <Brain size={20} />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">21-Feature Evidence Scorer</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Trained XGBoost regression model calculates continuous document quality scores (0–100) based on OCR fidelity, temporal alignment, and multi-document consistency.
            </p>
          </div>
        </div>
      </section>

      {/* ---- FINAL CTA BANNER ---- */}
      <section className="relative z-10 py-16 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto text-center">
        <div className="glass-card p-10 sm:p-14 border border-gold-500/25 relative overflow-hidden">
          <h2 className="font-display text-3xl sm:text-4xl font-extrabold text-white mb-4">
            Ready to prepare your case file?
          </h2>
          <p className="text-slate-300 text-sm max-w-xl mx-auto mb-8 leading-relaxed">
            Begin the guided briefing process now. Your facts remain secure, organized, and ready for your advocate's review.
          </p>
          <button
            onClick={onStartCase}
            className="btn-gold px-8 py-3.5 rounded-xl text-base font-bold inline-flex items-center gap-2 cursor-pointer shadow-xl shadow-gold-500/30"
          >
            <span>Build My Case Now</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* ---- FOOTER ---- */}
      <footer id="compliance" className="relative z-10 border-t border-white/[0.06] bg-navy-950/90 py-10 px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex items-center justify-center gap-2 text-slate-400 font-semibold">
            <Scale size={16} className="text-gold-400" />
            <span>CaseCompiler Legal Information System</span>
          </div>
          <p className="text-[11px] text-slate-500 max-w-2xl mx-auto leading-relaxed">
            ⚠️ Disclaimer: CaseCompiler is an AI case organization platform designed to assist qualified advocates and legal practitioners in matter review. It does not provide legal advice, represent parties in court, or create an attorney-client relationship. All extracted entities and statutory references require independent professional verification.
          </p>
          <p className="text-[11px] text-slate-600">
            © 2026 CaseCompiler. Built with Gemini Multimodal Intelligence &amp; XGBoost Forensics.
          </p>
        </div>
      </footer>
    </div>
  )
}
