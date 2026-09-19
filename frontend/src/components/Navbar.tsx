import React from 'react';

interface NavbarProps {
  isConnected: boolean | null;
  totalProjects?: number;
}

export const Navbar: React.FC<NavbarProps> = ({ isConnected, totalProjects }) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M12 8v4" />
              <path d="M12 16h.01" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">CivicLens</h1>
            <p className="brand-subtitle">Public Project Risk Intelligence</p>
          </div>
        </div>

        <div className="navbar-meta">
          {totalProjects !== undefined && (
            <span className="dataset-chip">
              <strong>{totalProjects}</strong> Projects Analyzed
            </span>
          )}

          <div className="backend-status">
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
              {isConnected === true
                ? 'Backend Connected'
                : isConnected === false
                ? 'Backend Unavailable'
                : 'Checking Connection...'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
