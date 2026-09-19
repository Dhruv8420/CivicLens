import React from 'react';

interface NavbarProps {
  isConnected: boolean | null;
  totalProjects?: number;
  onOpenUpload?: () => void;
  isUploadOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  isConnected,
  totalProjects,
  onOpenUpload,
  isUploadOpen,
}) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
            </svg>
          </div>
          <div>
            <div className="brand-title-row">
              <h1 className="brand-title">CivicLens</h1>
              <span className="brand-badge">ENTERPRISE</span>
            </div>
            <p className="brand-subtitle">Public Infrastructure Risk Intelligence</p>
          </div>
        </div>

        <nav className="navbar-nav">
          <a href="#overview" className="nav-link active">Overview</a>
          <a href="#projects" className="nav-link">Projects Audit</a>
          <a href="#detectors" className="nav-link">Risk Engine</a>
        </nav>

        <div className="navbar-meta">
          {onOpenUpload && (
            <button
              className="navbar-upload-btn"
              onClick={onOpenUpload}
              title="Upload custom dataset CSV for risk analysis"
            >
              <span className="upload-btn-icon">{isUploadOpen ? '✖' : '📤'}</span>
              <span>{isUploadOpen ? 'Close Upload' : 'Upload Dataset'}</span>
            </button>
          )}

          {totalProjects !== undefined && (
            <span className="dataset-chip">
              <span className="chip-dot" />
              <strong>{totalProjects.toLocaleString()}</strong> Projects Monitored
            </span>
          )}

          <div className="backend-status" title={isConnected ? 'Backend API Connected' : 'Connecting to API...'}>
            <span
              className={`status-indicator ${
                isConnected === true
                  ? 'status-online'
                  : isConnected === false
                  ? 'status-offline'
                  : 'status-checking'
              }`}
            />
            <span className="status-text">
              {isConnected === true ? 'System Active' : isConnected === false ? 'Offline' : 'Checking'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
