import React, { useMemo, useState } from 'react';
import type { RiskEngineResult, RiskLevel } from '../types/risk';
import { extractMetadata } from '../utils/metadata';
import { RiskBadge } from './RiskBadge';

interface ProjectTableProps {
  projects: RiskEngineResult[];
  onSelectProject: (projectId: string) => void;
  selectedProjectId?: string | null;
  activeFilter: string;
  onFilterChange: (filter: string) => void;
}

export const ProjectTable: React.FC<ProjectTableProps> = ({
  projects,
  onSelectProject,
  selectedProjectId,
  activeFilter,
  onFilterChange,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'risk_score' | 'project_id' | 'flagged'>('risk_score');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const filteredAndSortedProjects = useMemo(() => {
    return projects
      .filter((p) => {
        if (activeFilter !== 'ALL' && p.risk_level !== activeFilter) {
          return false;
        }

        if (searchTerm.trim()) {
          const term = searchTerm.toLowerCase().trim();
          const { sector } = extractMetadata(p.signals);
          const matchId = p.project_id.toLowerCase().includes(term);
          const matchSector = sector.toLowerCase().includes(term);
          const matchLevel = p.risk_level.toLowerCase().includes(term);
          return matchId || matchSector || matchLevel;
        }

        return true;
      })
      .sort((a, b) => {
        let valA: any;
        let valB: any;

        if (sortField === 'risk_score') {
          valA = a.risk_score;
          valB = b.risk_score;
        } else if (sortField === 'flagged') {
          valA = a.flagged_detectors_count;
          valB = b.flagged_detectors_count;
        } else {
          valA = a.project_id;
          valB = b.project_id;
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
  }, [projects, activeFilter, searchTerm, sortField, sortDirection]);

  const handleSort = (field: 'risk_score' | 'project_id' | 'flagged') => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'project_id' ? 'asc' : 'desc');
    }
  };

  const filterLevels: Array<{ label: string; value: string }> = [
    { label: 'All Projects', value: 'ALL' },
    { label: 'Critical Risk', value: 'CRITICAL' },
    { label: 'High Risk', value: 'HIGH' },
    { label: 'Medium Risk', value: 'MEDIUM' },
    { label: 'Low Risk', value: 'LOW' },
  ];

  return (
    <div className="table-container-card">
      <div className="table-toolbar">
        <div className="filter-pills">
          {filterLevels.map((lvl) => (
            <button
              key={lvl.value}
              className={`filter-pill ${activeFilter === lvl.value ? 'active' : ''}`}
              onClick={() => onFilterChange(lvl.value)}
            >
              {lvl.label}
            </button>
          ))}
        </div>

        <div className="search-box">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search by ID, sector..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          {searchTerm && (
            <button className="clear-search-btn" onClick={() => setSearchTerm('')}>
              ×
            </button>
          )}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="projects-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('project_id')} className="sortable-col">
                Project ID {sortField === 'project_id' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th>Sector</th>
              <th>Status</th>
              <th onClick={() => handleSort('flagged')} className="sortable-col">
                Flagged Signals {sortField === 'flagged' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th onClick={() => handleSort('risk_score')} className="sortable-col">
                Risk Score {sortField === 'risk_score' ? (sortDirection === 'asc' ? '↑' : '↓') : ''}
              </th>
              <th>Risk Level</th>
              <th className="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedProjects.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-table-cell">
                  No projects match the current filter or search criteria.
                </td>
              </tr>
            ) : (
              filteredAndSortedProjects.map((project) => {
                const { sector, status } = extractMetadata(project.signals);
                const isSelected = selectedProjectId === project.project_id;

                return (
                  <tr
                    key={project.project_id}
                    className={`project-row ${isSelected ? 'row-selected' : ''}`}
                    onClick={() => onSelectProject(project.project_id)}
                  >
                    <td className="font-mono text-bold">{project.project_id}</td>
                    <td>
                      <span className="sector-tag">{sector}</span>
                    </td>
                    <td>
                      <span className={`status-chip status-${status.toLowerCase().replace(/\s+/g, '-')}`}>
                        {status}
                      </span>
                    </td>
                    <td>
                      {project.flagged_detectors_count > 0 ? (
                        <span className="flagged-count-badge">
                          ⚠️ {project.flagged_detectors_count} of {project.total_detectors_evaluated}
                        </span>
                      ) : (
                        <span className="clean-count-badge">✓ 0 flagged</span>
                      )}
                    </td>
                    <td>
                      <div className="score-cell">
                        <span className="score-num">{project.risk_score.toFixed(1)}</span>
                        <div className="mini-score-bar">
                          <div
                            className={`mini-score-fill score-fill-${project.risk_level.toLowerCase()}`}
                            style={{ width: `${project.risk_score}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <RiskBadge level={project.risk_level as RiskLevel} />
                    </td>
                    <td className="text-right">
                      <button
                        className="inspect-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectProject(project.project_id);
                        }}
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        Showing {filteredAndSortedProjects.length} of {projects.length} analyzed projects
      </div>
    </div>
  );
};
