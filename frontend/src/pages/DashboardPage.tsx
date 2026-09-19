import React, { useCallback, useEffect, useState } from 'react';
import { DetectorAvailabilityBanner } from '../components/DetectorAvailabilityBanner';
import { Navbar } from '../components/Navbar';
import { ProjectDetailDrawer } from '../components/ProjectDetailDrawer';
import { ProjectTable } from '../components/ProjectTable';
import { SummaryCards } from '../components/SummaryCards';
import { UploadSection } from '../components/UploadSection';
import { checkBackendHealth, fetchAllProjects, uploadCSVDataset } from '../services/api';
import type { RiskEngineResult, UploadResponse } from '../types/risk';

export const DashboardPage: React.FC = () => {
  const [projects, setProjects] = useState<RiskEngineResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('ALL');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [showUploadForm, setShowUploadForm] = useState<boolean>(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setUploadResult(null);

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

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    try {
      const result = await uploadCSVDataset(file);
      setUploadResult(result);
      setProjects(result.projects || []);
      setActiveFilter('ALL');
      setSelectedProjectId(null);
      setShowUploadForm(false);
    } catch (err: any) {
      throw err;
    } finally {
      setIsUploading(false);
    }
  };

  const selectedProject = projects.find((p) => p.project_id === selectedProjectId) || null;

  return (
    <div className="dashboard-layout">
      <Navbar
        isConnected={isConnected}
        totalProjects={projects.length}
        onOpenUpload={() => setShowUploadForm(!showUploadForm)}
        isUploadOpen={showUploadForm}
      />

      <main className="dashboard-content">
        <div className="hero-banner">
          <div className="hero-content">
            <div className="hero-pill">
              <span className="hero-pill-icon">🛡️</span>
              <span>Explainable Risk Intelligence Engine • MoSPI PAIMANA Audit Integration</span>
            </div>
            <h2 className="hero-title">Public Infrastructure Risk Audit</h2>
            <p className="hero-subtitle">
              Automated anomaly detection for major development projects. Evaluates sector-wise IQR cost baselines, physical vs expenditure progress gaps, completion delays, and budget overruns.
            </p>
          </div>
        </div>

        {showUploadForm && (
          <UploadSection onUpload={handleUpload} isUploading={isUploading} />
        )}

        {uploadResult && (
          <DetectorAvailabilityBanner
            filename={uploadResult.filename}
            totalProjects={uploadResult.total_projects}
            detectorAvailability={uploadResult.detector_availability}
            warnings={uploadResult.warnings}
            onReset={loadData}
          />
        )}

        {isLoading && (
          <div className="state-card loading-state">
            <div className="spinner" />
            <p className="state-title">Analyzing Infrastructure Dataset...</p>
            <p className="state-subtitle">
              Computing IQR sector baselines, expenditure progress gaps, schedule deadlines, and cost overrun signals.
            </p>
          </div>
        )}

        {!isLoading && error && (
          <div className="state-card error-state">
            <div className="error-icon">⚠️</div>
            <h3 className="state-title">Backend API Offline</h3>
            <p className="state-subtitle">{error}</p>
            <button className="primary-btn retry-btn" onClick={loadData}>
              🔄 Retry System Connection
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
