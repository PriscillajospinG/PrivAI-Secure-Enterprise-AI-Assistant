import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Info, AlertTriangle, BadgeCheck, CircleHelp, Sparkles, Database, ChevronDown, ChevronUp } from 'lucide-react';
import { aiService, getApiErrorMessage, type QueryResponse, type SourceCitation } from '../services/api.service';
import { MarkdownContent } from '../components/MarkdownContent';

interface Message {
    id: string;
    role: 'assistant' | 'user';
    content: string;
    timestamp: string;
    confidence?: number;
    validationStatus?: string;
    validation?: string;
    contextPreview?: string[];
    sources?: SourceCitation[];
    metadata?: {
        retrieved_documents?: number;
        latency_ms?: number;
        cache_hit?: boolean;
    };
    statusMessage?: string;
    error?: string;
    isLoading?: boolean;
}

export const ChatPage: React.FC<{ mode: string }> = ({ mode }) => {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            timestamp: new Date().toISOString(),
            content: `Hello! I am your Secure AI Assistant. I operate entirely locally. How can I help you explore your enterprise knowledge base today?`
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [demoMode, setDemoMode] = useState(true);
    const [showDebug, setShowDebug] = useState(false);
    const [expandedMessage, setExpandedMessage] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const formatTime = (timestamp: string) =>
        new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const confidenceBadgeClass = (confidence?: number) => {
        if (typeof confidence !== 'number') return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
        if (confidence >= 0.7) return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
        if (confidence >= 0.45) return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
    };

    const highlightSnippet = (snippet: string, query: string) => {
        const terms = query
            .toLowerCase()
            .split(/\s+/)
            .map((term) => term.trim())
            .filter((term) => term.length > 2);

        if (terms.length === 0) return snippet;

        return snippet
            .split(/(\s+)/)
            .map((token) => {
                const clean = token.toLowerCase().replace(/[^a-z0-9]/g, '');
                return terms.includes(clean) ? `**${token}**` : token;
            })
            .join('');
    };

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const trimmedInput = input.trim();
        const now = new Date().toISOString();
        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            timestamp: now,
            content: trimmedInput,
        };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        // Add placeholder for assistant response
        const assistantMsgId = (Date.now() + 1).toString();
        setMessages(prev => [
            ...prev,
            {
                id: assistantMsgId,
                role: 'assistant',
                timestamp: new Date().toISOString(),
                content: '',
                isLoading: true,
                statusMessage: 'Retrieving context and preparing response...',
            },
        ]);

        try {
            const result = await aiService.streamQuery({
                query: trimmedInput,
                task_type: mode === 'search' ? 'search' : 'chat'
            }, {
                onStatus: (status) => {
                    const message = typeof status.message === 'string' ? status.message : 'Processing...';
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantMsgId
                            ? { ...msg, statusMessage: message }
                            : msg
                    ));
                },
                onToken: (token) => {
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantMsgId
                            ? { ...msg, content: `${msg.content}${token}` }
                            : msg
                    ));
                },
                onDone: (payload: QueryResponse) => {
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantMsgId
                            ? {
                                ...msg,
                                content: payload.result.response,
                                confidence: payload.result.confidence,
                                validationStatus: payload.result.validation_status,
                                validation: payload.result.validation,
                                contextPreview: payload.result.context_preview,
                                sources: payload.result.sources,
                                metadata: {
                                    retrieved_documents: payload.metadata.retrieved_documents,
                                    latency_ms: payload.metadata.latency_ms,
                                    cache_hit: payload.metadata.cache_hit,
                                },
                                isLoading: false,
                                statusMessage: '',
                            }
                            : msg
                    ));
                },
                onError: (message) => {
                    setMessages(prev => prev.map(msg =>
                        msg.id === assistantMsgId
                            ? { ...msg, content: '', error: message, isLoading: false }
                            : msg
                    ));
                }
            });

            if (result.metadata?.cache_hit) {
                setExpandedMessage(assistantMsgId);
            }
        } catch (err) {
            setMessages(prev => prev.map(msg =>
                msg.id === assistantMsgId
                    ? { ...msg, content: `Request failed: ${getApiErrorMessage(err)}`, error: getApiErrorMessage(err), isLoading: false }
                    : msg
            ));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <header className="px-10 py-6 border-b border-glass-border bg-background/50 backdrop-blur-md flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-display font-bold">
                        {mode === 'chat' ? 'AI Secure Chat' : 'Knowledge Search'}
                    </h2>
                    <p className="text-xs text-slate-500 font-medium">Enterprise RAG Engine (Local)</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setDemoMode(prev => !prev)}
                        className={`px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-wider transition-colors ${demoMode
                                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                                : 'bg-slate-500/10 border-slate-500/20 text-slate-400'
                            }`}
                    >
                        Demo Mode {demoMode ? 'ON' : 'OFF'}
                    </button>
                    <button
                        onClick={() => setShowDebug(prev => !prev)}
                        className={`px-3 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-wider transition-colors ${showDebug
                                ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                                : 'bg-slate-500/10 border-slate-500/20 text-slate-400'
                            }`}
                    >
                        Debug {showDebug ? 'ON' : 'OFF'}
                    </button>
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] font-bold text-blue-400 uppercase tracking-wider">
                        <Bot size={14} />
                        Llama 3 Active
                    </div>
                </div>
            </header>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto px-10 py-8 space-y-6">
                {messages.length <= 1 && (
                    <div className="glass-card border-dashed border-white/20 p-8 text-center max-w-2xl mx-auto">
                        <Sparkles className="mx-auto text-blue-300 mb-3" size={28} />
                        <h3 className="text-lg font-bold text-slate-100">Start your enterprise conversation</h3>
                        <p className="text-slate-400 text-sm mt-2">Ask policy, contract, meeting, or IT-security questions to see grounded answers with explainability.</p>
                    </div>
                )}
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[80%] flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${msg.role === 'user'
                                ? 'bg-accent-secondary shadow-lg shadow-purple-500/20'
                                : 'bg-glass-bg border border-glass-border'
                                }`}>
                                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} className="text-accent-primary" />}
                            </div>
                            <div className={`group relative p-4 rounded-2xl text-[15px] leading-relaxed ${msg.role === 'user'
                                ? 'bg-accent-primary text-white'
                                : 'bg-glass-bg border border-glass-border text-slate-200'
                                }`}>
                                {msg.isLoading ? (
                                    <div className="flex items-center gap-2 py-1">
                                        <Loader2 size={16} className="animate-spin" />
                                        <span className="text-sm font-medium italic opacity-70">{msg.statusMessage || 'Processing context and generating response...'}</span>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {msg.error && (
                                            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300 flex items-center gap-2">
                                                <AlertTriangle size={14} />
                                                {msg.error}
                                            </div>
                                        )}
                                        {msg.content && <MarkdownContent content={msg.content} />}
                                        {msg.role === 'assistant' && (
                                            <div className="space-y-2 pt-2 border-t border-white/10 text-xs text-slate-400">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full border font-semibold ${confidenceBadgeClass(msg.confidence)}`}>
                                                        <BadgeCheck size={12} />
                                                        Confidence {typeof msg.confidence === 'number' ? msg.confidence.toFixed(2) : 'n/a'}
                                                    </span>
                                                    {msg.validationStatus && <span>Validation: {msg.validationStatus}</span>}
                                                    {msg.metadata?.latency_ms != null && <span>Latency: {msg.metadata.latency_ms.toFixed(0)} ms</span>}
                                                    {msg.metadata?.cache_hit && <span className="text-emerald-300">Cache hit</span>}
                                                </div>

                                                {typeof msg.confidence === 'number' && msg.confidence < 0.45 && (
                                                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-200 flex items-center gap-2">
                                                        <AlertTriangle size={14} />
                                                        Low confidence answer
                                                    </div>
                                                )}

                                                {msg.content.toLowerCase().includes('no relevant data found') && (
                                                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-amber-200 flex items-center gap-2">
                                                        <CircleHelp size={14} />
                                                        No relevant information found in documents
                                                    </div>
                                                )}

                                                {(demoMode || (msg.sources && msg.sources.length > 0)) && (
                                                    <div className="pt-2 space-y-3">
                                                        <button
                                                            onClick={() => setExpandedMessage(prev => prev === msg.id ? null : msg.id)}
                                                            className="w-full text-left rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center justify-between text-slate-200"
                                                        >
                                                            <span className="font-semibold">Why this answer?</span>
                                                            {expandedMessage === msg.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                                        </button>

                                                        {expandedMessage === msg.id && (
                                                            <div className="rounded-lg border border-white/10 bg-black/20 p-3 space-y-3">
                                                                <div className="text-[11px] text-slate-400 flex items-center gap-2">
                                                                    <Database size={12} />
                                                                    Retrieved documents: {msg.metadata?.retrieved_documents ?? msg.sources?.length ?? 0}
                                                                </div>

                                                                <div>
                                                                    <div className="font-semibold text-slate-200 mb-2">Sources Used</div>
                                                                    {msg.sources && msg.sources.length > 0 ? (
                                                                        <ul className="space-y-2">
                                                                            {msg.sources.map((source, index) => (
                                                                                <li key={`${source.source}-${source.chunk_id}-${index}`} id={`source-${msg.id}-${index}`} className="rounded-md border border-white/10 bg-white/5 p-2">
                                                                                    <button
                                                                                        type="button"
                                                                                        className="text-blue-300 hover:text-blue-200 font-semibold text-xs"
                                                                                        onClick={() => navigator.clipboard.writeText(`${source.source} | chunk ${source.chunk_id || 'n/a'}`)}
                                                                                        title="Copy source reference"
                                                                                    >
                                                                                        {source.source} • chunk {source.chunk_id || 'n/a'} • page {source.page_number ?? 'n/a'}
                                                                                    </button>
                                                                                    <div className="text-[11px] text-slate-400 mt-1">Similarity score: {(source.score ?? 0).toFixed(2)}</div>
                                                                                    {source.snippet && (
                                                                                        <div className="mt-2 text-[11px] text-slate-300">
                                                                                            <MarkdownContent content={highlightSnippet(source.snippet, msg.content)} />
                                                                                        </div>
                                                                                    )}
                                                                                </li>
                                                                            ))}
                                                                        </ul>
                                                                    ) : (
                                                                        <div className="text-[11px] text-slate-500">No sources available for this response.</div>
                                                                    )}
                                                                </div>

                                                                {showDebug && (
                                                                    <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
                                                                        <div className="font-semibold text-amber-200 text-xs">Debug Context</div>
                                                                        <div className="text-[11px] text-slate-300">Validation Notes: {msg.validation || 'n/a'}</div>
                                                                        <div className="text-[11px] text-slate-300">Raw context:</div>
                                                                        <ul className="space-y-1">
                                                                            {(msg.contextPreview && msg.contextPreview.length > 0) ? msg.contextPreview.map((ctx, idx) => (
                                                                                <li key={`${msg.id}-ctx-${idx}`} className="text-[11px] text-slate-400">{ctx.slice(0, 220)}...</li>
                                                                            )) : <li className="text-[11px] text-slate-500">No context preview available.</li>}
                                                                        </ul>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                                <div className={`mt-2 text-[10px] ${msg.role === 'user' ? 'text-blue-100/80' : 'text-slate-500'}`}>
                                    {formatTime(msg.timestamp)}
                                </div>
                                {msg.role === 'assistant' && !msg.isLoading && (
                                    <div className="absolute -bottom-6 right-0 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2 text-[10px] text-slate-500">
                                        <Info size={10} />
                                        Verified by Validation Agent
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="px-10 pb-8">
                <div className="max-w-4xl mx-auto">
                    <div className="relative group">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-accent-primary to-accent-secondary rounded-2xl blur opacity-20 group-focus-within:opacity-40 transition duration-500" />
                        <div className="relative bg-background-sidebar border border-glass-border rounded-2xl flex items-end p-2 gap-2 shadow-2xl">
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                placeholder={mode === 'chat' ? "Ask about company policies, IT help, or operations..." : "Search for keywords in the knowledge base..."}
                                className="flex-1 bg-transparent border-none focus:ring-0 text-slate-200 placeholder-slate-500 py-3 px-4 resize-none max-h-40 min-h-[52px]"
                                rows={1}
                            />
                            <button
                                onClick={handleSend}
                                disabled={!input.trim() || loading}
                                className="w-11 h-11 bg-accent-primary hover:bg-accent-hover disabled:opacity-50 disabled:hover:bg-accent-primary text-white rounded-xl flex items-center justify-center transition-all duration-200 flex-shrink-0"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
                            </button>
                        </div>
                    </div>
                    {loading && (
                        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-slate-400">
                            <Loader2 size={12} className="animate-spin" />
                            Generating response in real time...
                        </div>
                    )}
                    <p className="mt-4 text-center text-[10px] text-slate-600 font-medium tracking-wide uppercase">
                        Privacy First Architecture &bull; Local Embeddings &bull; Zero Cloud Upload
                    </p>
                </div>
            </div>
        </div>
    );
};
