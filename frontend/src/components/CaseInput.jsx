import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { FileText, Image, Upload, X, AlertCircle, Loader2, Scale } from 'lucide-react'

const MAX_FILES = 8
const MAX_MB = 20

function FileChip({ file, onRemove }) {
  const isImage = file.type.startsWith('image/')
  const Icon = isImage ? Image : FileText
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-navy-800 border border-navy-700 text-sm text-slate-300 group">
      <Icon size={13} className="text-gold-400 shrink-0" aria-hidden="true" />
      <span className="max-w-[140px] truncate">{file.name}</span>
      <button
        type="button"
        onClick={() => onRemove(file)}
        aria-label={`Remove file ${file.name}`}
        className="ml-1 text-slate-500 hover:text-red-400 transition-colors focus:outline-none focus:ring-1 focus:ring-red-400 rounded"
      >
        <X size={13} aria-hidden="true" />
      </button>
    </div>
  )
}

const SAMPLE_DISPUTE = `I rented a 2BHK flat (Flat 302, HSR Layout Sector 2, Bangalore) from my landlord Suresh Kumar starting 1st April 2023. At the time of signing the agreement, I paid a refundable security deposit of Rs. 1,00,000 via bank transfer. My monthly rent was Rs. 22,000, which I paid regularly without default.

On 12th February 2024, Suresh Kumar sent me a WhatsApp notice asking me to vacate the flat by 15th February 2024. I vacated on 15th February and handed over keys in good condition. However, Suresh Kumar is refusing to refund my full deposit and is withholding Rs. 45,000 claiming bogus painting and deep-cleaning charges, which was never agreed to in our rental agreement (clause says normal wear and tear is landlord responsibility). He has only offered to return Rs. 55,000. I need my remaining Rs. 45,000 refunded immediately.`

export const loadSampleImages = async () => {
  const list = [
    { url: '/samples/rental_agreement.jpg', name: 'rental_agreement.jpg' },
    { url: '/samples/bank_transfer_receipt.jpg', name: 'bank_transfer_receipt.jpg' },
    { url: '/samples/whatsapp_notice.jpg', name: 'whatsapp_notice.jpg' },
  ]
  const loaded = await Promise.all(
    list.map(async ({ url, name }) => {
      const res = await fetch(url)
      const blob = await res.blob()
      return new File([blob], name, { type: 'image/jpeg' })
    })
  )
  return loaded
}

export default function CaseInput({ onSubmit, loading, initialDescription = '', initialFiles = [] }) {
  const [description, setDescription] = useState(initialDescription)
  const [files, setFiles] = useState(initialFiles)
  const [loadingSample, setLoadingSample] = useState(false)
  const [error, setError] = useState('')

  React.useEffect(() => {
    if (initialDescription) setDescription(initialDescription)
  }, [initialDescription])

  React.useEffect(() => {
    if (initialFiles && initialFiles.length > 0) setFiles(initialFiles)
  }, [initialFiles])

  const onDrop = useCallback(
    (accepted, rejected) => {
      if (rejected.length > 0) {
        setError('Some files were rejected. Check format or size (max 20 MB each).')
      }
      const combined = [...files, ...accepted].slice(0, MAX_FILES)
      setFiles(combined)
      if (combined.length === MAX_FILES) {
        setError(`Maximum ${MAX_FILES} files allowed.`)
      } else {
        setError('')
      }
    },
    [files]
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.webp'],
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: MAX_MB * 1024 * 1024,
    maxFiles: MAX_FILES,
  })

  const removeFile = (file) => {
    setFiles((prev) => prev.filter((f) => f !== file))
    setError('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!description.trim()) {
      setError('Please describe your situation before submitting.')
      return
    }
    setError('')
    onSubmit(description, files)
  }

  const handleInsertSample = async () => {
    setDescription(SAMPLE_DISPUTE)
    setError('')
    setLoadingSample(true)
    try {
      const sampleFiles = await loadSampleImages()
      setFiles(sampleFiles)
    } catch (err) {
      console.warn('Failed to load sample images:', err)
    } finally {
      setLoadingSample(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-slide-up">
      {/* Disclaimer */}
      <div className="disclaimer-banner rounded-lg p-4">
        <div className="flex gap-3 items-start">
          <Scale size={16} className="text-gold-400 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-400 leading-relaxed">
            <span className="font-semibold text-gold-400">For lawyer review only.</span>{' '}
            CaseCompiler organises your information to help a legal practitioner understand
            your matter. It does <span className="font-semibold">not</span> provide legal advice.
          </p>
        </div>
      </div>

      {/* Description textarea */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-slate-300">
            Describe your situation
            <span className="ml-2 text-xs text-slate-500 font-normal hidden sm:inline">
              Include dates, names, amounts, and what occurred.
            </span>
          </label>
          <button
            type="button"
            onClick={handleInsertSample}
            disabled={loadingSample}
            aria-label="Insert sample dispute with 3 supporting documents"
            className="text-xs text-gold-400 hover:text-gold-300 transition-colors underline font-medium cursor-pointer flex items-center gap-1.5 focus:outline-none focus:ring-1 focus:ring-gold-400 rounded"
          >
            {loadingSample && <Loader2 size={12} className="animate-spin" role="status" aria-label="Loading sample" />}
            <span>Insert Sample + 3 Supporting Docs</span>
          </button>
        </div>
        <textarea
          id="case-description"
          aria-label="Legal case description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && description.trim() && !loading) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          placeholder="Example: My landlord, Ramesh Kumar, has refused to return my security deposit of ₹50,000 after I vacated the flat at 12B Indiranagar, Bengaluru on 15 August 2024. The tenancy started in March 2022 and I gave proper 2-month notice in writing. He is claiming deductions for damage that was already present when I moved in..."
          rows={8}
          className="input-legal resize-none leading-relaxed focus:outline-none focus:ring-2 focus:ring-gold-400/80"
          disabled={loading}
        />
        <div className="flex justify-between items-center mt-1">
          <span className="text-[11px] text-slate-500">
            Provide specific details · Press <kbd className="px-1 py-0.5 rounded bg-navy-800 border border-navy-700 font-mono text-[10px] text-slate-400">Ctrl + Enter</kbd> to analyze
          </span>
          <div className="flex items-center gap-2.5">
            {description.length > 0 && !loading && (
              <button
                type="button"
                onClick={() => setDescription('')}
                aria-label="Clear case description text"
                className="text-[11px] text-slate-500 hover:text-red-400 transition-colors underline cursor-pointer"
              >
                Clear
              </button>
            )}
            <span className="text-xs text-slate-600 font-mono">{description.length} chars</span>
          </div>
        </div>
      </div>

      {/* File dropzone */}
      <div>
        <label htmlFor="file-upload-zone" className="block text-sm font-medium text-slate-300 mb-2">
          Evidence &amp; Documents
          <span className="ml-2 text-xs text-slate-500 font-normal">
            Optional — images, PDFs, text files (max {MAX_FILES} files, {MAX_MB} MB each)
          </span>
        </label>
        <div
          {...getRootProps()}
          id="file-upload-zone"
          role="button"
          tabIndex={0}
          aria-label="Upload evidence files and documents zone. Press Enter or Space to browse files, or drag and drop files here."
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              const inputEl = document.querySelector('#file-upload-zone input')
              if (inputEl) inputEl.click()
            }
          }}
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer
            focus:outline-none focus:ring-2 focus:ring-gold-400 focus:border-gold-400
            ${isDragActive
              ? 'border-gold-400/60 bg-gold-400/5 scale-[1.01]'
              : 'border-navy-700 bg-navy-900/30 hover:border-navy-600 hover:bg-navy-900/50'
            }`}
        >
          <input {...getInputProps()} aria-label="Upload evidence files input" />
          <Upload
            size={28}
            aria-hidden="true"
            className={`mx-auto mb-3 ${isDragActive ? 'text-gold-400' : 'text-slate-600'}`}
          />
          {isDragActive ? (
            <p className="text-sm text-gold-400 font-medium">Drop files here…</p>
          ) : (
            <>
              <p className="text-sm text-slate-400">
                Drag &amp; drop files, or{' '}
                <span className="text-gold-400 font-medium">click to browse</span>
              </p>
              <p className="text-xs text-slate-600 mt-1">
                JPG · PNG · PDF · TXT · MD
              </p>
            </>
          )}
        </div>

        {/* File chips */}
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {files.map((f, i) => (
              <FileChip key={i} file={f} onRemove={removeFile} />
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div role="alert" className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <AlertCircle size={15} className="shrink-0" aria-hidden="true" />
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !description.trim()}
        id="submit-case-btn"
        aria-label={loading ? 'Analysing case facts and evidence' : 'Analyse case facts and evidence'}
        className="w-full py-3.5 px-6 rounded-xl font-semibold text-navy-950 text-sm
                   bg-gradient-to-r from-gold-400 to-gold-500
                   hover:from-gold-500 hover:to-gold-600
                   focus:outline-none focus:ring-2 focus:ring-gold-400
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-all duration-200 shadow-lg shadow-gold-500/10
                   flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" role="status" aria-label="Processing analysis" />
            Analysing case…
          </>
        ) : (
          <>
            <Scale size={16} aria-hidden="true" />
            Analyse Case
          </>
        )}
      </button>
    </form>
  )
}
