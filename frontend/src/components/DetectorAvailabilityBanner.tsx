import React from 'react';
import type { DetectorAvailabilityInfo } from '../types/risk';

interface DetectorAvailabilityBannerProps {
  filename: string;
  totalProjects: number;
  detectorAvailability: Record<string, DetectorAvailabilityInfo>;
  warnings?: string[];
  onReset: () => void;
}

const DETECTOR_LABELS: Record<string, string> = {
  cost_anomaly: 'Cost Anomaly',
  progress_mismatch: 'Progress Mismatch',
  cost_overrun: 'Cost Overrun',
  delay: 'Delay',
};

export const DetectorAvailabilityBanner: React.FC<DetectorAvailabilityBannerProps> = ({
  filename,
  totalProjects,
  detectorAvailability,
  warnings,
  onReset,
}) => {
  return (
    <div className="availability-banner-card">
      <div className="banner-header">
        <div className="banner-title-group">
          <span className="file-icon">📄</span>
          <div>
            <h3 className="banner-filename">{filename}</h3>
            <p className="banner-meta">
              Custom Dataset • {totalProjects} projects evaluated
            </p>
          </div>
        </div>
        <button className="reset-btn" onClick={onReset} title="Reset to default synthetic dataset">
          ← Reset to Synthetic Benchmark
        </button>
      </div>

      <div className="detector-pills-row">
        {Object.entries(detectorAvailability).map(([detKey, info]) => {
          const label = DETECTOR_LABELS[detKey] || detKey;
          return (
            <div
              key={detKey}
              className={`detector-avail-pill ${info.available ? 'pill-available' : 'pill-skipped'}`}
              title={info.reason}
            >
              <span className="pill-status-icon">{info.available ? '✓' : '⚠️'}</span>
              <span className="pill-label">{label}</span>
              <span className="pill-badge">{info.available ? 'Active' : 'Skipped'}</span>
            </div>
          );
        })}
      </div>

      {warnings && warnings.length > 0 && (
        <div className="banner-warnings">
          <span className="warning-icon">💡</span>
          <div className="warning-list">
            {warnings.map((w, i) => (
              <span key={i} className="warning-item">
                {w}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
