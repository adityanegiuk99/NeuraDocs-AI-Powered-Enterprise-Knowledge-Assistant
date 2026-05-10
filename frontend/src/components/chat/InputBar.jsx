import { useState } from 'react';
import { Send } from 'lucide-react';

export default function InputBar({ onSend, disabled }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const query = input.trim();
    if (!query || disabled) return;
    onSend(query);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about your knowledge base..."
        rows={1}
        disabled={disabled}
        id="chat-input"
      />
      <button type="submit" className="send-btn" disabled={disabled || !input.trim()}>
        <Send size={18} />
      </button>
    </form>
  );
}
