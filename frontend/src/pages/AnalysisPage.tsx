import React, { useState } from 'react';
import {
    FileText,
    ShieldCheck,
    Users,
    Loader2,
    ChevronRight,
    Copy,
    Download,
    Terminal
} from 'lucide-react';
import { aiService } from '../services/api.service';

export const AnalysisPage: React.FC<{ mode: string }> = ({ mode }) => {
    const [query, setQuery] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<string | null>(null);

    const getPageInfo = () => {
        switch (mode) {
            case 'summarize':
                return {
                    title: 'Document Summarizer',
                    desc: 'Generate concise executive summaries and key highlights.',
                    icon: <FileText className="text-blue-400" size={32} />,
                    placeholder: 'Which document should I summarize? (e.g. HR Policy)',
                    color: 'blue'
                };
            case 'analyze':
                return {
                    title: 'Contract Analyzer',
                    desc: 'Extract risks, obligations, and key legal clauses.',
                    icon: <ShieldCheck className="text-emerald-400" size={32} />,
                    placeholder: 'Search for a particular contract to analyze...',
                    color: 'emerald'
                };
            case 'meeting':
                return {
                    title: 'Meeting Intelligence',
                    desc: 'Extract action items, decisions, and tasks from transcripts.',
                    icon: <Users className="text-purple-400" size={32} />,
                    placeholder: 'Analyze which meeting transcript?',
                    color: 'purple'
                };
            default:
                return {
                    title: 'AI Analysis',
                    desc: 'Extract intelligence from your data.',
                    icon: <FileText size={32} />,
                    placeholder: 'Enter query...',
                    color: 'blue'
                };
        }
    };

    const info = getPageInfo();

    const handleRun = async () => {
        if (!query.trim() || loading) return;

        setLoading(true);
        setResult(null);

        try {
            const resp = await aiService.query({
                query: query,
                task_type: mode
            });
            setResult(resp.response);
        } catch (error) {
            setResult("Error: Failed to perform analysis. Ensure the document is in the knowledge base.");
        } finally {
            setLoading(false);
        }
    };

    const colorMap = {
        blue: {
            bg: 'bg-blue-500/10',
            border: 'border-blue-500/20',
            loading: 'border-blue-500'
        },
        emerald: {
            bg: 'bg-emerald-500/10',
            border: 'border-emerald-500/20',
            loading: 'border-emerald-500'
        },
        purple: {
            bg: 'bg-purple-500/10',
            border: 'border-purple-500/20',
            loading: 'border-purple-500'
        }
    };

    const colors = colorMap[info.color as keyof typeof colorMap] || colorMap.blue;

    return (
        <div className="h-full bg-background/30 p-10 overflow-y-auto">
            <div className="max-w-5xl mx-auto">
                <header className="mb-10 flex items-start justify-between">
                    <div className="flex gap-6 items-center">
                        <div className={`p-4 rounded-2xl ${colors.bg} border ${colors.border}`}>
                            {info.icon}
                        </div>
                        <div>
                            <h2 className="text-3xl font-display font-bold text-slate-100">{info.title}</h2>
                            <p className="text-slate-400 mt-1">{info.desc}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="p-2.5 rounded-xl glass-card transition-colors hover:bg-white/10">
                            <Download size={20} className="text-slate-400" />
                        </button>
                        <button className="p-2.5 rounded-xl glass-card transition-colors hover:bg-white/10">
                            <Settings size={20} className="text-slate-400" />
                        </button>
                    </div>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    {/* Controls */}
                    <div className="lg:col-span-4 space-y-6">
                        <div className="glass-card p-6 space-y-6">
                            <div>
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 block">Target Document</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        value={query}
                                        onChange={(e) => setQuery(e.target.value)}
                                        placeholder={info.placeholder}
                                        className="w-full bg-background-sidebar border border-glass-border rounded-xl py-3 px-4 text-sm focus:ring-1 focus:ring-accent-primary outline-none text-slate-200"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4 pt-2">
                                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Agent Options</div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Human Approval Step</span>
                                    <div className="w-10 h-5 bg-accent-primary rounded-full relative"><div className="absolute right-1 top-1 w-3 h-3 bg-white rounded-full" /></div>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-slate-400">Strict Context Masking</span>
                                    <div className="w-10 h-5 bg-white/10 rounded-full relative"><div className="absolute left-1 top-1 w-3 h-3 bg-slate-500 rounded-full" /></div>
                                </div>
                            </div>

                            <button
                                onClick={handleRun}
                                disabled={!query.trim() || loading}
                                className={`w-full py-4 mt-6 bg-accent-primary hover:bg-accent-hover disabled:opacity-50 text-white rounded-xl font-bold flex items-center justify-center gap-2 shadow-xl shadow-blue-500/10 transition-all`}
                            >
                                {loading ? <Loader2 className="animate-spin" size={20} /> : <Terminal size={20} />}
                                Run AI Pipeline
                            </button>
                        </div>

                        <div className="p-4 rounded-xl border border-blue-500/10 bg-blue-500/5 text-blue-400/80 text-[11px] leading-relaxed flex gap-3">
                            <Info size={16} className="flex-shrink-0 mt-0.5" />
                            <span>This tool uses local embeddings to locate the document and runs a specialized multi-agent graph to perform the extraction.</span>
                        </div>
                    </div>

                    {/* Results Area */}
                    <div className="lg:col-span-8">
                        {loading ? (
                            <div className="glass-card h-[500px] flex flex-col items-center justify-center text-center p-10 animate-pulse">
                                <div className={`w-16 h-16 rounded-full border-t-2 ${colors.loading} animate-spin mb-6`} />
                                <h4 className="font-bold text-xl mb-2 tracking-tight">AI Agents are Working</h4>
                                <p className="text-slate-500 text-sm max-w-xs">Connecting chunks, parsing data, and generating high-accuracy results locally.</p>
                            </div>
                        ) : result ? (
                            <div className="glass-card min-h-[500px] flex flex-col">
                                <div className="p-4 border-b border-glass-border flex justify-between items-center bg-white/5">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI Output Generation</span>
                                    <button
                                        onClick={() => navigator.clipboard.writeText(result)}
                                        className="flex items-center gap-2 text-xs font-bold text-accent-primary hover:text-accent-hover"
                                    >
                                        <Copy size={14} />
                                        Copy Result
                                    </button>
                                </div>
                                <div className="p-8 prose prose-invert max-w-none whitespace-pre-wrap font-sans text-slate-300 leading-relaxed overflow-y-auto">
                                    {result}
                                </div>
                            </div>
                        ) : (
                            <div className="glass-card h-[500px] border-dashed flex flex-col items-center justify-center text-center p-10">
                                <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-6">
                                    {info.icon}
                                </div>
                                <h4 className="font-bold text-xl mb-2">No Analysis Selected</h4>
                                <p className="text-slate-500 text-sm max-w-xs">Enter a document name or query in the sidebar to begin the AI-powered extraction process.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

const Settings = ({ size, className }: { size: number, className: string }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" />
    </svg>
);

const Info = ({ size, className }: { size: number, className: string }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
);
