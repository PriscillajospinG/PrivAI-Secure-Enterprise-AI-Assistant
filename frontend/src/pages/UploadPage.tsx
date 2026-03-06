import React, { useState } from 'react';
import { Upload, File, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';
import { aiService } from '../services/api.service';

export const UploadPage: React.FC = () => {
    const [files, setFiles] = useState<File[]>([]);
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(Array.from(e.target.files));
        }
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUpload = async () => {
        if (files.length === 0) return;

        setUploading(true);
        setStatus(null);

        try {
            const data = new DataTransfer();
            files.forEach(file => data.items.add(file));

            const result = await aiService.upload(data.files);
            setStatus({
                type: 'success',
                message: `${result.file_count} documents successfully indexed into the local vector database.`
            });
            setFiles([]);
        } catch (error) {
            setStatus({
                type: 'error',
                message: 'Failed to upload and index documents. Please check backend connectivity.'
            });
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-background/30 px-10 py-10">
            <div className="max-w-4xl mx-auto w-full">
                <header className="mb-10">
                    <h2 className="text-3xl font-display font-bold gradient-text">Knowledge Management</h2>
                    <p className="text-slate-400 mt-2">Upload enterprise documents to expand the assistant's knowledge base.</p>
                </header>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Upload Box */}
                    <div className="space-y-6">
                        <div className="relative group">
                            <input
                                type="file"
                                multiple
                                onChange={handleFileChange}
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                            />
                            <div className="p-10 glass-card bg-accent-primary/5 border-dashed border-2 border-accent-primary/30 group-hover:border-accent-primary/50 flex flex-col items-center justify-center text-center transition-all">
                                <div className="w-16 h-16 rounded-2xl bg-accent-primary/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                    <Upload className="text-accent-primary" size={32} />
                                </div>
                                <h3 className="font-bold text-lg mb-1">Click or drag documents here</h3>
                                <p className="text-sm text-slate-500">Supports PDF, TXT, and Docx files</p>
                                <div className="mt-6 px-4 py-2 bg-accent-primary text-white rounded-lg text-sm font-bold shadow-lg shadow-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity">
                                    Select Files
                                </div>
                            </div>
                        </div>

                        {status && (
                            <div className={`p-4 rounded-xl flex items-start gap-3 border ${status.type === 'success'
                                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                    : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                                }`}>
                                {status.type === 'success' ? <CheckCircle2 size={20} /> : <AlertCircle size={20} />}
                                <p className="text-sm font-medium">{status.message}</p>
                            </div>
                        )}
                    </div>

                    {/* File List */}
                    <div className="glass-card flex flex-col h-[400px]">
                        <div className="p-4 border-b border-glass-border flex justify-between items-center">
                            <h4 className="font-bold">Queue ({files.length} files)</h4>
                            {files.length > 0 && (
                                <button
                                    onClick={() => setFiles([])}
                                    className="text-xs font-bold text-rose-500 hover:text-rose-400"
                                >
                                    Clear All
                                </button>
                            )}
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-2">
                            {files.length === 0 ? (
                                <div className="h-full flex flex-col items-center justify-center text-slate-600 italic text-sm">
                                    <File size={32} className="mb-2 opacity-20" />
                                    No files selected
                                </div>
                            ) : (
                                files.map((file, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-all">
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <File size={18} className="text-slate-400 flex-shrink-0" />
                                            <span className="text-sm text-slate-300 truncate">{file.name}</span>
                                        </div>
                                        <button
                                            onClick={() => removeFile(i)}
                                            className="p-1 hover:bg-white/10 rounded-md text-slate-500 hover:text-rose-500 transition-colors"
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>

                        <div className="p-4 border-t border-glass-border bg-white/5">
                            <button
                                onClick={handleUpload}
                                disabled={files.length === 0 || uploading}
                                className="w-full py-3 bg-accent-primary hover:bg-accent-hover disabled:opacity-50 disabled:grayscale text-white rounded-xl font-bold flex items-center justify-center gap-2 transition-all"
                            >
                                {uploading ? (
                                    <>
                                        <Loader2 size={20} className="animate-spin" />
                                        Indexing Knowledge...
                                    </>
                                ) : (
                                    <>
                                        <CheckCircle2 size={20} />
                                        Process & Index Documents
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
