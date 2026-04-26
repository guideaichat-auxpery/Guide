import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import ImageExtension from '@tiptap/extension-image';
import LinkExtension from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { useRef, useEffect, useState } from 'react';
import { api } from '../lib/api';
import {
  Bold,
  Italic,
  List,
  Heading2,
  Link2,
  Code,
  Image,
  Quote,
  ListOrdered,
  Undo2,
  Redo2,
  Minus,
  MoreHorizontal,
} from 'lucide-react';

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
}

interface ToolbarButton {
  icon: typeof Bold;
  action: () => void;
  title: string;
  active: boolean;
}

export default function RichTextEditor({ content, onChange, placeholder }: RichTextEditorProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);
  const overflowRef = useRef<HTMLDivElement>(null);
  const [overflowOpen, setOverflowOpen] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      ImageExtension.configure({ inline: false }),
      LinkExtension.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder: placeholder || 'Start writing...' }),
    ],
    content,
    onUpdate: ({ editor: e }) => {
      onChange(e.getHTML());
    },
  });

  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content]);

  useEffect(() => {
    if (!overflowOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (overflowRef.current && !overflowRef.current.contains(e.target as Node)) {
        setOverflowOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOverflowOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [overflowOpen]);

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !editor) return;
    if (!file.type.startsWith('image/')) return;

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.postForm<{ url: string }>('/tools/upload-image', formData);
      editor.chain().focus().setImage({ src: res.url, alt: file.name }).run();
    } catch {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result as string;
        editor.chain().focus().setImage({ src: dataUrl, alt: file.name }).run();
      };
      reader.readAsDataURL(file);
    }
    if (imageInputRef.current) imageInputRef.current.value = '';
  };

  const addLink = () => {
    if (!editor) return;
    const url = window.prompt('Enter URL:');
    if (url) {
      editor.chain().focus().setLink({ href: url }).run();
    }
  };

  if (!editor) return null;

  const historyButtons: ToolbarButton[] = [
    { icon: Undo2, action: () => editor.chain().focus().undo().run(), title: 'Undo', active: false },
    { icon: Redo2, action: () => editor.chain().focus().redo().run(), title: 'Redo', active: false },
  ];

  const formatButtons: ToolbarButton[] = [
    { icon: Bold, action: () => editor.chain().focus().toggleBold().run(), title: 'Bold', active: editor.isActive('bold') },
    { icon: Italic, action: () => editor.chain().focus().toggleItalic().run(), title: 'Italic', active: editor.isActive('italic') },
  ];

  const coreBlockButtons: ToolbarButton[] = [
    { icon: Heading2, action: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), title: 'Heading', active: editor.isActive('heading', { level: 2 }) },
    { icon: List, action: () => editor.chain().focus().toggleBulletList().run(), title: 'Bullet List', active: editor.isActive('bulletList') },
  ];

  const extraBlockButtons: ToolbarButton[] = [
    { icon: ListOrdered, action: () => editor.chain().focus().toggleOrderedList().run(), title: 'Numbered List', active: editor.isActive('orderedList') },
  ];

  const overflowButtons: ToolbarButton[] = [
    { icon: Quote, action: () => editor.chain().focus().toggleBlockquote().run(), title: 'Quote', active: editor.isActive('blockquote') },
    { icon: Code, action: () => editor.chain().focus().toggleCodeBlock().run(), title: 'Code Block', active: editor.isActive('codeBlock') },
    { icon: Minus, action: () => editor.chain().focus().setHorizontalRule().run(), title: 'Divider', active: false },
    { icon: Link2, action: addLink, title: 'Link', active: editor.isActive('link') },
    { icon: Image, action: () => imageInputRef.current?.click(), title: 'Insert image', active: false },
  ];

  const mobileMoreItems: ToolbarButton[] = [...extraBlockButtons, ...overflowButtons];

  const buttonClass = (active: boolean) =>
    `inline-flex items-center justify-center min-w-[40px] min-h-[40px] sm:min-w-0 sm:min-h-0 sm:p-1.5 rounded hover:bg-eco-card transition-colors ${
      active ? 'bg-eco-card text-ink' : ''
    }`;

  const iconClass = (active: boolean) => (active ? 'text-ink' : 'text-eco-text/60');

  const renderInlineButton = (btn: ToolbarButton) => (
    <button
      key={btn.title}
      type="button"
      onClick={btn.action}
      className={buttonClass(btn.active)}
      title={btn.title}
      aria-label={btn.title}
      aria-pressed={btn.active}
    >
      <btn.icon size={16} className={iconClass(btn.active)} />
    </button>
  );

  const Separator = ({ desktopOnly = false }: { desktopOnly?: boolean }) => (
    <div
      className={`w-px h-5 bg-eco-border mx-0.5 self-center ${desktopOnly ? 'hidden sm:block' : ''}`}
      aria-hidden="true"
    />
  );

  return (
    <div className="border border-eco-border rounded-xl overflow-hidden">
      <div className="flex items-center gap-0.5 px-2 py-1.5 sm:px-3 sm:py-2 bg-sand/30 border-b border-eco-border flex-nowrap overflow-x-auto no-print">
        {historyButtons.map(renderInlineButton)}
        <Separator desktopOnly />
        {formatButtons.map(renderInlineButton)}
        <Separator desktopOnly />
        {coreBlockButtons.map(renderInlineButton)}

        <div className="hidden sm:flex items-center gap-0.5">
          {extraBlockButtons.map(renderInlineButton)}
          <Separator />
          {overflowButtons.map(renderInlineButton)}
        </div>

        <div className="sm:hidden ml-auto relative" ref={overflowRef}>
          <button
            type="button"
            onClick={() => setOverflowOpen((v) => !v)}
            className={buttonClass(overflowOpen)}
            title="More formatting"
            aria-label="More formatting options"
            aria-haspopup="menu"
            aria-expanded={overflowOpen}
          >
            <MoreHorizontal size={16} className={iconClass(overflowOpen)} />
          </button>
          {overflowOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full mt-1 z-20 min-w-[10rem] rounded-xl border border-eco-border bg-eco-card shadow-lg py-1"
            >
              {mobileMoreItems.map((btn) => (
                <button
                  key={btn.title}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    btn.action();
                    setOverflowOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-sand/50 transition-colors ${
                    btn.active ? 'bg-sand/40 text-ink' : 'text-eco-text'
                  }`}
                >
                  <btn.icon size={16} className={iconClass(btn.active)} />
                  <span>{btn.title}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
        />
      </div>
      <EditorContent editor={editor} className="tiptap-editor" />
    </div>
  );
}
