import React, { useCallback, useEffect, useState } from 'react';
import { Navbar } from '../components/Navbar';
import { ProjectDetailDrawer } from '../components/ProjectDetailDrawer';
import { ProjectTable } from '../components/ProjectTable';
import { SummaryCards } from '../components/SummaryCards';
import { checkBackendHealth, fetchAllProjects } from '../services/api';
import type { RiskEngineResult } from '../types/risk';

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<RiskEngineResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const healthy = await checkBackendHealth();
    setIsConnected(healthy);

    if (!healthy) {
      setError(
        'Backend API server is unreachable. Please ensure the FastAPI backend is running on http://127.0.0.1:8000.'
      );
      setIsLoading(false);
      return;
    }

    try {
      const data = await fetchAllProjects();
      setProjects(data.projects || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load project risk data.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const selectedProject = projects.find((p) => p.project_id === selectedProjectId) || null;

  return (
    <div className="dashboard-layout">
      <Navbar isConnected={isConnected} totalProjects={projects.length} />

      <main className="dashboard-content">
        {isLoading && (
          <div className="state-card loading-state">
            <div className="spinner" />
            <p className="state-title">Analyzing Public Development Projects...</p>
            <p className="state-subtitle">
              Calculating IQR bounds, progress gaps, schedule delays, and cost overruns.
            </p>
          </div>
        )}

        {!isLoading && error && (
          <div className="state-card error-state">
            <div className="error-icon">⚠️</div>
            <h3 className="state-title">Backend Connection Failure</h3>
            <p className="state-subtitle">{error}</p>
            <button className="primary-btn retry-btn" onClick={loadData}>
              🔄 Retry Connection
            </button>
          </div>
        )}

        {!isLoading && !error && (
          <>
            <SummaryCards
              projects={projects}
              activeFilter={activeFilter}
              onSelectFilter={(lvl) => setActiveFilter(lvl)}
            />

            <ProjectTable
              projects={projects}
              activeFilter={activeFilter}
              onFilterChange={(lvl) => setActiveFilter(lvl)}
              selectedProjectId={selectedProjectId}
              onSelectProject={(id) => setSelectedProjectId(id)}
            />
          </>
        )}
      </main>

      <ProjectDetailDrawer project={selectedProject} onClose={() => setSelectedProjectId(null)} />
    </div>
  );
};
