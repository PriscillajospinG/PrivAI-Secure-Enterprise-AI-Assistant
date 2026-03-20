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
    };
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

export const aiService = {
    async query(data: QueryRequest): Promise<QueryResponse> {
        const response = await api.post<QueryResponse>('/query', data);
        return response.data;
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
};

export default api;
