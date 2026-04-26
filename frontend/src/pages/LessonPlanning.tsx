import { useState, useRef } from 'react';
import { tools, api } from '../lib/api';
import type { LessonPlanRequest, AlignRequest, DifferentiateRequest } from '../lib/types';
import { Loader2, BookOpen, Target, Layers, Upload, X, FileText, Copy, Printer, Check, Pencil, Eye } from 'lucide-react';
import EditableGeneratedContent, { htmlToPlainText } from '../components/EditableGeneratedContent';

type Mode = 'generate' | 'align' | 'differentiate';

const modes: { key: Mode; icon: typeof BookOpen; label: string; desc: string }[] = [
  { key: 'generate', icon: BookOpen, label: 'Generate Plan', desc: 'Create a full lesson plan' },
  { key: 'align', icon: Target, label: 'Align Curriculum', desc: 'Analyze curriculum alignment' },
  { key: 'differentiate', icon: Layers, label: 'Differentiate', desc: 'Adapt for diverse learners' },
];

const focusAreaOptions = [
  'All learners (full differentiation)',
  'Learning support (struggling students)',
  'Extension (gifted & talented)',
  'EAL/D language support',
  'Neurodiversity (autism, ADHD, dyslexia)',
];

export default function LessonPlanning() {
  const [mode, setMode] = useState<Mode>('generate');
  const [topic, setTopic] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-9');
  const [subject, setSubject] = useState('');
  const [duration, setDuration] = useState('45');
  const [additional, setAdditional] = useState('');
  const [lessonDescription, setLessonDescription] = useState('');
  const [classComposition, setClassComposition] = useState('');
  const [focusArea, setFocusArea] = useState(focusAreaOptions[0]);
  const [result, setResult] = useState('');
  const [editedHtml, setEditedHtml] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [uploading, setUploading] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const copyTextFallback = (text: string) => {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch { /* noop */ }
    document.body.removeChild(ta);
  };

  const handleCopy = async () => {
    const text = editedHtml !== null ? htmlToPlainText(editedHtml) : result;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      copyTextFallback(text);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handlePrint = () => window.print();

  const modeLabel = modes.find(m => m.key === mode)?.label || 'Result';

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    if (!validTypes.includes(file.type) && !file.name.endsWith('.txt') && !file.name.endsWith('.pdf') && !file.name.endsWith('.docx')) {
      setError('Please upload a PDF, DOCX, or TXT file');
      return;
    }
    setUploadedFile(file);
    setError('');

    if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setFileContent(ev.target?.result as string || '');
      };
      reader.readAsText(file);
    } else {
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await api.postForm<{ content: string }>('/tools/upload-document', formData);
        setFileContent(res.content);
      } catch {
        const reader = new FileReader();
        reader.onload = (ev) => {
          const base64 = ev.target?.result as string || '';
          setFileContent(`[Document: ${file.name}]\n\n${base64.substring(0, 500)}`);
        };
        reader.readAsDataURL(file);
      } finally {
        setUploading(false);
      }
    }
  };

  const removeFile = () => {
    setUploadedFile(null);
    setFileContent('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult('');
    setEditedHtml(null);
    setIsEditing(false);
    try {
      const additionalContext = [additional, fileContent].filter(Boolean).join('\n\n') || undefined;
      let res: { content: string };
      if (mode === 'generate') {
        const payload: LessonPlanRequest = {
          topic,
          age_group: ageGroup,
          subject: subject || undefined,
          duration: duration || undefined,
          additional_context: additionalContext,
        };
        res = await tools.lessonPlan(payload);
      } else if (mode === 'align') {
        const payload: AlignRequest = {
          topic,
          age_group: ageGroup,
          subject: subject || undefined,
          duration: duration || undefined,
          additional_context: additionalContext,
        };
        res = await tools.align(payload);
      } else {
        const payload: DifferentiateRequest = {
          topic,
          age_group: ageGroup,
          subject: subject || undefined,
          duration: duration || undefined,
          additional_context: additionalContext,
          lesson_description: lessonDescription.trim() || undefined,
          class_composition: classComposition.trim() || undefined,
          focus_area: focusArea || undefined,
        };
        res = await tools.differentiate(payload);
      }
      setResult(res.content);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <h2 className="text-2xl font-serif text-ink mb-1">Lesson Planning</h2>
      <p className="text-sm text-eco-text/60 mb-6">AI-powered tools for Montessori lesson preparation</p>

      <div className="flex gap-2 mb-6 flex-wrap">
        {modes.map(m => (
          <button
            key={m.key}
            onClick={() => { setMode(m.key); setResult(''); setEditedHtml(null); setIsEditing(false); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              mode === m.key ? 'bg-leaf/15 text-leaf-dark border border-leaf/30' : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}
          >
            <m.icon size={16} />
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Topic</label>
              <input value={topic} onChange={e => setTopic(e.target.value)} required
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                placeholder="e.g., Fractions with bead chains" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Age group</label>
                <select value={ageGroup} onChange={e => setAgeGroup(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                  <option value="3-6">3-6 (Primary)</option>
                  <option value="6-9">6-9 (Lower Elementary)</option>
                  <option value="9-12">9-12 (Upper Elementary)</option>
                  <option value="12-15">12-15 (Adolescent)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-ink mb-1.5">Duration (min)</label>
                <input type="number" value={duration} onChange={e => setDuration(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Subject area</label>
              <input value={subject} onChange={e => setSubject(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                placeholder="e.g., Mathematics, Language, Science" />
            </div>
            {mode === 'differentiate' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1.5">
                    Lesson description <span className="text-eco-text/40 font-normal">(optional)</span>
                  </label>
                  <textarea value={lessonDescription} onChange={e => setLessonDescription(e.target.value)} rows={3}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none"
                    placeholder="e.g., Students investigate the water cycle through observation journals and outdoor exploration over 3 sessions." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1.5">
                    Class composition <span className="text-eco-text/40 font-normal">(optional)</span>
                  </label>
                  <input value={classComposition} onChange={e => setClassComposition(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf"
                    placeholder="e.g., 3 dyslexic, 2 EAL/D, 1 gifted, 20 on-track. Mixed Year 4/5." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-ink mb-1.5">Differentiation focus</label>
                  <select value={focusArea} onChange={e => setFocusArea(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf">
                    {focusAreaOptions.map(opt => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </div>
              </>
            )}
            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Additional context</label>
              <textarea value={additional} onChange={e => setAdditional(e.target.value)} rows={3}
                className="w-full px-4 py-2.5 rounded-xl border border-eco-border bg-white text-sm text-ink focus:border-leaf resize-none"
                placeholder="Any specific requirements, materials, or student needs..." />
            </div>

            <div>
              <label className="block text-sm font-medium text-ink mb-1.5">Upload document (optional)</label>
              {uploadedFile ? (
                <div className="flex items-center gap-3 p-3 bg-sand/30 rounded-xl">
                  <FileText size={18} className="text-eco-accent shrink-0" />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-ink truncate block">{uploadedFile.name}</span>
                    {uploading && <span className="text-xs text-eco-text/50 flex items-center gap-1"><Loader2 size={10} className="animate-spin" /> Processing...</span>}
                    {!uploading && fileContent && <span className="text-xs text-leaf-dark">Ready</span>}
                  </div>
                  <button type="button" onClick={removeFile} className="p-1 rounded-lg hover:bg-sand text-eco-text/40 hover:text-ink">
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 p-3 border-2 border-dashed border-eco-border rounded-xl text-sm text-eco-text/50 hover:border-leaf/40 hover:text-ink transition-colors">
                  <Upload size={16} />
                  Upload PDF, DOCX, or TXT
                </button>
              )}
              <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt" onChange={handleFileUpload} className="hidden" />
            </div>

            <button type="submit" disabled={loading || uploading}
              className="w-full py-2.5 bg-leaf hover:bg-leaf-dark disabled:opacity-50 text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2">
              {loading ? <><Loader2 size={16} className="animate-spin" /> Generating...</> : modes.find(m => m.key === mode)?.label}
            </button>
          </form>
        </div>

        <div className={`bg-eco-card rounded-2xl border border-eco-border p-6 ${result ? 'printable-area' : ''}`}>
          <div className="flex items-start justify-between gap-3 mb-3 no-print">
            <div>
              <h3 className="font-sans text-sm font-semibold text-ink">{modeLabel}</h3>
              {result && (topic || ageGroup || duration) && (
                <p className="text-xs text-eco-text/60 mt-0.5">
                  {[topic, ageGroup && `Ages ${ageGroup}`, duration && `${duration} min`, subject].filter(Boolean).join(' · ')}
                </p>
              )}
            </div>
            {result && (
              <div className="flex gap-1.5 shrink-0">
                <button type="button" onClick={() => setIsEditing(v => !v)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isEditing
                      ? 'bg-leaf/15 text-leaf-dark hover:bg-leaf/25'
                      : 'text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand'
                  }`}
                  title={isEditing ? 'Switch to view mode' : 'Edit content'}>
                  {isEditing ? <><Eye size={13} /> View</> : <><Pencil size={13} /> Edit</>}
                </button>
                <button type="button" onClick={handleCopy}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                  title="Copy to clipboard">
                  {copied ? <><Check size={13} className="text-leaf-dark" /> Copied</> : <><Copy size={13} /> Copy</>}
                </button>
                <button type="button" onClick={handlePrint}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                  title="Print or save as PDF">
                  <Printer size={13} /> Print
                </button>
              </div>
            )}
          </div>

          <div className="hidden print:block mb-4 pb-3 border-b border-eco-border">
            <h1 className="font-serif text-2xl text-ink m-0">{topic || modeLabel}</h1>
            <p className="text-sm text-eco-text/70 mt-1">
              {[ageGroup && `Ages ${ageGroup}`, duration && `${duration} minutes`, subject].filter(Boolean).join(' · ')}
            </p>
          </div>

          {error && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3 no-print">{error}</div>}
          {result ? (
            <div className="max-h-[60vh] overflow-y-auto print:max-h-none print:overflow-visible">
              <EditableGeneratedContent
                markdown={result}
                editedHtml={editedHtml}
                isEditing={isEditing}
                onEditedHtmlChange={setEditedHtml}
              />
            </div>
          ) : (
            <p className="text-sm text-eco-text/40 italic">Your generated content will appear here...</p>
          )}
        </div>
      </div>
    </div>
  );
}
