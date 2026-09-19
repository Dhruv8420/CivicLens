import React, { useRef, useState } from 'react';

interface UploadSectionProps {
  onUpload: (file: File) => Promise<void>;
  isUploading: boolean;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ onUpload, isUploading }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleFileChange = (file: File | null) => {
    setUploadError(null);
    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Please select a valid CSV file (.csv format).');
      setSelectedFile(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size exceeds the 10 MB limit.');
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setUploadError(null);
    try {
      await onUpload(selectedFile);
    } catch (err: any) {
      setUploadError(err.message || 'Failed to analyze uploaded CSV dataset.');
    }
  };

  return (
    <div className="upload-section-card">
      <div className="upload-header">
        <span className="upload-icon">📤</span>
        <div>
          <h3 className="upload-title">Analyze External Project Dataset</h3>
          <p className="upload-subtitle">
            Upload custom CSVs or public open data (e.g. data.gov.in). CivicLens dynamically maps headers & evaluates available detector signals.
          </p>
        </div>
      </div>

      <div
        className={`dropzone ${dragActive ? 'dropzone-active' : ''} ${selectedFile ? 'has-file' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="file-input-hidden"
          onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
        />

        {!selectedFile ? (
          <div className="dropzone-prompt">
            <span className="folder-icon">📂</span>
            <p className="dropzone-text">
              <strong>Click to select a CSV</strong> or drag and drop file here
            </p>

          </div>
        ) : (
          <div className="selected-file-card">
            <span className="csv-badge">CSV</span>
            <div className="file-info-text">
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">{formatFileSize(selectedFile.size)}</span>
            </div>
            <button
              type="button"
              className="change-file-btn"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setUploadError(null);
              }}
            >
              Remove
            </button>
          </div>
        )}
      </div>

      {uploadError && (
        <div className="upload-error-banner">
          ⚠️ {uploadError}
        </div>
      )}

      {selectedFile && (
        <div className="upload-actions">
          <button
            className="primary-btn analyze-btn"
            onClick={handleSubmit}
            disabled={isUploading}
          >
            {isUploading ? (
              <>
                <span className="spinner-small" /> Analyzing Dataset...
              </>
            ) : (
              '⚡ Analyze Dataset with CivicLens'
            )}
          </button>
        </div>
      )}
    </div>
  );
};
