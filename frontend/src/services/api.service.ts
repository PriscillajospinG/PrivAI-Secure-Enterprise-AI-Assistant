import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface QueryRequest {
    query: string;
    task_type: string;
}

export interface QueryResponse {
    query: string;
    response: string;
    context: string[];
    validation: string;
    approved: boolean;
    task_type: string;
}

export interface UploadResponse {
    message: string;
    file_count: number;
}

export const aiService = {
    query: async (data: QueryRequest): Promise<QueryResponse> => {
        const response = await api.post<QueryResponse>('/query', data);
        return response.data;
    },

    upload: async (files: FileList): Promise<UploadResponse> => {
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

    healthCheck: async () => {
        const response = await api.get('/health');
        return response.data;
    }
};

export default api;
