import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Trash2, Plus } from 'lucide-react';
import type { ChatMessage } from '../lib/api';

interface Props {
  title: string;
  subtitle?: string;
  placeholder?: string;
  onSend: (message: string, history: ChatMessage[]) => Promise<string>;
  welcomeMessage?: string;
  accentColor?: string;
  quickPrompts?: string[];
}

export default function ChatInterface({ title, subtitle, placeholder, onSend, welcomeMessage, quickPrompts }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(
    welcomeMessage ? [{ role: 'assistant', content: welcomeMessage }] : []
  );
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;
    setInput('');
    const userMsg: ChatMessage = { role: 'user', content: msg };
    const history = [...messages, userMsg];
    setMessages(history);
    setLoading(true);
    try {
      const response = await onSend(msg, messages);
      setMessages(prev => [...prev, { role: 'assistant', content: response }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `I'm sorry, something went wrong. Please try again.` }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages(welcomeMessage ? [{ role: 'assistant', content: welcomeMessage }] : []);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-serif text-ink">{title}</h2>
          {subtitle && <p className="text-sm text-eco-text/60 mt-1">{subtitle}</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={clearChat} className="p-2 rounded-xl text-eco-text/50 hover:bg-sand/50 hover:text-ink transition-colors" title="New conversation">
            <Plus size={18} />
          </button>
          <button onClick={clearChat} className="p-2 rounded-xl text-eco-text/50 hover:bg-soft-rose/50 hover:text-danger transition-colors" title="Clear chat">
            <Trash2 size={18} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-eco-card rounded-2xl border border-eco-border p-4 space-y-4">
        {messages.length === 0 && quickPrompts && (
          <div className="flex flex-wrap gap-2 justify-center py-8">
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSend(prompt)}
                className="px-4 py-2 bg-sand/50 hover:bg-sand text-sm text-ink rounded-xl transition-colors border border-eco-border"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-leaf/15 text-ink'
                : 'bg-sand/40 text-eco-text'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start animate-fade-in">
            <div className="bg-sand/40 rounded-2xl px-4 py-3">
              <Loader2 className="animate-spin text-leaf" size={18} />
            </div>
          </div>
        )}

        <div ref={messagesEnd} />
      </div>

      <div className="mt-3 flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Type your message...'}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-eco-border bg-eco-card px-4 py-3 text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf focus:ring-0 transition-colors"
          style={{ minHeight: '44px', maxHeight: '120px' }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = Math.min(target.scrollHeight, 120) + 'px';
          }}
        />
        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          className="px-4 py-3 bg-leaf hover:bg-leaf-dark disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
