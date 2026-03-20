import React from 'react';
import ReactMarkdown from 'react-markdown';

export const MarkdownContent: React.FC<{ content: string }> = ({ content }) => {
    return (
        <div className="prose prose-invert prose-sm max-w-none prose-headings:mb-2 prose-headings:mt-4 prose-p:my-2 prose-ul:my-2 prose-li:my-1">
            <ReactMarkdown>{content}</ReactMarkdown>
        </div>
    );
};
