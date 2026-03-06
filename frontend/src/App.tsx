import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatPage } from './pages/ChatPage';

const App: React.FC = () => {
  const [activeMode, setActiveMode] = useState('chat');

  return (
    <div className="flex h-screen bg-[#020617] overflow-hidden text-white">
      <Sidebar activeMode={activeMode} onModeChange={setActiveMode} />
      <main className="flex-1 overflow-hidden relative">
        <ChatPage mode={activeMode} />
      </main>
    </div>
  );
};

export default App;
