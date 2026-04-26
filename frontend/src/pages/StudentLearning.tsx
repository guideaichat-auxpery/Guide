import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  AlertTriangle, X, Loader2, CheckCircle, Shield, Plus, Trash2, Pencil,
  Send, Paperclip, FileText, MessageSquare, ArrowUp, Upload, FileCheck2,
  Menu,
} from 'lucide-react';
import GeneratedContent from '../components/GeneratedContent';
import { tools, type ChatMessage } from '../lib/api';
import type { Conversation } from '../lib/types';
import { useAuth } from '../contexts/AuthContext';

const SUBJECTS = [
  { id: 'English',     label: 'English',     hex: '#7da87b', tint: 'rgba(125,168,123,0.18)' },
  { id: 'Maths',       label: 'Maths',       hex: '#5b9bd5', tint: 'rgba(91,155,213,0.18)' },
  { id: 'Science',     label: 'Science',     hex: '#c97e5a', tint: 'rgba(201,126,90,0.18)' },
  { id: 'History',     label: 'History',     hex: '#b76e79', tint: 'rgba(183,110,121,0.18)' },
  { id: 'Geography',   label: 'Geography',   hex: '#d8b76a', tint: 'rgba(216,183,106,0.20)' },
  { id: 'Civics',      label: 'Civics',      hex: '#5d6f8c', tint: 'rgba(93,111,140,0.18)' },
  { id: 'Economics',   label: 'Economics',   hex: '#8a6a4f', tint: 'rgba(138,106,79,0.18)' },
] as const;

const YEAR_LEVELS = ['Year 7', 'Year 8', 'Year 9'] as const;

// AC V9 keyword set per subject — used to bold curriculum terms in AI replies.
// Kept short and lowercase for quick word-boundary matching.
const KEYWORDS: Record<string, string[]> = {
  English: ['theme', 'narrative', 'character', 'persuasive', 'analytical', 'figurative', 'imagery', 'thesis', 'evidence'],
  Maths: ['algebra', 'equation', 'variable', 'fraction', 'ratio', 'percentage', 'probability', 'theorem', 'pythagoras', 'gradient'],
  Science: ['hypothesis', 'experiment', 'variable', 'observation', 'cell', 'photosynthesis', 'ecosystem', 'force', 'energy', 'atom', 'molecule'],
  History: ['source', 'evidence', 'continuity', 'change', 'significance', 'colonisation', 'federation', 'indigenous', 'revolution'],
  Geography: ['environment', 'sustainability', 'biome', 'landform', 'climate', 'liveability', 'interconnection', 'urbanisation'],
  Civics: ['democracy', 'parliament', 'citizenship', 'rights', 'responsibilities', 'constitution', 'justice', 'rule of law'],
  Economics: ['market', 'supply', 'demand', 'consumer', 'producer', 'scarcity', 'resources', 'opportunity cost'],
};

function highlightKeywords(text: string, subjects: string[]): string {
  if (!text || subjects.length === 0) return text;
  const terms = subjects.flatMap(s => KEYWORDS[s] || []);
  if (terms.length === 0) return text;
  // Sort longest-first so multi-word terms win.
  const sorted = [...new Set(terms)].sort((a, b) => b.length - a.length);
  // Wrap in **bold** if not already adjacent to asterisks.
  let out = text;
  for (const term of sorted) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(?<![*\\w])(${escaped})(?!\\w)`, 'gi');
    out = out.replace(re, '**$1**');
  }
  return out;
}

interface UIMessage extends ChatMessage {
  id: string;
}

export default function StudentLearning() {
  const { user } = useAuth();
  const rawDisplayName = user && 'full_name' in user ? (user.full_name || '') : '';
  const displayName = (rawDisplayName && rawDisplayName.trim()) || 'Explorer';

  // ----- conversation state -----
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);
  const [restoredToast, setRestoredToast] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ----- input state -----
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>([]);
  const [yearLevel, setYearLevel] = useState<string>('Year 8');

  // ----- file upload state -----
  const [workFile, setWorkFile] = useState<File | null>(null);
  const [rubricFile, setRubricFile] = useState<File | null>(null);
  const [uploadingFeedback, setUploadingFeedback] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  // ----- safety modal -----
  const [showSafety, setShowSafety] = useState(false);
  const [safetyText, setSafetyText] = useState('');
  const [safetySending, setSafetySending] = useState(false);
  const [safetySent, setSafetySent] = useState(false);

  const messagesRef = useRef<HTMLDivElement>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  // Tracks the most recent conversation the user asked to open so that
  // out-of-order responses from earlier fetches don't overwrite messages
  // for the conversation that's currently selected.
  const latestRequestedSessionRef = useRef<string | null>(null);

  const activeSubject = selectedSubjects[0] || null;
  const subjectMeta = SUBJECTS.find(s => s.id === activeSubject) || null;
  const accent = subjectMeta?.hex || '#7da87b';
  const accentTint = subjectMeta?.tint || 'rgba(125,168,123,0.18)';

  // -- load conversations + restore most recent on mount --
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await tools.listConversations('student');
        if (cancelled) return;
        const list = res.conversations || [];
        setConversations(list);
        if (list.length > 0) {
          const mostRecent = list[0];
          await openConversation(mostRecent, { silent: false });
        }
      } catch {
        // non-fatal: student can still start a new chat
      } finally {
        if (!cancelled) setConversationsLoading(false);
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -- auto-scroll to newest --
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, sending, uploadingFeedback]);

  // -- scroll-to-top button visibility --
  const onScroll = useCallback(() => {
    const el = messagesRef.current;
    if (!el) return;
    setShowScrollTop(el.scrollTop > 240);
  }, []);

  // -- toast auto-dismiss --
  useEffect(() => {
    if (!restoredToast) return;
    const t = setTimeout(() => setRestoredToast(null), 3500);
    return () => clearTimeout(t);
  }, [restoredToast]);

  async function openConversation(c: Conversation, opts: { silent?: boolean } = {}) {
    latestRequestedSessionRef.current = c.session_id;
    setActiveSessionId(c.session_id);
    setSidebarOpen(false);
    try {
      const res = await tools.getMessages(c.session_id, 'student');
      // Drop this response if the user has already moved on to another chat.
      if (latestRequestedSessionRef.current !== c.session_id) return;
      const loaded: UIMessage[] = (res.messages || []).map((m, i) => ({
        ...m,
        id: `${c.session_id}-${i}`,
      }));
      setMessages(loaded);
      // Re-apply persisted subject if available so theming survives reloads.
      const tag = (c as Conversation & { subject_tag?: string | null }).subject_tag;
      if (tag && SUBJECTS.some(s => s.id === tag)) {
        setSelectedSubjects([tag]);
      }
      if (!opts.silent) {
        setRestoredToast(`Restored "${c.title}"`);
      }
    } catch {
      if (latestRequestedSessionRef.current === c.session_id) {
        setMessages([]);
      }
    }
  }

  async function startNewConversation(title?: string): Promise<string | null> {
    try {
      const res = await tools.createConversation({
        interface_type: 'student',
        title: title || 'New chat',
      });
      const session_id = res.session_id;
      // Re-fetch list so the sidebar picks up the new entry.
      const list = await tools.listConversations('student');
      setConversations(list.conversations || []);
      setActiveSessionId(session_id);
      setMessages([]);
      return session_id;
    } catch {
      return null;
    }
  }

  async function handleNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setInput('');
    setWorkFile(null);
    setRubricFile(null);
    setShowUpload(false);
  }

  async function handleRename(c: Conversation) {
    const next = renameDraft.trim();
    setRenamingId(null);
    setRenameDraft('');
    if (!next || next === c.title) return;
    try {
      await tools.renameConversation(String(c.id), next);
      setConversations(prev => prev.map(x => x.id === c.id ? { ...x, title: next } : x));
    } catch {
      // ignore — keep old title
    }
  }

  async function handleDelete(c: Conversation) {
    if (!confirm(`Delete "${c.title}"? This can't be undone.`)) return;
    try {
      await tools.deleteConversation(String(c.id));
      setConversations(prev => prev.filter(x => x.id !== c.id));
      if (activeSessionId === c.session_id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch {
      // ignore
    }
  }

  async function ensureSession(): Promise<string | null> {
    if (activeSessionId) return activeSessionId;
    const titleSeed = input.trim().slice(0, 40) || (activeSubject ? `${activeSubject} chat` : 'New chat');
    return await startNewConversation(titleSeed);
  }

  async function handleSend(textOverride?: string) {
    const msg = (textOverride ?? input).trim();
    if (!msg || sending) return;
    setInput('');
    const session_id = await ensureSession();
    if (!session_id) {
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: "I couldn't start a new chat just now. Please try again in a moment.",
      }]);
      return;
    }
    const userMsg: UIMessage = { id: `u-${Date.now()}`, role: 'user', content: msg };
    setMessages(prev => [...prev, userMsg]);
    setSending(true);
    try {
      const res = await tools.studentChat({
        message: msg,
        session_id,
        subjects: selectedSubjects,
        year_level: yearLevel,
      });
      setMessages(prev => [...prev, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: res.response,
      }]);
      // Refresh sidebar so titles/timestamps update.
      tools.listConversations('student').then(r => setConversations(r.conversations || [])).catch(() => {});
    } catch {
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: "I'm sorry, something went wrong. Please try again.",
      }]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function handleFeedbackUpload() {
    if (!workFile || uploadingFeedback) return;
    const session_id = await ensureSession();
    if (!session_id) return;
    setUploadingFeedback(true);
    const stagedUserMsg: UIMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: `📎 Shared work: **${workFile.name}**${rubricFile ? `\n📋 Rubric: **${rubricFile.name}**` : ''}`,
    };
    setMessages(prev => [...prev, stagedUserMsg]);
    try {
      const res = await tools.studentWorkFeedback({
        work_file: workFile,
        rubric_file: rubricFile,
        session_id,
        year_level: yearLevel,
        subjects: selectedSubjects,
      });
      setMessages(prev => [...prev, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: res.response,
      }]);
      setWorkFile(null);
      setRubricFile(null);
      setShowUpload(false);
      tools.listConversations('student').then(r => setConversations(r.conversations || [])).catch(() => {});
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Something went wrong uploading that.';
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `I couldn't read that file just now. ${msg}`,
      }]);
    } finally {
      setUploadingFeedback(false);
    }
  }

  async function handleSafetyReport() {
    if (!safetyText.trim()) return;
    setSafetySending(true);
    try {
      await tools.chat({
        message: `[SAFETY REPORT] ${safetyText}`,
        interface_type: 'safety_report',
      });
      setSafetySent(true);
      setTimeout(() => {
        setShowSafety(false);
        setSafetyText('');
        setSafetySent(false);
      }, 2000);
    } catch {
      setSafetySent(true);
    } finally {
      setSafetySending(false);
    }
  }

  function toggleSubject(id: string) {
    setSelectedSubjects(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  }

  const showWelcome = messages.length === 0 && !sending;

  const themedMessages = useMemo(() =>
    messages.map(m => m.role === 'assistant'
      ? { ...m, content: highlightKeywords(m.content, selectedSubjects) }
      : m
    ),
    [messages, selectedSubjects]
  );

  return (
    <div className="animate-fade-in flex flex-col lg:flex-row gap-4 h-[calc(100vh-7rem)]">
      {/* ----- conversation sidebar ----- */}
      <aside
        className={`${sidebarOpen ? 'block' : 'hidden'} lg:block lg:w-64 shrink-0 bg-eco-card border border-eco-border rounded-2xl p-3 flex flex-col overflow-hidden`}
        aria-label="Your conversations"
      >
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-ink">Your chats</h3>
          <button
            onClick={handleNewChat}
            className="p-1.5 rounded-lg hover:bg-sand/60 text-ink"
            title="New chat"
            aria-label="New chat"
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto -mx-1 px-1">
          {conversationsLoading ? (
            <div className="text-xs text-eco-text/50 px-2 py-3">Loading…</div>
          ) : conversations.length === 0 ? (
            <div className="text-xs text-eco-text/50 px-2 py-3">No chats yet. Send a message to start one.</div>
          ) : (
            <ul className="space-y-1">
              {conversations.map(c => {
                const active = c.session_id === activeSessionId;
                const isRenaming = renamingId === String(c.id);
                return (
                  <li key={c.id}>
                    <div
                      className={`group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm cursor-pointer transition-colors ${
                        active ? 'bg-sand/70 text-ink' : 'text-eco-text hover:bg-sand/40'
                      }`}
                      onClick={() => !isRenaming && openConversation(c)}
                    >
                      <MessageSquare size={14} className="shrink-0 opacity-60" />
                      {isRenaming ? (
                        <input
                          autoFocus
                          value={renameDraft}
                          onChange={e => setRenameDraft(e.target.value)}
                          onKeyDown={e => {
                            if (e.key === 'Enter') handleRename(c);
                            if (e.key === 'Escape') { setRenamingId(null); setRenameDraft(''); }
                          }}
                          onBlur={() => handleRename(c)}
                          onClick={e => e.stopPropagation()}
                          className="flex-1 bg-white border border-eco-border rounded px-1.5 py-0.5 text-sm text-ink focus:border-leaf focus:outline-none"
                        />
                      ) : (
                        <span className="flex-1 truncate" title={c.title}>{c.title}</span>
                      )}
                      {!isRenaming && (
                        <>
                          <button
                            onClick={e => { e.stopPropagation(); setRenamingId(String(c.id)); setRenameDraft(c.title); }}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/60 text-eco-text/60 hover:text-ink"
                            title="Rename"
                            aria-label="Rename"
                          >
                            <Pencil size={12} />
                          </button>
                          <button
                            onClick={e => { e.stopPropagation(); handleDelete(c); }}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/60 text-eco-text/60 hover:text-danger"
                            title="Delete"
                            aria-label="Delete"
                          >
                            <Trash2 size={12} />
                          </button>
                        </>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>

      {/* ----- main chat area ----- */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* header (subject-themed) */}
        <div
          className="rounded-2xl border p-3 mb-2 flex items-center gap-2 transition-colors"
          style={{ background: accentTint, borderColor: `${accent}55` }}
        >
          <button
            onClick={() => setSidebarOpen(o => !o)}
            className="lg:hidden p-2 rounded-lg hover:bg-white/40 text-ink"
            aria-label="Toggle chats"
          >
            <Menu size={18} />
          </button>
          <div className="min-w-0">
            <h2 className="text-xl font-serif text-ink truncate">
              Hi {displayName}
            </h2>
            <p className="text-xs text-eco-text/70 truncate">
              {activeSubject ? `Working on ${activeSubject} · ${yearLevel}` : `Ready when you are · ${yearLevel}`}
            </p>
          </div>
          <button
            onClick={() => setShowSafety(true)}
            className="ml-auto p-2 rounded-xl text-warning hover:bg-warning/10 transition-colors"
            title="Report a concern"
            aria-label="Report a concern"
          >
            <AlertTriangle size={16} />
          </button>
        </div>

        {/* privacy banner */}
        <div className="mb-2 p-2.5 bg-sky/10 border border-sky/20 rounded-xl flex items-start gap-2">
          <Shield size={14} className="text-ink mt-0.5 shrink-0" />
          <p className="text-xs text-eco-text/60">
            Your conversations are private but monitored for safety. A trusted adult can see if something concerning comes up. You can always report a concern using the warning icon above.
          </p>
        </div>

        {/* subject + year picker */}
        <div className="mb-2 p-2.5 bg-eco-card border border-eco-border rounded-xl flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1.5">
            {SUBJECTS.map(s => {
              const on = selectedSubjects.includes(s.id);
              return (
                <button
                  key={s.id}
                  onClick={() => toggleSubject(s.id)}
                  className="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors"
                  style={on
                    ? { background: s.hex, color: 'white', borderColor: s.hex }
                    : { background: 'transparent', color: '#3f4a3a', borderColor: '#d8d3c4' }
                  }
                  aria-pressed={on}
                >
                  {s.label}
                </button>
              );
            })}
          </div>
          <div className="ml-auto flex items-center gap-2">
            <label className="text-xs text-eco-text/60">Year</label>
            <select
              value={yearLevel}
              onChange={e => setYearLevel(e.target.value)}
              className="text-xs px-2 py-1 rounded-lg border border-eco-border bg-white text-ink focus:border-leaf focus:outline-none"
            >
              {YEAR_LEVELS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
        </div>

        {/* messages */}
        <div
          ref={messagesRef}
          onScroll={onScroll}
          className="relative flex-1 overflow-y-auto bg-eco-card rounded-2xl border border-eco-border p-4 space-y-4"
        >
          {showWelcome && (
            <div className="text-center py-10 text-eco-text/60">
              <p className="text-base text-ink font-serif mb-2">
                What would you like to explore today?
              </p>
              <p className="text-xs">
                Pick one or more subjects above, then ask a question or share work for feedback.
              </p>
            </div>
          )}

          {themedMessages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  m.role === 'user'
                    ? 'bg-leaf/15 text-ink text-sm leading-relaxed'
                    : 'bg-sand/40 text-eco-text border-l-2'
                }`}
                style={m.role === 'assistant' ? { borderLeftColor: accent } : undefined}
              >
                {m.role === 'user'
                  ? <GeneratedContent content={m.content} variant="chat" />
                  : <GeneratedContent content={m.content} variant="chat" />
                }
              </div>
            </div>
          ))}

          {(sending || uploadingFeedback) && (
            <div className="flex justify-start animate-fade-in">
              <div className="bg-sand/40 rounded-2xl px-4 py-3 border-l-2" style={{ borderLeftColor: accent }}>
                <Loader2 className="animate-spin" size={18} style={{ color: accent }} />
              </div>
            </div>
          )}

          <div ref={messagesEnd} />

          {showScrollTop && (
            <button
              onClick={() => messagesRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
              className="sticky bottom-2 ml-auto block p-2 rounded-full bg-white border border-eco-border shadow-sm hover:bg-sand/40"
              title="Scroll to top"
              aria-label="Scroll to top"
            >
              <ArrowUp size={16} />
            </button>
          )}
        </div>

        {/* upload panel */}
        {showUpload && (
          <div className="mt-2 p-3 bg-eco-card border border-eco-border rounded-2xl">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-ink">Get feedback on your work</h4>
              <button
                onClick={() => { setShowUpload(false); setWorkFile(null); setRubricFile(null); }}
                className="p-1 rounded-lg hover:bg-sand/50"
                aria-label="Close upload panel"
              >
                <X size={16} />
              </button>
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              <FileSlot
                label="Your work (required)"
                file={workFile}
                onPick={setWorkFile}
                accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg"
                Icon={FileText}
              />
              <FileSlot
                label="Rubric (optional)"
                file={rubricFile}
                onPick={setRubricFile}
                accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg"
                Icon={FileCheck2}
              />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xs text-eco-text/60">
                PDFs, Word docs, plain text, or images. We'll align feedback to {yearLevel} {selectedSubjects.length ? selectedSubjects.join(', ') : 'AC V9 standards'}.
              </p>
              <button
                onClick={handleFeedbackUpload}
                disabled={!workFile || uploadingFeedback}
                className="px-3 py-1.5 text-sm font-medium text-white rounded-xl disabled:opacity-50 transition-colors flex items-center gap-2"
                style={{ background: accent }}
              >
                {uploadingFeedback ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                How about some feedback?
              </button>
            </div>
          </div>
        )}

        {/* composer */}
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => setShowUpload(o => !o)}
            className={`p-3 rounded-xl border transition-colors ${
              showUpload
                ? 'bg-leaf/15 border-leaf/30 text-leaf'
                : 'bg-eco-card border-eco-border text-eco-text/70 hover:text-ink'
            }`}
            title="Upload work for feedback"
            aria-label="Upload work for feedback"
          >
            <Paperclip size={18} />
          </button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={activeSubject
              ? `Ask anything about ${activeSubject}…`
              : 'Ask a question, or pick a subject above'}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-eco-border bg-eco-card px-4 py-3 text-sm text-ink placeholder:text-eco-text/40 focus:border-leaf focus:ring-0 transition-colors"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            onInput={(e) => {
              const t = e.target as HTMLTextAreaElement;
              t.style.height = 'auto';
              t.style.height = Math.min(t.scrollHeight, 120) + 'px';
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || sending}
            className="px-4 py-3 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
            style={{ background: accent }}
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </div>
      </main>

      {/* ----- toast ----- */}
      {restoredToast && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-ink text-white text-sm px-4 py-2 rounded-full shadow-lg flex items-center gap-2 animate-fade-in z-50"
        >
          <CheckCircle size={14} />
          {restoredToast}
        </div>
      )}

      {/* ----- safety modal ----- */}
      {showSafety && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20">
          <div className="bg-eco-card rounded-2xl border border-eco-border p-6 w-full max-w-sm mx-4 shadow-xl animate-fade-in">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-serif text-ink">Report a Concern</h3>
              <button
                onClick={() => { setShowSafety(false); setSafetyText(''); setSafetySent(false); }}
                className="p-1 rounded-lg hover:bg-sand/50"
                aria-label="Close"
              >
                <X size={18} />
              </button>
            </div>
            {safetySent ? (
              <div className="text-center py-6">
                <CheckCircle className="mx-auto text-leaf mb-3" size={36} />
                <p className="text-sm text-ink font-medium">Your report has been sent.</p>
                <p className="text-xs text-eco-text/60 mt-1">A trusted adult will review this.</p>
              </div>
            ) : (
              <>
                <p className="text-sm text-eco-text/60 mb-4">
                  If something made you uncomfortable, please tell a trusted adult. You can also let us know here.
                </p>
                <textarea
                  rows={3}
                  value={safetyText}
                  onChange={e => setSafetyText(e.target.value)}
                  placeholder="What happened?"
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none mb-3"
                />
                <button
                  onClick={handleSafetyReport}
                  disabled={safetySending || !safetyText.trim()}
                  className="w-full py-2 bg-warning hover:bg-warning/80 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {safetySending && <Loader2 size={14} className="animate-spin" />}
                  Send report
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface FileSlotProps {
  label: string;
  file: File | null;
  onPick: (f: File | null) => void;
  accept: string;
  Icon: typeof FileText;
}

function FileSlot({ label, file, onPick, accept, Icon }: FileSlotProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <label className="block cursor-pointer">
      <span className="text-xs text-eco-text/60">{label}</span>
      <div
        className="mt-1 flex items-center gap-2 p-2 rounded-xl border border-dashed border-eco-border bg-white/60 hover:border-leaf/50"
        onClick={() => inputRef.current?.click()}
      >
        <Icon size={16} className="text-eco-text/60" />
        <span className="text-sm text-ink truncate flex-1">
          {file ? file.name : 'Choose a file'}
        </span>
        {file && (
          <button
            onClick={e => { e.stopPropagation(); onPick(null); }}
            className="p-1 rounded hover:bg-sand/40 text-eco-text/60"
            aria-label="Remove file"
          >
            <X size={14} />
          </button>
        )}
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={accept}
          onChange={e => onPick(e.target.files?.[0] || null)}
        />
      </div>
    </label>
  );
}
