import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  variant?: 'default' | 'prose' | 'chat';
  className?: string;
}

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

  if (!looksLikeMarkdown(content)) {
    return (
      <div className={`${variantClass} ${className}`.trim()}>
        {content.split(/\n{2,}/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    );
  }

  return (
    <div className={`${variantClass} ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

export default memo(GeneratedContentInner);
