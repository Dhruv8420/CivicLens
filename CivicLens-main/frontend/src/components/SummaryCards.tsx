import React from 'react';
import type { RiskEngineResult } from '../types/risk';

interface SummaryCardsProps {
  projects: RiskEngineResult[];
  onSelectFilter?: (level: string) => void;
  activeFilter?: string;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  projects,
  onSelectFilter,
  activeFilter = 'ALL',
}) => {
  const total = projects.length;
  const criticalCount = projects.filter((p) => p.risk_level === 'CRITICAL').length;
  const highCount = projects.filter((p) => p.risk_level === 'HIGH').length;
  const flaggedCount = projects.filter((p) => p.flagged_detectors_count > 0).length;

  return (
    <div className="summary-cards-grid">
      <div
        className={`summary-card ${activeFilter === 'ALL' ? 'active' : ''}`}
        onClick={() => onSelectFilter?.('ALL')}
      >
        <div className="card-header">
          <span className="card-title">Total Projects</span>
          <div className="card-icon card-icon-slate">📊</div>
        </div>
        <div className="card-value">{total}</div>
        <p className="card-description">Full dataset analyzed</p>
      </div>

      <div
        className={`summary-card summary-card-critical ${activeFilter === 'CRITICAL' ? 'active' : ''}`}
        onClick={() => onSelectFilter?.('CRITICAL')}
      >
        <div className="card-header">
          <span className="card-title">Critical Risk</span>
          <div className="card-icon card-icon-red">⚠️</div>
        </div>
        <div className="card-value">{criticalCount}</div>
        <p className="card-description">Priority review recommended</p>
      </div>

      <div
        className={`summary-card summary-card-high ${activeFilter === 'HIGH' ? 'active' : ''}`}
        onClick={() => onSelectFilter?.('HIGH')}
      >
        <div className="card-header">
          <span className="card-title">High Risk</span>
          <div className="card-icon card-icon-orange">⚡</div>
        </div>
        <div className="card-value">{highCount}</div>
        <p className="card-description">Verification recommended</p>
      </div>

      <div
        className={`summary-card ${activeFilter === 'FLAGGED' ? 'active' : ''}`}
        onClick={() => onSelectFilter?.('FLAGGED')}
      >
        <div className="card-header">
          <span className="card-title">Flagged Indicators</span>
          <div className="card-icon card-icon-blue">🔎</div>
        </div>
        <div className="card-value">{flaggedCount}</div>
        <p className="card-description">Projects with 1+ flagged signal</p>
      </div>
    </div>
  );
};
