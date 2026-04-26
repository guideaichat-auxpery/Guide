import { useState, useRef } from 'react';
import { tools, api } from '../lib/api';
import type { LessonPlanRequest, AlignRequest, DifferentiateRequest } from '../lib/types';
import { Loader2, BookOpen, Target, Layers, Upload, X, FileText } from 'lucide-react';

type Mode = 'generate' | 'align' | 'differentiate';

const modes: { key: Mode; icon: typeof BookOpen; label: string; desc: string }[] = [
  { key: 'generate', icon: BookOpen, label: 'Generate Plan', desc: 'Create a full lesson plan' },
  { key: 'align', icon: Target, label: 'Align Curriculum', desc: 'Analyze curriculum alignment' },
  { key: 'differentiate', icon: Layers, label: 'Differentiate', desc: 'Adapt for diverse learners' },
];

export default function LessonPlanning() {
  const [mode, setMode] = useState<Mode>('generate');
  const [topic, setTopic] = useState('');
  const [ageGroup, setAgeGroup] = useState('6-9');
  const [subject, setSubject] = useState('');
  const [duration, setDuration] = useState('45');
  const [additional, setAdditional] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileContent, setFileContent] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
            onClick={() => { setMode(m.key); setResult(''); }}
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

        <div className="bg-eco-card rounded-2xl border border-eco-border p-6">
          <h3 className="font-sans text-sm font-semibold text-ink mb-3">Result</h3>
          {error && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3">{error}</div>}
          {result ? (
            <div className="prose text-sm text-eco-text leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">{result}</div>
          ) : (
            <p className="text-sm text-eco-text/40 italic">Your generated content will appear here...</p>
          )}
        </div>
      </div>
    </div>
  );
}
