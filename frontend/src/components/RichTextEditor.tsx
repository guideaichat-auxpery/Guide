import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import ImageExtension from '@tiptap/extension-image';
import LinkExtension from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { useRef, useEffect } from 'react';
import { api } from '../lib/api';
import { Bold, Italic, List, Heading2, Link2, Code, Image, Quote, ListOrdered, Undo2, Redo2, Minus } from 'lucide-react';

interface RichTextEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
}

export default function RichTextEditor({ content, onChange, placeholder }: RichTextEditorProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);

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

  const toolbarButtons = [
    { icon: Undo2, action: () => editor.chain().focus().undo().run(), title: 'Undo', active: false },
    { icon: Redo2, action: () => editor.chain().focus().redo().run(), title: 'Redo', active: false },
    { icon: Bold, action: () => editor.chain().focus().toggleBold().run(), title: 'Bold', active: editor.isActive('bold') },
    { icon: Italic, action: () => editor.chain().focus().toggleItalic().run(), title: 'Italic', active: editor.isActive('italic') },
    { icon: Heading2, action: () => editor.chain().focus().toggleHeading({ level: 2 }).run(), title: 'Heading', active: editor.isActive('heading', { level: 2 }) },
    { icon: List, action: () => editor.chain().focus().toggleBulletList().run(), title: 'Bullet List', active: editor.isActive('bulletList') },
    { icon: ListOrdered, action: () => editor.chain().focus().toggleOrderedList().run(), title: 'Numbered List', active: editor.isActive('orderedList') },
    { icon: Quote, action: () => editor.chain().focus().toggleBlockquote().run(), title: 'Quote', active: editor.isActive('blockquote') },
    { icon: Code, action: () => editor.chain().focus().toggleCodeBlock().run(), title: 'Code Block', active: editor.isActive('codeBlock') },
    { icon: Minus, action: () => editor.chain().focus().setHorizontalRule().run(), title: 'Divider', active: false },
    { icon: Link2, action: addLink, title: 'Link', active: editor.isActive('link') },
  ];

  return (
    <div className="border border-eco-border rounded-xl overflow-hidden">
      <div className="flex items-center gap-0.5 px-3 py-2 bg-sand/30 border-b border-eco-border flex-wrap no-print">
        {toolbarButtons.map((btn, i) => (
          <span key={btn.title}>
            {(i === 2 || i === 5 || i === 9) && <div className="w-px h-4 bg-eco-border mx-0.5 inline-block align-middle" />}
            <button type="button" onClick={btn.action}
              className={`p-1.5 rounded hover:bg-eco-card transition-colors ${btn.active ? 'bg-eco-card text-ink' : ''}`}
              title={btn.title}>
              <btn.icon size={14} className={btn.active ? 'text-ink' : 'text-eco-text/60'} />
            </button>
          </span>
        ))}
        <div className="w-px h-4 bg-eco-border mx-0.5" />
        <button type="button" onClick={() => imageInputRef.current?.click()}
          className="p-1.5 rounded hover:bg-eco-card transition-colors" title="Insert image">
          <Image size={14} className="text-eco-text/60" />
        </button>
        <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
      </div>
      <EditorContent editor={editor} className="tiptap-editor" />
    </div>
  );
}
