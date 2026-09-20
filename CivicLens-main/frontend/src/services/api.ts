import type { HealthResponse, ProjectsResponse, RiskEngineResult, UploadResponse } from '../types/risk';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) return false;
    const data: HealthResponse = await response.json();
    return data.status === 'ok';
  } catch {
    return false;
  }
}

export async function fetchAllProjects(params?: {
  reference_date?: string;
  progress_threshold?: number;
  cost_overrun_threshold?: number;
}): Promise<ProjectsResponse> {
  const query = new URLSearchParams();
  if (params?.reference_date) query.append('reference_date', params.reference_date);
  if (params?.progress_threshold !== undefined) {
    query.append('progress_threshold', params.progress_threshold.toString());
  }
  if (params?.cost_overrun_threshold !== undefined) {
    query.append('cost_overrun_threshold', params.cost_overrun_threshold.toString());
  }

  const url = `${API_BASE_URL}/api/projects${query.toString() ? `?${query.toString()}` : ''}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch projects (HTTP ${response.status})`);
  }

  return response.json();
}

export async function fetchProjectById(
  projectId: string,
  params?: {
    reference_date?: string;
    progress_threshold?: number;
    cost_overrun_threshold?: number;
  }
): Promise<RiskEngineResult> {
  const query = new URLSearchParams();
  if (params?.reference_date) query.append('reference_date', params.reference_date);
  if (params?.progress_threshold !== undefined) {
    query.append('progress_threshold', params.progress_threshold.toString());
  }
  if (params?.cost_overrun_threshold !== undefined) {
    query.append('cost_overrun_threshold', params.cost_overrun_threshold.toString());
  }

  const url = `${API_BASE_URL}/api/projects/${encodeURIComponent(projectId)}${
    query.toString() ? `?${query.toString()}` : ''
  }`;
  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Project '${projectId}' not found.`);
    }
    throw new Error(`Failed to fetch project ${projectId} (HTTP ${response.status})`);
  }

  return response.json();
}

export async function uploadCSVDataset(
  file: File,
  params?: {
    reference_date?: string;
    progress_threshold?: number;
    cost_overrun_threshold?: number;
  }
): Promise<UploadResponse> {
  const query = new URLSearchParams();
  if (params?.reference_date) query.append('reference_date', params.reference_date);
  if (params?.progress_threshold !== undefined) {
    query.append('progress_threshold', params.progress_threshold.toString());
  }
  if (params?.cost_overrun_threshold !== undefined) {
    query.append('cost_overrun_threshold', params.cost_overrun_threshold.toString());
  }

  const formData = new FormData();
  formData.append('file', file);

  const url = `${API_BASE_URL}/api/analyze/upload${query.toString() ? `?${query.toString()}` : ''}`;
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const msg = errorBody?.detail || `Failed to process uploaded CSV (HTTP ${response.status})`;
    throw new Error(msg);
  }

  return response.json();
}
