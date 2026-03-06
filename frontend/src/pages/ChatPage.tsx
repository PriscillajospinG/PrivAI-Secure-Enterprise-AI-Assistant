import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, Info } from 'lucide-react';
import { aiService } from '../services/api.service';
import type { QueryResponse } from '../services/api.service';

interface Message {
    id: string;
    role: 'assistant' | 'user';
    content: string;
    isLoading?: boolean;
}

export const ChatPage: React.FC<{ mode: string }> = ({ mode }) => {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: `Hello! I am your Secure AI Assistant. I operate entirely locally. How can I help you explore your enterprise knowledge base today?`
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        // Add placeholder for assistant response
        const assistantMsgId = (Date.now() + 1).toString();
        setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '', isLoading: true }]);

        try {
            const result = await aiService.query({
                query: input,
                task_type: mode
            });

            setMessages(prev => prev.map(msg =>
                msg.id === assistantMsgId
                    ? { ...msg, content: result.response, isLoading: false }
                    : msg
            ));
        } catch (error) {
            setMessages(prev => prev.map(msg =>
                msg.id === assistantMsgId
                    ? { ...msg, content: "Sorry, I encountered an error connecting to the local LLM. Please make sure Ollama is running.", isLoading: false }
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
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-[10px] font-bold text-blue-400 uppercase tracking-wider">
                    <Bot size={14} />
                    Llama 3 Active
                </div>
            </header>

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto px-10 py-8 space-y-6">
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
                                        <span className="text-sm font-medium italic opacity-70">Processing context and generating response...</span>
                                    </div>
                                ) : (
                                    msg.content
                                )}
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
                    <p className="mt-4 text-center text-[10px] text-slate-600 font-medium tracking-wide uppercase">
                        Privacy First Architecture &bull; Local Embeddings &bull; Zero Cloud Upload
                    </p>
                </div>
            </div>
        </div>
    );
};
