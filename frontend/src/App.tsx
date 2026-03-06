import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatPage } from './pages/ChatPage';
import { UploadPage } from './pages/UploadPage';
import { AnalysisPage } from './pages/AnalysisPage';

const App: React.FC = () => {
  const [activeMode, setActiveMode] = useState('chat');

  const renderContent = () => {
    switch (activeMode) {
      case 'chat':
      case 'search':
        return <ChatPage mode={activeMode} />;
      case 'upload':
        return <UploadPage />;
      case 'summarize':
      case 'analyze':
      case 'meeting':
        return <AnalysisPage mode={activeMode} />;
      default:
        return <ChatPage mode="chat" />;
    }
  };

  return (
    <div className="flex h-screen bg-[#020617] overflow-hidden">
      <Sidebar activeMode={activeMode} onModeChange={setActiveMode} />
      <main className="flex-1 overflow-hidden relative">
        {/* Background Decorative Element */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-500/5 rounded-full blur-[100px] -mr-64 -mt-64" />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-purple-500/5 rounded-full blur-[80px] -ml-32 -mb-32" />

        <div className="relative h-full">
          {renderContent()}
        </div>
      </main>
    </div>
  );
};

export default App;
