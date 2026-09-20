import React from 'react';
import type { RiskEngineResult } from '../types/risk';
import { extractMetadata } from '../utils/metadata';
import { ContributionBar } from './ContributionBar';
import { RiskBadge } from './RiskBadge';

interface ProjectDetailDrawerProps {
  project: RiskEngineResult | null;
  onClose: () => void;
}

export const ProjectDetailDrawer: React.FC<ProjectDetailDrawerProps> = ({ project, onClose }) => {
  if (!project) return null;

  const { sector, status } = extractMetadata(project.signals);
  const contributions = Object.values(project.detector_contributions);

  const pmSignal = project.signals.find((s) => s.detector === 'progress_mismatch');
  const delaySignal = project.signals.find((s) => s.detector === 'delay');
  const coSignal = project.signals.find((s) => s.detector === 'cost_overrun');
  const caSignal = project.signals.find((s) => s.detector === 'cost_anomaly');

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <div className="drawer-subtitle-row">
              <span className="sector-tag">{sector}</span>
              <span className={`status-chip status-${status.toLowerCase().replace(/\s+/g, '-')}`}>
                {status}
              </span>
            </div>
            <h2 className="drawer-title">{project.project_id}</h2>
          </div>
          <button className="close-drawer-btn" onClick={onClose} aria-label="Close drawer">
            ×
          </button>
        </div>

        <div className="drawer-body">
          <div className={`hero-risk-card hero-risk-${project.risk_level.toLowerCase()}`}>
            <div className="hero-risk-score-col">
              <span className="hero-score-label">Project Risk Score</span>
              <div className="hero-score-number">{project.risk_score.toFixed(1)}</div>
              <span className="hero-score-scale">out of 100 max</span>
            </div>

            <div className="hero-risk-meta-col">
              <div className="hero-level-row">
                <span className="hero-level-label">Classification:</span>
                <RiskBadge level={project.risk_level} />
              </div>
              <p className="hero-indicator-count">
                <strong>{project.flagged_detectors_count}</strong> of {project.total_detectors_evaluated} risk indicators flagged
              </p>
            </div>
          </div>

          <div className="recommendation-box">
            <div className="recommendation-header">
              <span className="rec-icon">📋</span>
              <span className="rec-title">Recommended Action</span>
            </div>
            <p className="recommendation-text">{project.recommendation}</p>
          </div>

          <div className="detail-section">
            <h3 className="section-title">
              <span className="title-icon">🔎</span> Why Flagged?
            </h3>
            {project.flagged_reasons.length === 0 ? (
              <div className="clean-signal-banner">
                <span>✓</span> No anomaly indicators were flagged for this project based on configured rules.
              </div>
            ) : (
              <ul className="flagged-reasons-list">
                {project.flagged_reasons.map((reason, idx) => (
                  <li key={idx} className="reason-item">
                    <span className="reason-bullet">⚡</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="detail-section">
            <h3 className="section-title">
              <span className="title-icon">📊</span> Signal Contribution Breakdown
            </h3>
            <p className="section-subtitle">
              Calculated dynamically from the 4 indicator detectors. Contributions sum to the project risk score.
            </p>
            <div className="contributions-list">
              {contributions.map((contrib) => (
                <ContributionBar key={contrib.detector} contribution={contrib} />
              ))}
            </div>
          </div>

          <div className="detail-section">
            <h3 className="section-title">
              <span className="title-icon">📈</span> Detector Evidence Data
            </h3>
            <div className="evidence-grid">
              {caSignal && (
                <div className="evidence-card">
                  <div className="evidence-card-title">Original Cost (Sector IQR)</div>
                  <div className="evidence-value">
                    Rs. {caSignal.original_cost_lakhs?.toLocaleString() ?? '—'} Lakhs
                  </div>
                  {caSignal.upper_bound !== undefined && (
                    <div className="evidence-meta">
                      Sector Upper Fence: Rs. {caSignal.upper_bound.toLocaleString()} Lakhs
                    </div>
                  )}
                </div>
              )}

              {pmSignal && (
                <div className="evidence-card">
                  <div className="evidence-card-title">Physical vs Financial Gap</div>
                  <div className="evidence-value">
                    {pmSignal.mismatch_pct !== undefined ? `${pmSignal.mismatch_pct}% mismatch` : '—'}
                  </div>
                  <div className="evidence-meta">
                    Financial: {pmSignal.financial_progress_pct?.toFixed(1) ?? '—'}% | Physical: {pmSignal.physical_progress_pct?.toFixed(1) ?? '—'}%
                  </div>
                </div>
              )}

              {delaySignal && (
                <div className="evidence-card">
                  <div className="evidence-card-title">Schedule Delay</div>
                  <div className="evidence-value">
                    {delaySignal.days_delayed !== undefined ? `${delaySignal.days_delayed} days delayed` : '—'}
                  </div>
                  <div className="evidence-meta">
                    Completion Deadline: {delaySignal.revised_completion_date || '—'}
                  </div>
                </div>
              )}

              {coSignal && (
                <div className="evidence-card">
                  <div className="evidence-card-title">Cost Overrun</div>
                  <div className="evidence-value">
                    {coSignal.cost_overrun_pct !== undefined ? `+${coSignal.cost_overrun_pct}% overrun` : '—'}
                  </div>
                  <div className="evidence-meta">
                    Revised: Rs. {coSignal.revised_cost_lakhs?.toLocaleString() ?? '—'} Lakhs
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="drawer-footer">
          <button className="secondary-btn" onClick={onClose}>
            Close Inspection
          </button>
        </div>
      </div>
    </div>
  );
};
