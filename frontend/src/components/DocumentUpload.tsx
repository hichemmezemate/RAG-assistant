import React, { useRef, useState } from 'react';
import { Document } from '../types';
import {
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

interface Props {
  documents: Document[];
  uploading: boolean;
  onUpload: (file: File) => void;
  onDelete: (id: string) => void;
}

export const DocumentUpload: React.FC<Props> = ({
  documents,
  uploading,
  onUpload,
  onDelete,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const renderStatusBadge = (status: Document['status']) => {
    switch (status) {
      case 'Indexed':
        return (
          <span className="status-badge status-indexed" title="Document indexé et interrogeable">
            <CheckCircle2 size={12} /> Indexé
          </span>
        );
      case 'Processing':
        return (
          <span className="status-badge status-processing" title="Indexation en cours">
            <Clock size={12} /> Traitement
          </span>
        );
      case 'Error':
        return (
          <span className="status-badge status-error" title="Erreur lors de l'indexation">
            <AlertTriangle size={12} /> Erreur
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="document-upload-panel">
      <div className="panel-header">
        <h3>Corpus documentaire</h3>
        <span className="doc-count">{documents.length} doc{documents.length > 1 ? 's' : ''}</span>
      </div>

      {/* Zone de drop */}
      <div
        className={`dropzone ${isDragOver ? 'dropzone-active' : ''} ${
          uploading ? 'dropzone-disabled' : ''
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          disabled={uploading}
        />

        {uploading ? (
          <div className="dropzone-content">
            <Loader2 size={24} className="spinner" />
            <p className="dropzone-text">Indexation en cours...</p>
          </div>
        ) : (
          <div className="dropzone-content">
            <UploadCloud size={24} className="upload-icon" />
            <p className="dropzone-title">Glisser un document ici ou cliquer</p>
            <p className="dropzone-sub">PDF, DOCX, TXT (max 10 Mo)</p>
          </div>
        )}
      </div>

      {/* Liste des documents */}
      <div className="doc-list-wrapper">
        <h4 className="doc-list-title">Documents du corpus</h4>
        {documents.length === 0 ? (
          <p className="empty-docs-text">Aucun document importé. Ajoutez un fichier pour débuter.</p>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.id} className="doc-item">
                <div className="doc-item-main">
                  <FileText size={16} className="doc-file-icon" />
                  <div className="doc-details">
                    <span className="doc-name" title={doc.filename}>
                      {doc.filename}
                    </span>
                    <span className="doc-meta">
                      {(() => {
                        const raw = doc.uploadedAt || doc.uploaded_at || new Date().toISOString();
                        const d = new Date(raw);
                        return !isNaN(d.getTime())
                          ? d.toLocaleDateString([], { day: '2-digit', month: 'short' })
                          : '';
                      })()}
                    </span>
                  </div>
                </div>

                <div className="doc-item-actions">
                  {renderStatusBadge(doc.status)}
                  <button
                    type="button"
                    className="btn-delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(doc.id);
                    }}
                    title="Supprimer le document du corpus"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
