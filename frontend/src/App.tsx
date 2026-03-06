import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';

const App: React.FC = () => {
  const [activeMode, setActiveMode] = useState('chat');

  return (
    <div className="flex h-screen bg-[#020617] overflow-hidden text-white">
      <Sidebar activeMode={activeMode} onModeChange={setActiveMode} />
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Sidebar Test</h1>
          <p className="text-slate-400">Current Mode: {activeMode}</p>
        </div>
      </main>
    </div>
  );
};

export default App;
