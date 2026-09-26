import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import ProgressStepper from './ProgressStepper'

describe('ProgressStepper Component', () => {
  it('renders with the correct step active based on currentStep prop', () => {
    const { container } = render(
      <ProgressStepper currentStep="extract" activePhase="extraction" />
    )

    // "AI Extraction" is currentStep -> active style
    const activeLabel = screen.getByText('AI Extraction')
    expect(activeLabel).toBeDefined()
    expect(activeLabel.className).toContain('text-gold-400')

    // "Describe Case" precedes currentStep -> done style
    const doneLabel = screen.getByText('Describe Case')
    expect(doneLabel).toBeDefined()
    expect(doneLabel.className).toContain('text-emerald-400')

    // Active circle should have .step-active class
    const activeStepCircle = container.querySelector('.step-active')
    expect(activeStepCircle).not.toBeNull()

    // Sub-phase checklist should be rendered when on 'extract'
    const subPhaseHeading = screen.getByText('Live Extraction Phases')
    expect(subPhaseHeading).toBeDefined()
  })
})
