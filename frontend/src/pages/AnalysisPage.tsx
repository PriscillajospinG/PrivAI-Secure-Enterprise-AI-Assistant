import React, { useState } from 'react';
import {
    FileText,
    ShieldCheck,
    Users,
    Loader2,
    Copy,
    Download,
    Terminal,
    AlertTriangle,
    CheckCircle2,
} from 'lucide-react';
import { aiService, getApiErrorMessage, type QueryResult, type TaskType } from '../services/api.service';
import { MarkdownContent } from '../components/MarkdownContent';

const sectionTitle = (key: string) => key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const normalizeSectionItems = (value: unknown): string[] => {
    if (Array.isArray(value)) {
        const items = value.map((item) => String(item).trim()).filter(Boolean);
        return items.length > 0 ? items : ['Not present in document'];
    }
    if (typeof value === 'string' && value.trim()) {
        return [value.trim()];
    }
    return ['Not present in document'];
};

const StructuredOutput: React.FC<{ result: QueryResult }> = ({ result }) => {
    const structured = result.structured_output;
    if (!structured || typeof structured !== 'object') {
        return (
            <div className="space-y-2">
                <h4 className="font-semibold text-slate-200">Narrative Output</h4>
                <MarkdownContent content={result.response} />
            </div>
        );
    }

    const entries = Object.entries(structured);
    return (
        <div className="space-y-6">
            {entries.map(([key, value]) => (
                <section key={key} className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-2">{sectionTitle(key)}</h4>
                    <ul className="space-y-2">
                        {normalizeSectionItems(value).map((item, index) => (
                            <li key={`${key}-${index}`} className="text-sm text-slate-200 leading-relaxed">• {item}</li>
                        ))}
                    </ul>
                </section>
            ))}
            <section className="rounded-xl border border-white/10 bg-white/5 p-4">
                <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-2">Raw Narrative</h4>
                <MarkdownContent content={result.response} />
            </section>
        </div>
    );
};

export const AnalysisPage: React.FC<{ mode: string }> = ({ mode }) => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<QueryResult | null>(null);
    const [error, setError] = useState('');

    const getPageInfo = () => {
        switch (mode) {
            case 'summarize':
                return {
                    title: 'Document Summarizer',
                    desc: 'Generate grounded summaries from indexed content only.',
                    icon: <FileText className="text-blue-400" size={32} />,
                    placeholder: 'What document or topic should be summarized?',
                    color: 'blue',
                };
            case 'analyze':
                return {
                    title: 'Contract Analyzer',
                    desc: 'Extract explicit clauses and obligations with strict grounding.',
                    icon: <ShieldCheck className="text-emerald-400" size={32} />,
                    placeholder: 'What contract should be analyzed?',
                    color: 'emerald',
                };
            case 'meeting':
                return {
                    title: 'Meeting Intelligence',
                    desc: 'Extract explicit decisions and action items from transcripts.',
                    icon: <Users className="text-purple-400" size={32} />,
                    placeholder: 'What meeting transcript should be analyzed?',
                    color: 'purple',
                };
            default:
                return {
                    title: 'AI Analysis',
                    desc: 'Structured extraction from enterprise documents.',
                    icon: <FileText size={32} />,
                    placeholder: 'Enter query...',
                    color: 'blue',
                };
        }
    };

    const info = getPageInfo();

    const handleRun = async () => {
        if (!query.trim() || loading) return;

        setLoading(true);
        setResult(null);
        setError('');

        try {
            const resp = await aiService.query({
                query,
                task_type: mode as TaskType,
            });
            setResult(resp.result);
        } catch (err) {
            setError(getApiErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    const colorMap = {
        blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', loading: 'border-blue-500' },
        emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', loading: 'border-emerald-500' },
        purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', loading: 'border-purple-500' },
    };

    const colors = colorMap[info.color as keyof typeof colorMap] || colorMap.blue;

    return (
        <div className="h-full bg-background/30 p-10 overflow-y-auto">
            <div className="max-w-6xl mx-auto">
                <header className="mb-10 flex items-start justify-between">
                    <div className="flex gap-6 items-center">
                        <div className={`p-4 rounded-2xl ${colors.bg} border ${colors.border}`}>{info.icon}</div>
                        <div>
                            <h2 className="text-3xl font-display font-bold text-slate-100">{info.title}</h2>
                            <p className="text-slate-400 mt-1">{info.desc}</p>
                        </div>
                    </div>
                    <button className="p-2.5 rounded-xl glass-card transition-colors hover:bg-white/10">
                        <Download size={20} className="text-slate-400" />
                    </button>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    <div className="lg:col-span-4 space-y-6">
                        <div className="glass-card p-6 space-y-6">
                            <div>
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 block">Query</label>
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder={info.placeholder}
                                    className="w-full bg-background-sidebar border border-glass-border rounded-xl py-3 px-4 text-sm focus:ring-1 focus:ring-accent-primary outline-none text-slate-200"
                                />
                            </div>

                            <button
                                onClick={handleRun}
                                disabled={!query.trim() || loading}
                                className="w-full py-4 bg-accent-primary hover:bg-accent-hover disabled:opacity-50 text-white rounded-xl font-bold flex items-center justify-center gap-2"
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : <Terminal size={20} />}
                                Run Pipeline
                            </button>
                        </div>

                        {result && (
                            <div className="glass-card p-4 space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">Validation</span>
                                    {result.approved ? (
                                        <span className="inline-flex items-center gap-1 text-emerald-400 text-xs font-semibold">
                                            <CheckCircle2 size={14} /> Approved
                                        </span>
                                    ) : (
                                        <span className="inline-flex items-center gap-1 text-rose-400 text-xs font-semibold">
                                            <AlertTriangle size={14} /> Needs review
                                        </span>
                                    )}
                                </div>
                                <p className="text-xs text-slate-400">{result.validation}</p>
                                {result.validation_status && (
                                    <p className="text-xs text-slate-300">Status: {result.validation_status}</p>
                                )}
                                <div className="pt-2 border-t border-white/10">
                                    <span className="text-xs text-slate-400">Confidence: </span>
                                    <span className="text-sm font-bold text-slate-200">{result.confidence.toFixed(2)}</span>
                                </div>
                            </div>
                        )}

                        {result && (
                            <div className="glass-card p-4">
                                <div className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">Sources</div>
                                <ul className="space-y-2">
                                    {result.sources.map((source, index) => (
                                        <li key={`${source.source}-${source.chunk_id}-${index}`} className="text-xs text-slate-300">
                                            {source.source} • chunk {source.chunk_id || 'n/a'} • page {source.page_number ?? 'n/a'} • score {(source.score ?? 0).toFixed(2)}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    <div className="lg:col-span-8">
                        {loading ? (
                            <div className="glass-card h-[520px] flex flex-col items-center justify-center text-center p-10 animate-pulse">
                                <div className={`w-16 h-16 rounded-full border-t-2 ${colors.loading} animate-spin mb-6`} />
                                <h4 className="font-bold text-xl mb-2 tracking-tight">Analyzing Document</h4>
                                <p className="text-slate-500 text-sm max-w-xs">Retrieving context, validating grounding, and producing structured output.</p>
                            </div>
                        ) : error ? (
                            <div className="glass-card min-h-[520px] p-8">
                                <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-rose-300 text-sm">{error}</div>
                            </div>
                        ) : result ? (
                            <div className="glass-card min-h-[520px] flex flex-col">
                                <div className="p-4 border-b border-glass-border flex justify-between items-center bg-white/5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Structured Output</span>
                                    <button
                                        onClick={() => navigator.clipboard.writeText(JSON.stringify(result.structured_output ?? result.response, null, 2))}
                                        className="flex items-center gap-2 text-xs font-bold text-accent-primary hover:text-accent-hover"
                                    >
                                        <Copy size={14} /> Copy
                                    </button>
                                </div>
                                <div className="p-6 overflow-y-auto">
                                    <StructuredOutput result={result} />
                                </div>
                            </div>
                        ) : (
                            <div className="glass-card h-[520px] border-dashed flex flex-col items-center justify-center text-center p-10">
                                <h4 className="font-bold text-xl mb-2">No Analysis Yet</h4>
                                <p className="text-slate-500 text-sm max-w-xs">Enter a query and run the pipeline to see structured, source-grounded output.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
