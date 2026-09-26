import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught component error:', error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="glass-card p-8 rounded-2xl border border-red-500/30 text-center my-6 shadow-2xl animate-fade-in"
        >
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <AlertCircle size={28} className="text-red-400" aria-hidden="true" />
          </div>
          <h3 className="text-lg font-bold text-slate-100 mb-2 font-display">Something went wrong, try again</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-5 leading-relaxed">
            {this.props.fallbackMessage ||
              this.state.error?.message ||
              'A component rendering error occurred. You can retry this section or start over.'}
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={this.handleReset}
              aria-label="Retry this section"
              className="btn-gold flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold cursor-pointer focus:outline-none focus:ring-2 focus:ring-gold-400"
            >
              <RefreshCw size={14} aria-hidden="true" />
              <span>Retry Section</span>
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
