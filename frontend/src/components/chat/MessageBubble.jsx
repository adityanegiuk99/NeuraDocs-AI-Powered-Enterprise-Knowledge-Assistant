import { Bot, User, FileText } from 'lucide-react';

export default function MessageBubble({ message, onShowSources }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'} ${message.isError ? 'error' : ''}`}>
      <div className="message-avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>
      <div className="message-content">
        <div className="message-bubble">
          <p>{message.content}</p>
        </div>
        {!isUser && !message.isError && (
          <div className="message-meta">
            {message.confidence > 0 && (
              <span className="meta-badge confidence">
                {Math.round(message.confidence * 100)}% confidence
              </span>
            )}
            {message.latency_ms > 0 && (
              <span className="meta-badge latency">
                {Math.round(message.latency_ms)}ms
              </span>
            )}
            {onShowSources && (
              <button className="meta-badge sources" onClick={onShowSources}>
                <FileText size={12} /> View Sources
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
