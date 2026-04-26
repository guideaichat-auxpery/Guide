import { memo, useMemo } from 'react';
import MarkdownIt from 'markdown-it';

interface Props {
  content: string;
  variant?: 'default' | 'prose' | 'chat';
  className?: string;
}

const md = new MarkdownIt({ html: false, linkify: true, breaks: false });

function looksLikeMarkdown(text: string): boolean {
  return /(^|\n)\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|>\s|```|\|.*\|)/.test(text)
    || /\*\*[^*]+\*\*/.test(text)
    || /(^|[\s(])\*[^*\n]+\*([\s.,;:!?)]|$)/.test(text);
}

function GeneratedContentInner({ content, variant = 'default', className = '' }: Props) {
  const variantClass =
    variant === 'prose'
      ? 'generated-content generated-content--prose'
      : variant === 'chat'
        ? 'generated-content generated-content--chat'
        : 'generated-content';

  const isMarkdown = looksLikeMarkdown(content);

  const html = useMemo(
    () => (isMarkdown ? md.render(content || '') : ''),
    [isMarkdown, content],
  );

  if (!isMarkdown) {
    return (
      <div className={`${variantClass} ${className}`.trim()}>
        {content.split(/\n{2,}/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    );
  }

  return (
    <div
      className={`${variantClass} ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export default memo(GeneratedContentInner);
