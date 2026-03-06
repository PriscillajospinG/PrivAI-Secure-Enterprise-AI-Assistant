import React from 'react';

const App: React.FC = () => {
  return (
    <div style={{
      backgroundColor: '#020617',
      color: 'white',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'sans-serif'
    }}>
      <h1 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '1rem' }}>PrivAI Modern UI</h1>
      <p style={{ color: '#94a3b8' }}>If you see this, React rendering is working correctly.</p>
      <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #334155', borderRadius: '0.5rem' }}>
        Status: Rendering Proof of Concept
      </div>
    </div>
  );
};

export default App;
