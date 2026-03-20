import React, { useState } from 'react';
import { Loader2, Search, FileText } from 'lucide-react';
import { aiService, getApiErrorMessage } from '../services/api.service';
import { MarkdownContent } from '../components/MarkdownContent';

export const SearchPage: React.FC = () => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [answer, setAnswer] = useState('');
    const [sources, setSources] = useState<Array<{ source: string; snippet: string }>>([]);
    const [confidence, setConfidence] = useState<number | null>(null);
    const [validation, setValidation] = useState('');
    const [validationStatus, setValidationStatus] = useState('');
    const [error, setError] = useState('');

    const runSearch = async () => {
        if (!query.trim() || loading) {
            return;
        }

        setLoading(true);
        setError('');
        try {
            const response = await aiService.query({
                query,
                task_type: 'search',
                top_k: 6,
            });
            setAnswer(response.result.response);
            setConfidence(response.result.confidence);
            setValidation(response.result.validation);
            setValidationStatus(response.result.validation_status);
            setSources(
                response.result.sources.map((source) => ({
                    source: `${source.source} (chunk ${source.chunk_id || 'n/a'}, page ${source.page_number ?? 'n/a'}, score ${(source.score ?? 0).toFixed(2)})`,
                    snippet: source.snippet,
                }))
            );
        } catch (err) {
            setAnswer('');
            setSources([]);
            setConfidence(null);
            setValidation('');
            setValidationStatus('');
            setError(getApiErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-full overflow-y-auto p-10 bg-background/30">
            <div className="max-w-5xl mx-auto space-y-8">
                <header>
                    <h2 className="text-3xl font-display font-bold">Knowledge Search</h2>
                    <p className="text-slate-400 mt-1">Search across indexed enterprise content with source citations.</p>
                </header>

                <div className="glass-card p-4 md:p-6 space-y-4">
                    <div className="flex flex-col md:flex-row gap-3">
                        <input
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder="Search enterprise knowledge (for example: leave policy)"
                            className="flex-1 bg-background-sidebar border border-glass-border rounded-xl py-3 px-4 text-sm focus:ring-1 focus:ring-accent-primary outline-none text-slate-200"
                        />
                        <button
                            onClick={runSearch}
                            disabled={!query.trim() || loading}
                            className="px-5 py-3 bg-accent-primary hover:bg-accent-hover disabled:opacity-50 rounded-xl text-white font-semibold flex items-center justify-center gap-2"
                        >
                            {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
                            Search
                        </button>
                    </div>

                    {error && (
                        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
                            {error}
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <section className="lg:col-span-2 glass-card min-h-[320px] p-6">
                        <h3 className="text-sm uppercase tracking-widest text-slate-500 font-bold mb-3">Result</h3>
                        {loading ? (
                            <div className="flex items-center gap-2 text-slate-400">
                                <Loader2 size={16} className="animate-spin" />
                                Searching indexed documents...
                            </div>
                        ) : answer ? (
                            <div className="space-y-3">
                                <MarkdownContent content={answer} />
                                <div className="text-xs text-slate-400">
                                    Confidence: <span className="font-semibold text-slate-200">{(confidence ?? 0).toFixed(2)}</span>
                                </div>
                                {validationStatus && <p className="text-xs text-slate-300">Validation: {validationStatus}</p>}
                                {validation && <p className="text-xs text-slate-500">Validator Notes: {validation}</p>}
                            </div>
                        ) : (
                            <p className="text-slate-500">Run a search to see context-grounded results.</p>
                        )}
                    </section>

                    <aside className="glass-card min-h-[320px] p-6">
                        <h3 className="text-sm uppercase tracking-widest text-slate-500 font-bold mb-3">Sources</h3>
                        {sources.length === 0 ? (
                            <p className="text-slate-500">No sources yet.</p>
                        ) : (
                            <ul className="space-y-3">
                                {sources.map((source, index) => (
                                    <li key={`${source.source}-${index}`} className="rounded-lg border border-white/10 p-3 bg-white/5">
                                        <div className="flex items-center gap-2 text-xs text-blue-300 font-semibold mb-1">
                                            <FileText size={13} />
                                            {source.source}
                                        </div>
                                        <p className="text-xs text-slate-400 line-clamp-4">{source.snippet}</p>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </aside>
                </div>
            </div>
        </div>
    );
};
