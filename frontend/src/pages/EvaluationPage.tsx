import React, { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, Gauge, Loader2, PlayCircle, RefreshCw, ShieldCheck, Timer } from 'lucide-react';
import { aiService, getApiErrorMessage, type EvaluationArtifacts, type EvaluationMetrics } from '../services/api.service';

export const EvaluationPage: React.FC = () => {
    const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
    const [artifacts, setArtifacts] = useState<EvaluationArtifacts | null>(null);
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState('');

    const apiBase = useMemo(() => (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, ''), []);

    const toAssetUrl = (path?: string) => {
        if (!path) return '';
        if (path.startsWith('http://') || path.startsWith('https://')) return path;
        return `${apiBase}${path}`;
    };

    const loadLatest = async () => {
        setRefreshing(true);
        setError('');
        try {
            const response = await aiService.getLatestEvaluation();
            if (response.available && response.metrics && response.artifacts) {
                setMetrics(response.metrics);
                setArtifacts(response.artifacts);
            }
        } catch (err) {
            setError(getApiErrorMessage(err));
        } finally {
            setRefreshing(false);
        }
    };

    useEffect(() => {
        loadLatest();
    }, []);

    const runEvaluation = async () => {
        setLoading(true);
        setError('');
        try {
            const response = await aiService.runEvaluation();
            if (response.metrics && response.artifacts) {
                setMetrics(response.metrics);
                setArtifacts(response.artifacts);
            }
        } catch (err) {
            setError(getApiErrorMessage(err));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="h-full overflow-y-auto p-10 bg-background/30">
            <div className="max-w-6xl mx-auto space-y-8">
                <header className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-3xl font-display font-bold">Evaluation Dashboard</h2>
                        <p className="text-slate-400 mt-1">Track quality, grounding performance, and response latency for demo readiness.</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={loadLatest}
                            disabled={refreshing || loading}
                            className="px-4 py-2 rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 text-slate-200 text-sm font-semibold flex items-center gap-2"
                        >
                            {refreshing ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                            Refresh
                        </button>
                        <button
                            onClick={runEvaluation}
                            disabled={loading}
                            className="px-5 py-2.5 rounded-xl bg-accent-primary hover:bg-accent-hover text-white text-sm font-semibold flex items-center gap-2"
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
                            Run Evaluation
                        </button>
                    </div>
                </header>

                {error && (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-300 text-sm">
                        {error}
                    </div>
                )}

                <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                    <MetricCard title="Accuracy" icon={<Gauge size={16} />} value={metrics?.accuracy} />
                    <MetricCard title="Precision" icon={<ShieldCheck size={16} />} value={metrics?.precision} />
                    <MetricCard title="Recall" icon={<Activity size={16} />} value={metrics?.recall} />
                    <MetricCard title="F1 Score" icon={<BarChart3 size={16} />} value={metrics?.f1_score} />
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <InfoCard title="Samples" value={metrics?.samples?.toString() ?? 'n/a'} />
                    <InfoCard title="Avg Response Time" value={metrics?.response_time_ms_avg != null ? `${metrics.response_time_ms_avg} ms` : 'n/a'} icon={<Timer size={16} />} />
                    <InfoCard title="P95 Response Time" value={metrics?.response_time_ms_p95 != null ? `${metrics.response_time_ms_p95} ms` : 'n/a'} icon={<Timer size={16} />} />
                </section>

                <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <ChartPanel title="Confusion Matrix" src={toAssetUrl(artifacts?.confusion_matrix)} />
                    <ChartPanel title="Response Time Graph" src={toAssetUrl(artifacts?.response_times)} />
                </section>
            </div>
        </div>
    );
};

const MetricCard: React.FC<{ title: string; value?: number; icon: React.ReactNode }> = ({ title, value, icon }) => (
    <div className="glass-card p-5">
        <div className="text-slate-400 text-xs uppercase tracking-widest font-semibold flex items-center gap-2">{icon}{title}</div>
        <div className="mt-3 text-3xl font-bold text-slate-100">{value != null ? value.toFixed(3) : 'n/a'}</div>
    </div>
);

const InfoCard: React.FC<{ title: string; value: string; icon?: React.ReactNode }> = ({ title, value, icon }) => (
    <div className="glass-card p-4 flex items-center justify-between">
        <div className="text-slate-400 text-xs uppercase tracking-widest font-semibold">{title}</div>
        <div className="flex items-center gap-2 text-slate-100 font-semibold">
            {icon}
            {value}
        </div>
    </div>
);

const ChartPanel: React.FC<{ title: string; src: string }> = ({ title, src }) => (
    <div className="glass-card p-4">
        <div className="text-sm font-semibold text-slate-200 mb-3">{title}</div>
        {src ? (
            <img src={src} alt={title} className="w-full rounded-lg border border-white/10" />
        ) : (
            <div className="h-64 rounded-lg border border-dashed border-white/20 flex items-center justify-center text-slate-500 text-sm">
                Run evaluation to generate this chart.
            </div>
        )}
    </div>
);
