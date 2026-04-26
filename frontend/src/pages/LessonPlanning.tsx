import { useState, useRef, useEffect } from 'react';
import { tools, api } from '../lib/api';
import type {
  LessonPlanRequest, AlignRequest, DifferentiateRequest,
  SavedLessonPlan, SavedLessonPlanKind,
} from '../lib/types';
import {
  Loader2, BookOpen, Target, Layers, Upload, X, FileText, Copy, Printer,
  Check, Pencil, Eye, Plus, BookMarked, ArrowLeft, Trash2, Save,
} from 'lucide-react';
import EditableGeneratedContent, { htmlToPlainText } from '../components/EditableGeneratedContent';

type Mode = 'generate' | 'align' | 'differentiate';
type View = 'create' | 'library' | 'detail';

const modes: { key: Mode; icon: typeof BookOpen; label: string; desc: string; kind: SavedLessonPlanKind }[] = [
  { key: 'generate', icon: BookOpen, label: 'Generate Plan', desc: 'Create a full lesson plan', kind: 'lesson_plan' },
  { key: 'align', icon: Target, label: 'Align Curriculum', desc: 'Analyze curriculum alignment', kind: 'alignment' },
  { key: 'differentiate', icon: Layers, label: 'Differentiate', desc: 'Adapt for diverse learners', kind: 'differentiation' },
];

const focusAreaOptions = [
  'All learners (full differentiation)',
  'Learning support (struggling students)',
  'Extension (gifted & talented)',
  'EAL/D language support',
  'Neurodiversity (autism, ADHD, dyslexia)',
];

const kindLabels: Record<SavedLessonPlanKind, string> = {
  lesson_plan: 'Lesson Plan',
  alignment: 'Alignment',
  differentiation: 'Differentiation',
};

const kindBadgeStyles: Record<SavedLessonPlanKind, string> = {
  lesson_plan: 'bg-leaf/15 text-leaf-dark',
  alignment: 'bg-sky/30 text-ink',
  differentiation: 'bg-clay/15 text-clay',
};

export default function LessonPlanning() {
  const [view, setView] = useState<View>('create');
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
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [savedPlans, setSavedPlans] = useState<SavedLessonPlan[]>([]);
  const [loadingPlans, setLoadingPlans] = useState(false);
  const [libraryError, setLibraryError] = useState('');
  const [selectedPlan, setSelectedPlan] = useState<SavedLessonPlan | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [detailEditedHtml, setDetailEditedHtml] = useState<string | null>(null);
  const [detailIsEditing, setDetailIsEditing] = useState(false);
  const [detailCopied, setDetailCopied] = useState(false);
  const [detailSaving, setDetailSaving] = useState(false);
  const [detailSaved, setDetailSaved] = useState(false);
  const [detailDirty, setDetailDirty] = useState(false);

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

  const copyText = async (text: string) => {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      copyTextFallback(text);
    }
  };

  const handleCopy = async () => {
    const text = editedHtml !== null ? htmlToPlainText(editedHtml) : result;
    if (!text) return;
    await copyText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handleDetailCopy = async () => {
    if (!selectedPlan) return;
    const text = detailEditedHtml !== null ? htmlToPlainText(detailEditedHtml) : selectedPlan.content;
    if (!text) return;
    await copyText(text);
    setDetailCopied(true);
    setTimeout(() => setDetailCopied(false), 1800);
  };

  const handlePrint = () => window.print();

  const currentMode = modes.find(m => m.key === mode);
  const modeLabel = currentMode?.label || 'Result';

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

  const resetGeneratedState = () => {
    setResult('');
    setEditedHtml(null);
    setIsEditing(false);
    setSavedId(null);
    setSaveError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    resetGeneratedState();
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

  const handleSave = async () => {
    if (!result || saving) return;
    setSaving(true);
    setSaveError('');
    try {
      const contentToSave = editedHtml !== null ? htmlToPlainText(editedHtml) : result;
      const kind = currentMode?.kind || 'lesson_plan';
      const titleParts = [topic.trim() || modeLabel];
      if (mode !== 'generate') titleParts.push(`(${kindLabels[kind]})`);
      const title = titleParts.join(' ');
      if (savedId) {
        // Updates only touch the current/edited content + metadata. The
        // original AI-generated version on the server is intentionally left alone.
        await tools.updateSavedLessonPlan(savedId, {
          title,
          content: contentToSave,
          age_group: ageGroup,
          kind,
          topic: topic.trim() || undefined,
          subject: subject.trim() || undefined,
          duration: duration.trim() || undefined,
        });
      } else {
        // First save: capture the AI-generated `result` as the immutable
        // original alongside whatever the user has now (which may be edited).
        const saved = await tools.saveLessonPlan({
          title,
          content: contentToSave,
          original_content: result,
          age_group: ageGroup,
          kind,
          topic: topic.trim() || undefined,
          subject: subject.trim() || undefined,
          duration: duration.trim() || undefined,
        });
        setSavedId(saved.id);
      }
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDetailSave = async () => {
    if (!selectedPlan || detailSaving) return;
    setDetailSaving(true);
    setDetailError('');
    try {
      const contentToSave = detailEditedHtml !== null ? htmlToPlainText(detailEditedHtml) : selectedPlan.content;
      const updated = await tools.updateSavedLessonPlan(selectedPlan.id, { content: contentToSave });
      setSelectedPlan(updated);
      setSavedPlans(plans =>
        plans.map(p => (p.id === updated.id ? { ...p, ...updated } : p)),
      );
      setDetailDirty(false);
      setDetailSaved(true);
      setTimeout(() => setDetailSaved(false), 2000);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : 'Failed to save changes. Please try again.');
    } finally {
      setDetailSaving(false);
    }
  };

  const loadSavedPlans = async () => {
    setLoadingPlans(true);
    setLibraryError('');
    try {
      const res = await tools.listSavedLessonPlans();
      setSavedPlans(res.plans);
    } catch (e) {
      setLibraryError(e instanceof Error ? e.message : 'Failed to load saved lesson plans.');
    } finally {
      setLoadingPlans(false);
    }
  };

  useEffect(() => {
    if (view === 'library') loadSavedPlans();
  }, [view]);

  const openPlan = async (plan: SavedLessonPlan) => {
    setLoadingPlan(true);
    setView('detail');
    setSelectedPlan(plan);
    setDetailEditedHtml(null);
    setDetailIsEditing(false);
    setDetailCopied(false);
    setDetailError('');
    setDetailSaving(false);
    setDetailSaved(false);
    setDetailDirty(false);
    try {
      const full = await tools.getSavedLessonPlan(plan.id);
      setSelectedPlan(full);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : 'Failed to load this saved plan. Showing the version from your library.');
    } finally {
      setLoadingPlan(false);
    }
  };

  const handleDetailEditedHtmlChange = (html: string) => {
    setDetailEditedHtml(html);
    setDetailDirty(true);
    setDetailSaved(false);
  };

  const handleResetToOriginal = () => {
    if (!selectedPlan) return;
    const original = selectedPlan.original_content ?? selectedPlan.content;
    if (!original) return;
    if (!confirm('Replace your edits with the original AI-generated version? Your saved edits will only persist if you click Save changes after.')) return;
    setSelectedPlan({ ...selectedPlan, content: original });
    setDetailEditedHtml(null);
    setDetailDirty(true);
    setDetailSaved(false);
  };

  const handleDeletePlan = async (id: string) => {
    if (!confirm('Delete this saved lesson plan?')) return;
    try {
      await tools.deleteSavedLessonPlan(id);
      setSavedPlans(plans => plans.filter(p => p.id !== id));
      setLibraryError('');
      if (selectedPlan?.id === id) {
        setSelectedPlan(null);
        setView('library');
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to delete this lesson plan.';
      if (selectedPlan?.id === id) {
        setDetailError(msg);
      } else {
        setLibraryError(msg);
      }
    }
  };

  if (view === 'detail' && selectedPlan) {
    const plan = selectedPlan;
    const planKind = (plan.kind || 'lesson_plan') as SavedLessonPlanKind;
    return (
      <div className="animate-fade-in">
        <button
          onClick={() => { setView('library'); setSelectedPlan(null); }}
          className="mb-4 inline-flex items-center gap-1 text-sm text-eco-accent hover:text-eco-hover transition-colors"
        >
          <ArrowLeft size={14} /> Back to library
        </button>
        <div className={`bg-eco-card rounded-2xl border border-eco-border p-6 ${plan.content ? 'printable-area' : ''}`}>
          {loadingPlan ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
          ) : (
            <>
              <div className="flex items-start justify-between gap-3 mb-4 no-print">
                <div className="min-w-0">
                  <h2 className="text-2xl font-serif text-ink truncate">{plan.title || plan.topic || 'Untitled'}</h2>
                </div>
                <div className="flex items-center gap-1.5 shrink-0 flex-wrap justify-end">
                  {(detailDirty || detailSaving || detailSaved) && (
                    <button
                      type="button"
                      onClick={handleDetailSave}
                      disabled={detailSaving || !detailDirty}
                      className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        detailSaved
                          ? 'bg-leaf/15 text-leaf-dark cursor-default'
                          : 'bg-leaf hover:bg-leaf-dark text-white disabled:opacity-50'
                      }`}
                      title={detailDirty ? 'Save changes to library' : 'No unsaved changes'}
                    >
                      {detailSaving ? (
                        <><Loader2 size={13} className="animate-spin" /> Saving...</>
                      ) : detailSaved ? (
                        <><Check size={13} /> Saved</>
                      ) : (
                        <><Save size={13} /> Save changes</>
                      )}
                    </button>
                  )}
                  {detailIsEditing
                    && plan.original_content
                    && plan.original_content !== plan.content
                    && (
                    <button
                      type="button"
                      onClick={handleResetToOriginal}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                      title="Replace with the original AI-generated version"
                    >
                      Reset to original
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setDetailIsEditing(v => !v)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      detailIsEditing
                        ? 'bg-leaf/15 text-leaf-dark hover:bg-leaf/25'
                        : 'text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand'
                    }`}
                    title={detailIsEditing ? 'Switch to view mode' : 'Edit content'}
                  >
                    {detailIsEditing ? <><Eye size={13} /> View</> : <><Pencil size={13} /> Edit</>}
                  </button>
                  <button
                    type="button"
                    onClick={handleDetailCopy}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Copy to clipboard"
                  >
                    {detailCopied ? <><Check size={13} className="text-leaf-dark" /> Copied</> : <><Copy size={13} /> Copy</>}
                  </button>
                  <button
                    type="button"
                    onClick={handlePrint}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-eco-text/70 hover:text-ink bg-sand/40 hover:bg-sand transition-colors"
                    title="Print or save as PDF"
                  >
                    <Printer size={13} /> Print
                  </button>
                  <button
                    onClick={() => handleDeletePlan(plan.id)}
                    className="p-2 rounded-xl text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors"
                    title="Delete saved plan"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mb-4 text-xs no-print">
                <span className={`px-2 py-1 rounded-lg ${kindBadgeStyles[planKind]}`}>{kindLabels[planKind]}</span>
                {plan.age_group && <span className="px-2 py-1 bg-sand/50 rounded-lg text-eco-text/70">Ages {plan.age_group}</span>}
                {plan.subject && <span className="px-2 py-1 bg-sand/50 rounded-lg text-eco-text/70">{plan.subject}</span>}
                {plan.duration && <span className="px-2 py-1 bg-sand/50 rounded-lg text-eco-text/70">{plan.duration} min</span>}
                {plan.created_at && (
                  <span className="px-2 py-1 bg-eco-bg rounded-lg text-eco-text/70">
                    {new Date(plan.created_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <div className="hidden print:block mb-4 pb-3 border-b border-eco-border">
                <h1 className="font-serif text-2xl text-ink m-0">{plan.title || plan.topic || 'Lesson plan'}</h1>
                <p className="text-sm text-eco-text/70 mt-1">
                  {[plan.age_group && `Ages ${plan.age_group}`, plan.duration && `${plan.duration} minutes`, plan.subject].filter(Boolean).join(' · ')}
                </p>
              </div>
              {detailError && (
                <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3 no-print">
                  {detailError}
                </div>
              )}
              <EditableGeneratedContent
                markdown={plan.content || ''}
                editedHtml={detailEditedHtml}
                isEditing={detailIsEditing}
                onEditedHtmlChange={handleDetailEditedHtmlChange}
              />
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-start justify-between mb-1 gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-serif text-ink">Lesson Planning</h2>
          <p className="text-sm text-eco-text/60">AI-powered tools for Montessori lesson preparation</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView('create')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              view === 'create'
                ? 'bg-leaf/15 text-leaf-dark border border-leaf/30'
                : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}
          >
            <Plus size={14} className="inline mr-1" /> Create
          </button>
          <button
            onClick={() => setView('library')}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
              view === 'library'
                ? 'bg-leaf/15 text-leaf-dark border border-leaf/30'
                : 'bg-eco-card border border-eco-border text-eco-text/70 hover:bg-sand/50'
            }`}
          >
            <BookMarked size={14} className="inline mr-1" /> Library
          </button>
        </div>
      </div>

      {view === 'create' ? (
        <>
          <div className="flex gap-2 my-6 flex-wrap">
            {modes.map(m => (
              <button
                key={m.key}
                onClick={() => { setMode(m.key); resetGeneratedState(); }}
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
                  {loading ? <><Loader2 size={16} className="animate-spin" /> Generating...</> : modeLabel}
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
                  <div className="flex gap-1.5 shrink-0 flex-wrap justify-end">
                    <button type="button" onClick={handleSave} disabled={saving}
                      className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors bg-leaf hover:bg-leaf-dark text-white disabled:opacity-50"
                      title={savedId !== null ? 'Update saved lesson plan' : 'Save to library'}>
                      {saving ? (
                        <><Loader2 size={13} className="animate-spin" /> Saving...</>
                      ) : savedId !== null ? (
                        <><Save size={13} /> Save changes</>
                      ) : (
                        <><Save size={13} /> Save</>
                      )}
                    </button>
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
              {saveError && <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3 no-print">{saveError}</div>}
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
        </>
      ) : (
        <div className="bg-eco-card rounded-2xl border border-eco-border p-6 mt-6">
          {libraryError && (
            <div className="p-3 bg-soft-rose/50 border border-danger/20 rounded-xl text-sm text-danger mb-3 flex items-start justify-between gap-3">
              <span>{libraryError}</span>
              <button
                onClick={loadSavedPlans}
                className="text-xs underline shrink-0 hover:text-ink"
              >
                Retry
              </button>
            </div>
          )}
          {loadingPlans ? (
            <div className="flex justify-center py-8"><Loader2 className="animate-spin text-leaf" size={24} /></div>
          ) : savedPlans.length === 0 ? (
            <p className="text-center text-sm text-eco-text/50 py-8">
              No saved lesson plans yet. Generate one and click <span className="font-medium text-ink">Save</span> to add it here.
            </p>
          ) : (
            <div className="space-y-3">
              {savedPlans.map(plan => {
                const planKind = (plan.kind || 'lesson_plan') as SavedLessonPlanKind;
                return (
                  <div key={plan.id} className="flex items-center gap-3 p-4 bg-sand/20 rounded-xl">
                    <BookOpen size={18} className="text-leaf shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-sans text-sm font-medium text-ink truncate">{plan.title || plan.topic || 'Untitled'}</h4>
                        <span className={`px-2 py-0.5 rounded-lg text-[10px] uppercase tracking-wide font-semibold ${kindBadgeStyles[planKind]}`}>
                          {kindLabels[planKind]}
                        </span>
                      </div>
                      <p className="text-xs text-eco-text/50 mt-0.5">
                        {[
                          plan.age_group && `Ages ${plan.age_group}`,
                          plan.subject,
                          plan.duration && `${plan.duration} min`,
                          plan.created_at && new Date(plan.created_at).toLocaleDateString(),
                        ].filter(Boolean).join(' · ')}
                      </p>
                    </div>
                    <button
                      onClick={() => openPlan(plan)}
                      className="p-1.5 rounded-lg text-eco-text/40 hover:text-ink hover:bg-sand/50 transition-colors"
                      title="View lesson plan"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      onClick={() => handleDeletePlan(plan.id)}
                      className="p-1.5 rounded-lg text-eco-text/40 hover:text-danger hover:bg-soft-rose/30 transition-colors"
                      title="Delete saved plan"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
