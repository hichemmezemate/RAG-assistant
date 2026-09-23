import React, { useState } from 'react';
import { SourceCitation as SourceCitationType } from '../types';
import { BookOpen, ChevronDown, ChevronUp, FileText } from 'lucide-react';

interface Props {
  sources: SourceCitationType[];
}

export const SourceCitation: React.FC<Props> = ({ sources }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!sources || sources.length === 0) {
    return null;
  }

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  return (
    <div className="source-citations-container">
      <div className="source-citations-header">
        <BookOpen size={14} className="source-icon" />
        <span>Sources citées ({sources.length}) :</span>
      </div>

      <div className="source-citations-list">
        {sources.map((source, index) => {
          const isExpanded = expandedIndex === index;
          return (
            <div key={`${source.documentId}-${index}`} className="source-card">
              <button
                type="button"
                className="source-card-header"
                onClick={() => toggleExpand(index)}
                aria-expanded={isExpanded}
              >
                <div className="source-info">
                  <FileText size={13} className="doc-icon" />
                  <span className="source-doc-name">{source.documentName}</span>
                  {source.pageOrSection && (
                    <span className="source-tag">{source.pageOrSection}</span>
                  )}
                </div>
                {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {isExpanded && (
                <div className="source-card-body">
                  <p className="source-extrait">« {source.extrait} »</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
