import { useState, useRef, useEffect } from 'react';
import { chat as chatApi } from '../../services/api';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';
import SourceCard from './SourceCard';
import { Bot, Plus, History } from 'lucide-react';

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSources, setShowSources] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    chatApi.listConversations().then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleNewChat = () => {
    setMessages([]);
    setConversationId(null);
    setShowSources(null);
  };

  const handleLoadConversation = async (convId) => {
    try {
      const history = await chatApi.getHistory(convId);
      setMessages(history.map(m => ({
        role: m.role,
        content: m.content,
        sources: m.sources ? JSON.parse(m.sources) : [],
        confidence: m.confidence,
        latency_ms: m.latency_ms,
      })));
      setConversationId(convId);
      setShowHistory(false);
    } catch (err) {
      console.error('Failed to load conversation:', err);
    }
  };

  const handleSend = async (query) => {
    const userMsg = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setShowSources(null);

    try {
      const res = await chatApi.query(query, conversationId);
      setConversationId(res.conversation_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
        confidence: res.confidence,
        latency_ms: res.latency_ms,
      }]);
      // Refresh conversations list
      chatApi.listConversations().then(setConversations).catch(() => {});
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
        isError: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-layout">
      {/* Conversation History Sidebar */}
      <div className={`chat-history-panel ${showHistory ? 'open' : ''}`}>
        <div className="chat-history-header">
          <h3>Conversations</h3>
          <button className="btn btn-sm" onClick={handleNewChat}>
            <Plus size={16} /> New
          </button>
        </div>
        <div className="chat-history-list">
          {conversations.map(c => (
            <button
              key={c.id}
              className={`history-item ${c.id === conversationId ? 'active' : ''}`}
              onClick={() => handleLoadConversation(c.id)}
            >
              <span className="history-title">{c.title}</span>
              <span className="history-count">{c.message_count} msgs</span>
            </button>
          ))}
          {conversations.length === 0 && (
            <p className="empty-text">No conversations yet</p>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        <div className="chat-header">
          <button className="btn btn-icon" onClick={() => setShowHistory(!showHistory)}>
            <History size={20} />
          </button>
          <h2>
            <Bot size={22} />
            Knowledge Assistant
          </h2>
          <button className="btn btn-sm btn-ghost" onClick={handleNewChat}>
            <Plus size={16} /> New Chat
          </button>
        </div>

        <div className="messages-container">
          {messages.length === 0 && (
            <div className="chat-empty">
              <Bot size={48} />
              <h3>Welcome to KnowledgeAI</h3>
              <p>Ask anything about your organization's knowledge base.</p>
              <div className="suggested-queries">
                {['What is the remote work policy?', 'How do I submit expense reports?', 'What are the coding standards?'].map(q => (
                  <button key={q} className="suggestion-chip" onClick={() => handleSend(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              message={msg}
              onShowSources={msg.sources?.length ? () => setShowSources(msg.sources) : null}
            />
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-bubble">
                <div className="typing-indicator">
                  <span></span><span></span><span></span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <InputBar onSend={handleSend} disabled={loading} />
      </div>

      {/* Sources Panel */}
      {showSources && (
        <div className="sources-panel">
          <div className="sources-header">
            <h3>Sources</h3>
            <button className="btn btn-icon" onClick={() => setShowSources(null)}>✕</button>
          </div>
          <div className="sources-list">
            {showSources.map((src, i) => (
              <SourceCard key={i} source={src} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
