import { FileText } from 'lucide-react';

export default function SourceCard({ source }) {
  return (
    <div className="source-card">
      <div className="source-header">
        <FileText size={14} />
        <span className="source-title">{source.document_title || 'Document'}</span>
        {source.relevance_score > 0 && (
          <span className="source-score">
            {Math.round(source.relevance_score * 100)}%
          </span>
        )}
      </div>
      {source.section_heading && (
        <div className="source-section">§ {source.section_heading}</div>
      )}
      <p className="source-text">{source.chunk_text || source.text}</p>
      {source.page_number && (
        <span className="source-page">Page {source.page_number}</span>
      )}
    </div>
  );
}
