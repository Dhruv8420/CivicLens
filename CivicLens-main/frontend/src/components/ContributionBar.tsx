import React from 'react';
import type { DetectorContribution } from '../types/risk';

interface ContributionBarProps {
  contribution: DetectorContribution;
}

const DETECTOR_LABELS: Record<string, string> = {
  cost_anomaly: 'Cost Anomaly (IQR Sector Baseline)',
  progress_mismatch: 'Progress Mismatch (Financial vs Physical)',
  delay: 'Project Delay (Passed Completion Deadline)',
  cost_overrun: 'Cost Overrun (Revised vs Original Cost)',
};

export const ContributionBar: React.FC<ContributionBarProps> = ({ contribution }) => {
  const { detector, is_flagged, severity, max_points, contribution: pts, reason } = contribution;
  const percentage = max_points > 0 ? Math.min(100, Math.max(0, (pts / max_points) * 100)) : 0;
  const label = DETECTOR_LABELS[detector] || detector;

  return (
    <div className={`contribution-card ${is_flagged ? 'contribution-flagged' : 'contribution-clean'}`}>
      <div className="contribution-header">
        <div className="contribution-title-row">
          <span className="contribution-label">{label}</span>
          {is_flagged ? (
            <span className="badge-flagged">Flagged</span>
          ) : (
            <span className="badge-clean">Aligned</span>
          )}
        </div>
        <div className="contribution-points">
          <span className="points-value">+{pts.toFixed(2)}</span>
          <span className="points-max">/ {max_points.toFixed(0)} pts</span>
        </div>
      </div>

      <div className="progress-bar-track">
        <div
          className={`progress-bar-fill ${is_flagged ? 'fill-flagged' : 'fill-clean'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      <div className="contribution-meta">
        <span>Severity: <strong>{severity.toFixed(2)}</strong></span>
        <span>Max Weight: <strong>{max_points} pts</strong></span>
      </div>

      {is_flagged && reason && (
        <p className="contribution-reason">
          <span className="reason-icon">💬</span> {reason}
        </p>
      )}
    </div>
  );
};
