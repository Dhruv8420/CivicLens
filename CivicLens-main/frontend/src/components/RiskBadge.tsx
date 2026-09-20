import React from 'react';
import type { RiskLevel } from '../types/risk';

interface RiskBadgeProps {
  level: RiskLevel;
  score?: number;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, score }) => {
  const levelClass = level.toLowerCase();

  return (
    <span className={`risk-badge risk-badge-${levelClass}`}>
      <span className="risk-dot" />
      {level}
      {score !== undefined && <span className="risk-score-value">({score.toFixed(1)})</span>}
    </span>
  );
};
