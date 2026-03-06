import React from 'react';
import {
    MessageSquare,
    FileUp,
    FileText,
    ShieldCheck,
    Users,
    Search,
    Settings,
    Shield
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface SidebarItemProps {
    icon: React.ReactNode;
    label: string;
    active?: boolean;
    onClick: () => void;
}

const SidebarItem = ({ icon, label, active, onClick }: SidebarItemProps) => (
    <button
        onClick={onClick}
        className={cn(
            "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group",
            active
                ? "bg-accent-primary text-white shadow-lg shadow-blue-500/20"
                : "text-slate-400 hover:bg-white/5 hover:text-white"
        )}
    >
        <span className={cn(
            "transition-transform duration-200",
            !active && "group-hover:scale-110"
        )}>
            {icon}
        </span>
        <span className="font-medium text-sm">{label}</span>
    </button>
);

interface SidebarProps {
    activeMode: string;
    onModeChange: (mode: string) => void;
}

export const Sidebar = ({ activeMode, onModeChange }: SidebarProps) => {
    return (
        <aside className="w-72 bg-background-sidebar border-r border-glass-border flex flex-col p-6 h-screen">
            <div className="flex items-center gap-3 mb-10 px-2">
                <div className="w-10 h-10 bg-gradient-to-br from-accent-primary to-accent-secondary rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                    <Shield className="text-white w-6 h-6" />
                </div>
                <div>
                    <h1 className="font-display font-bold text-xl tracking-tight">PrivAI</h1>
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Secure Intel</p>
                </div>
            </div>

            <nav className="flex-1 space-y-2">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4 px-4">Core Tools</div>
                <SidebarItem
                    icon={<MessageSquare size={20} />}
                    label="AI Chat (RAG)"
                    active={activeMode === 'chat'}
                    onClick={() => onModeChange('chat')}
                />
                <SidebarItem
                    icon={<Search size={20} />}
                    label="Knowledge Search"
                    active={activeMode === 'search'}
                    onClick={() => onModeChange('search')}
                />

                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-8 mb-4 px-4">Analysis</div>
                <SidebarItem
                    icon={<FileText size={20} />}
                    label="Summarizer"
                    active={activeMode === 'summarize'}
                    onClick={() => onModeChange('summarize')}
                />
                <SidebarItem
                    icon={<ShieldCheck size={20} />}
                    label="Contract Analyzer"
                    active={activeMode === 'analyze'}
                    onClick={() => onModeChange('analyze')}
                />
                <SidebarItem
                    icon={<Users size={20} />}
                    label="Meeting Intel"
                    active={activeMode === 'meeting'}
                    onClick={() => onModeChange('meeting')}
                />

                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-8 mb-4 px-4">System</div>
                <SidebarItem
                    icon={<FileUp size={20} />}
                    label="Document Manager"
                    active={activeMode === 'upload'}
                    onClick={() => onModeChange('upload')}
                />
            </nav>

            <div className="mt-auto pt-6 border-t border-glass-border">
                <SidebarItem
                    icon={<Settings size={20} />}
                    label="Settings"
                    onClick={() => { }}
                />
                <div className="mt-4 px-4 py-3 glass-card bg-blue-500/5 border-blue-500/10 flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-sm shadow-emerald-500/50" />
                    <span className="text-[11px] font-medium text-slate-400">Local LLM: Active</span>
                </div>
            </div>
        </aside>
    );
};
