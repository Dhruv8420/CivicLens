/**
 * CivicLens Frontend - TypeScript Type Definitions
 */

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface DetectorContribution {
  detector: string;
  is_flagged: boolean;
  severity: number;
  max_points: number;
  contribution: number;
  status: 'computed' | 'missing_data';
  direction: string;
  reason: string;
}

export interface DetectorSignal {
  project_id: string;
  detector: string;
  is_flagged: boolean;
  severity: number;
  reason: string;
  // Optional evidence & metadata fields from detectors
  sector?: string;
  direction?: string;
  days_delayed?: number;
  mismatch_pct?: number;
  cost_overrun_pct?: number;
  financial_progress_pct?: number;
  physical_progress_pct?: number;
  original_cost_lakhs?: number;
  revised_cost_lakhs?: number;
  expenditure_lakhs?: number;
  lower_bound?: number;
  upper_bound?: number;
  status?: string;
  revised_completion_date?: string;
  reference_date?: string;
  threshold?: number;
}

export interface RiskEngineResult {
  project_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  recommendation: string;
  flagged_detectors_count: number;
  total_detectors_evaluated: number;
  detector_contributions: Record<string, DetectorContribution>;
  flagged_reasons: string[];
  signals: DetectorSignal[];
}

export interface ProjectsResponse {
  total: number;
  projects: RiskEngineResult[];
}

export interface HealthResponse {
  status: string;
}

export interface ProjectMetadata {
  sector: string;
  status: string;
}
