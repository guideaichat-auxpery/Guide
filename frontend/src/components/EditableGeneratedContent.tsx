import { memo, useMemo } from 'react';
import MarkdownIt from 'markdown-it';
import GeneratedContent from './GeneratedContent';
import RichTextEditor from './RichTextEditor';

const md = new MarkdownIt({ html: false, linkify: true, breaks: false });

interface Props {
  markdown: string;
  editedHtml: string | null;
  isEditing: boolean;
  onEditedHtmlChange: (html: string) => void;
  variant?: 'default' | 'prose' | 'chat';
  className?: string;
}

function variantToClass(variant: Props['variant']): string {
  if (variant === 'prose') return 'generated-content generated-content--prose';
  if (variant === 'chat') return 'generated-content generated-content--chat';
  return 'generated-content';
}

function EditableGeneratedContentInner({
  markdown,
  editedHtml,
  isEditing,
  onEditedHtmlChange,
  variant = 'default',
  className = '',
}: Props) {
  const initialEditHtml = useMemo(() => {
    if (editedHtml !== null) return editedHtml;
    return md.render(markdown || '');
  }, [editedHtml, markdown]);

  if (isEditing) {
    return (
      <div className={className}>
        <RichTextEditor content={initialEditHtml} onChange={onEditedHtmlChange} />
      </div>
    );
  }

  if (editedHtml !== null) {
    return (
      <div
        className={`${variantToClass(variant)} ${className}`.trim()}
        dangerouslySetInnerHTML={{ __html: editedHtml }}
      />
    );
  }

  return <GeneratedContent content={markdown} variant={variant} className={className} />;
}

export default memo(EditableGeneratedContentInner);

export function htmlToPlainText(html: string): string {
  if (typeof document === 'undefined') return html;
  const div = document.createElement('div');
  div.style.position = 'fixed';
  div.style.left = '-99999px';
  div.style.top = '0';
  div.innerHTML = html;
  document.body.appendChild(div);
  const text = div.innerText || div.textContent || '';
  document.body.removeChild(div);
  return text;
}
