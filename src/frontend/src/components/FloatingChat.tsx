import { useState, useRef, useEffect } from 'react';
import { MessageSquare, X, Send, Mic, Menu, Plus, Paperclip } from 'lucide-react';
import { useAIContext } from '../context/AIContext';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  attachmentUrl?: string;
}

interface ChatSession {
  id: string;
  title: string;
  updated_at: string;
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export default function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "Hi! I'm Aegis, your health copilot. How can I help you today?" }
  ]);
  const [input, setInput] = useState('');
  const [attachment, setAttachment] = useState<File | null>(null);
  const [attachmentPreview, setAttachmentPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  
  const { state: aiState } = useAIContext();

  useEffect(() => {
    if (attachment) {
      const url = URL.createObjectURL(attachment);
      setAttachmentPreview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setAttachmentPreview(null);
    }
  }, [attachment]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isOpen]);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      
      recognition.onresult = (event: any) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript;
        }
        setInput(transcript);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const loadSessions = async () => {
    try {
      const res = await fetch('/api/chat/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (e) {
      console.error("Failed to load sessions");
    }
  };

  const handleToggleSidebar = () => {
    if (!showSidebar) {
      loadSessions();
    }
    setShowSidebar(!showSidebar);
  };

  const startNewChat = () => {
    setSessionId(null);
    setMessages([{ role: 'assistant', content: "Hi! I'm Aegis, your health copilot. How can I help you today?" }]);
    setShowSidebar(false);
  };

  const selectSession = async (id: string) => {
    setSessionId(id);
    setShowSidebar(false);
    try {
      const res = await fetch(`/api/chat/sessions/${id}/history`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error("Failed to load history");
    }
  };

  const handleSend = async () => {
    if (!input.trim() && !attachment) return;
    
    const userMessage = input.trim() || 'Attached an image';
    setInput('');
    const currentAttachment = attachment;
    const displayUrl = currentAttachment ? URL.createObjectURL(currentAttachment) : undefined;
    setAttachment(null);
    setMessages(prev => [...prev, { role: 'user', content: userMessage, attachmentUrl: displayUrl }]);
    setIsLoading(true);
    
    try {
      const formData = new FormData();
      formData.append('message', userMessage);
      if (sessionId) {
        formData.append('session_id', sessionId);
      }
      if (currentAttachment) {
        formData.append('file', currentAttachment);
      }
      formData.append('screen_context', JSON.stringify(aiState));
      
      const res = await fetch('/api/chat', {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) throw new Error('Failed to fetch');
      
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      if (!sessionId) {
        setSessionId(data.session_id);
      }
    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I couldn't reach the server right now." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleListen = () => {
    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
    } else {
      setInput('');
      recognitionRef.current?.start();
      setIsListening(true);
    }
  };

  return (
    <div className="chat-widget-container">
      <div className={`glass-panel chat-panel ${!isOpen ? 'closed' : ''}`} style={{ position: 'relative', overflow: 'hidden' }}>
        
        {/* Sidebar Overlay */}
        <div style={{
          position: 'absolute',
          top: 0, bottom: 0, left: 0, width: '250px',
          background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border-color)',
          transform: showSidebar ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.3s ease',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600 }}>Chat History</span>
            <button className="icon-btn" onClick={startNewChat} title="New Chat">
              <Plus size={18} />
            </button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
            {sessions.map(s => (
              <div 
                key={s.id} 
                onClick={() => selectSession(s.id)}
                style={{ 
                  padding: '0.75rem', 
                  borderRadius: '0.5rem', 
                  cursor: 'pointer',
                  background: sessionId === s.id ? 'var(--bg-tertiary)' : 'transparent',
                  marginBottom: '0.25rem',
                  fontSize: '0.9rem',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
              >
                {s.title}
              </div>
            ))}
            {sessions.length === 0 && (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                No history found
              </div>
            )}
          </div>
        </div>

        <div className="flex-between chat-header">
          <div className="flex-center" style={{ gap: '0.5rem' }}>
            <button className="icon-btn" onClick={handleToggleSidebar}>
              <Menu size={20} />
            </button>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-success)' }}></div>
            <span style={{ fontWeight: 600 }}>Aegis Copilot</span>
          </div>
          <button className="icon-btn" onClick={() => setIsOpen(false)}>
            <X size={20} />
          </button>
        </div>
        
        <div className="chat-messages" onClick={() => showSidebar && setShowSidebar(false)}>
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.attachmentUrl && (
                <div style={{ marginBottom: '8px' }}>
                  <img src={msg.attachmentUrl} alt="attachment" style={{ maxWidth: '100%', borderRadius: '8px', maxHeight: '200px', objectFit: 'contain', border: '1px solid var(--border-color)' }} />
                </div>
              )}
              {msg.content}
            </div>
          ))}
          {isLoading && (
            <div className="message assistant" style={{ opacity: 0.7 }}>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center', height: '24px' }}>
                <div style={{ width: 6, height: 6, background: 'var(--text-secondary)', borderRadius: '50%', animation: 'pulse-glow 1s infinite' }}></div>
                <div style={{ width: 6, height: 6, background: 'var(--text-secondary)', borderRadius: '50%', animation: 'pulse-glow 1s infinite 0.2s' }}></div>
                <div style={{ width: 6, height: 6, background: 'var(--text-secondary)', borderRadius: '50%', animation: 'pulse-glow 1s infinite 0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="chat-input-area" onClick={() => showSidebar && setShowSidebar(false)}>
          {attachmentPreview && (
            <div style={{ position: 'absolute', top: '-60px', left: '10px', background: 'var(--bg-secondary)', padding: '6px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
              <img src={attachmentPreview} alt="preview" style={{ height: '40px', width: '40px', objectFit: 'cover', borderRadius: '4px' }} />
              <div style={{ display: 'flex', flexDirection: 'column', maxWidth: '120px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>{attachment?.name}</span>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Image attached</span>
              </div>
              <button className="icon-btn" style={{ padding: '4px', height: 'auto', width: 'auto' }} onClick={() => setAttachment(null)}>
                <X size={14} />
              </button>
            </div>
          )}
          <label className="icon-btn" style={{ cursor: 'pointer', color: 'var(--text-secondary)' }}>
            <Paperclip size={20} />
            <input 
              type="file" 
              accept="image/*" 
              style={{ display: 'none' }} 
              onChange={(e) => e.target.files && setAttachment(e.target.files[0])} 
              disabled={showSidebar}
            />
          </label>
          <button 
            className="icon-btn" 
            onClick={toggleListen}
            style={{ color: isListening ? 'var(--accent-danger)' : 'var(--text-secondary)' }}
            disabled={showSidebar}
          >
            {isListening ? (
              <div className="recording-indicator" />
            ) : (
              <Mic size={20} />
            )}
          </button>
          <input 
            type="text" 
            className="chat-input" 
            placeholder="Log data or ask a question..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={showSidebar}
          />
          <button className="icon-btn" onClick={handleSend} style={{ color: 'var(--accent-primary)' }} disabled={showSidebar}>
            <Send size={20} />
          </button>
        </div>
      </div>
      
      {!isOpen && (
        <button className="fab-btn" onClick={() => setIsOpen(true)}>
          <MessageSquare size={28} />
        </button>
      )}
    </div>
  );
}
