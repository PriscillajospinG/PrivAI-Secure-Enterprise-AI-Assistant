import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 120000,
});

export type TaskType = 'chat' | 'search' | 'summarize' | 'analyze' | 'meeting';

export interface QueryRequest {
    query: string;
    task_type: TaskType;
    top_k?: number;
}

export interface SourceCitation {
    source: string;
    chunk_id: string;
    page_number?: number | null;
    score?: number | null;
    snippet: string;
}

export interface QueryResult {
    query: string;
    task_type: TaskType;
    response: string;
    validation: string;
    validation_status: string;
    approved: boolean;
    confidence: number;
    structured_output?: Record<string, unknown> | null;
    sources: SourceCitation[];
    context_preview: string[];
}

export interface QueryResponse {
    success: true;
    result: QueryResult;
    metadata: {
        attempts?: number;
        effective_top_k?: number;
        validation_attempts?: number;
        retrieved_documents?: number;
        latency_ms?: number;
        cache_hit?: boolean;
    };
}

export interface EvaluationArtifacts {
    confusion_matrix: string;
    response_times: string;
    metrics_bar_chart: string;
    detailed_results: string;
    metrics: string;
}

export interface EvaluationMetrics {
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    exact_match: number;
    token_precision: number;
    token_recall: number;
    token_f1: number;
    response_time_ms_avg: number;
    response_time_ms_p95: number;
    samples: number;
}

export interface EvaluationResponse {
    success?: boolean;
    available?: boolean;
    message?: string;
    metrics?: EvaluationMetrics;
    artifacts?: EvaluationArtifacts;
}

export interface UploadResult {
    uploaded_files: string[];
    indexed_chunks: number;
    skipped_files: string[];
}

export interface UploadResponse {
    success: true;
    result: UploadResult;
    metadata: {
        indexed_files?: string[];
    };
}

export interface HealthResponse {
    status: 'healthy' | 'degraded';
    ollama: {
        available: boolean;
        models: string[];
        llm_model_ready: boolean;
        embedding_model_ready: boolean;
    };
    vector_store: {
        collection: string;
        document_chunks: number;
    };
    environment: string;
}

export function getApiErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        const message = error.response?.data?.error;
        return detail || message || error.message || 'Request failed';
    }
    if (error instanceof Error) {
        return error.message;
    }
    return 'Request failed';
}

interface StreamCallbacks {
    onStatus?: (payload: Record<string, unknown>) => void;
    onToken?: (token: string) => void;
    onDone?: (payload: QueryResponse) => void;
    onError?: (message: string) => void;
}

function parseSseEventBlock(block: string): { event: string; data: string } | null {
    const lines = block.split('\n').map((line) => line.trim()).filter(Boolean);
    if (lines.length === 0) return null;

    let event = 'message';
    const dataLines: string[] = [];

    for (const line of lines) {
        if (line.startsWith('event:')) {
            event = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim());
        }
    }

    return { event, data: dataLines.join('\n') };
}

export const aiService = {
    async query(data: QueryRequest): Promise<QueryResponse> {
        const response = await api.post<QueryResponse>('/query', data);
        return response.data;
    },

    async streamQuery(data: QueryRequest, callbacks: StreamCallbacks = {}): Promise<QueryResponse> {
        const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');
        const response = await fetch(`${baseUrl}/query/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok || !response.body) {
            throw new Error(`Streaming request failed: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });

            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() ?? '';

            for (const block of blocks) {
                const parsed = parseSseEventBlock(block);
                if (!parsed) continue;

                let payload: unknown = parsed.data;
                try {
                    payload = JSON.parse(parsed.data);
                } catch {
                    payload = parsed.data;
                }

                if (parsed.event === 'status') {
                    callbacks.onStatus?.((payload as Record<string, unknown>) ?? {});
                    continue;
                }

                if (parsed.event === 'token') {
                    const token = (payload as { token?: string })?.token ?? '';
                    callbacks.onToken?.(token);
                    continue;
                }

                if (parsed.event === 'done') {
                    const result = payload as QueryResponse;
                    callbacks.onDone?.(result);
                    return result;
                }

                if (parsed.event === 'error') {
                    const message = (payload as { detail?: string })?.detail ?? 'Streaming failed';
                    callbacks.onError?.(message);
                    throw new Error(message);
                }
            }
        }

        throw new Error('Stream closed before completion');
    },

    async upload(files: FileList): Promise<UploadResponse> {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        const response = await api.post<UploadResponse>('/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    async healthCheck(): Promise<HealthResponse> {
        const response = await api.get<HealthResponse>('/health');
        return response.data;
    },

    async runEvaluation(): Promise<EvaluationResponse> {
        const response = await api.post<EvaluationResponse>('/evaluation/run');
        return response.data;
    },

    async getLatestEvaluation(): Promise<EvaluationResponse> {
        const response = await api.get<EvaluationResponse>('/evaluation/latest');
        return response.data;
    },
};

export default api;
