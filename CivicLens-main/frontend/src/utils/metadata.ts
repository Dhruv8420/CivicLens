import type { DetectorSignal, ProjectMetadata } from '../types/risk';

/**
 * Safely extracts sector and status metadata from the list of detector signals
 * by searching by detector name rather than assuming fixed array order.
 */
export function extractMetadata(signals: DetectorSignal[] = []): ProjectMetadata {
  let sector = '—';
  let status = '—';

  for (const signal of signals) {
    if (signal.detector === 'cost_anomaly' && signal.sector) {
      sector = signal.sector;
    }
    if (signal.detector === 'delay' && signal.status) {
      status = signal.status;
    }
  }

  if (sector === '—') {
    const signalWithSector = signals.find((s) => Boolean(s.sector));
    if (signalWithSector?.sector) {
      sector = signalWithSector.sector;
    }
  }

  if (status === '—') {
    const signalWithStatus = signals.find((s) => Boolean(s.status));
    if (signalWithStatus?.status) {
      status = signalWithStatus.status;
    }
  }

  return { sector, status };
}
