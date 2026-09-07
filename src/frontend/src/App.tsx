import { useState } from 'react';
import Dashboard from './components/Dashboard';
import FloatingChat from './components/FloatingChat';

function App() {
  const [showLogModal, setShowLogModal] = useState(false);
  const [logText, setLogText] = useState('');
  const [logStatus, setLogStatus] = useState('');

  const submitLog = async () => {
    setLogStatus('Submitting...');
    try {
      const formData = new FormData();
      formData.append('text', logText);
      const res = await fetch('/api/intake', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        setLogStatus('Logged successfully!');
        setTimeout(() => {
          setShowLogModal(false);
          setLogStatus('');
          setLogText('');
        }, 1000);
      } else {
        setLogStatus('Failed to log');
      }
    } catch (e) {
      setLogStatus('Error reaching server');
    }
  };

  const handleTakeoutUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      alert('Uploading and parsing Takeout zip... this may take a moment.');
      const res = await fetch('/api/import/takeout', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        alert('Takeout data imported successfully!');
      } else {
        alert('Failed to import Takeout data.');
      }
    } catch (err) {
      alert('Error uploading file.');
    }
  };

  const handleScaleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      alert('Uploading and parsing FITINDEX csv...');
      const res = await fetch('/api/import/fitindex/csv', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        alert('Scale data imported successfully!');
      } else {
        alert('Failed to import scale data.');
      }
    } catch (err) {
      alert('Error uploading file.');
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="flex-center" style={{ marginBottom: '3rem', gap: '1rem' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: 'linear-gradient(135deg, var(--accent-secondary), var(--accent-primary))', boxShadow: 'var(--glow-primary)' }}></div>
          <h1 className="heading-2" style={{ margin: 0 }}>Aegis</h1>
        </div>
        
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <a href="#" className="btn" style={{ background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)' }}>Overview</a>
          <button onClick={() => alert('Analytics dashboard coming soon!')} className="btn" style={{ background: 'transparent', border: '1px solid transparent', textAlign: 'left' }}>Analytics</button>
          <button onClick={() => alert('Settings coming soon!')} className="btn" style={{ background: 'transparent', border: '1px solid transparent', textAlign: 'left' }}>Settings</button>
        </nav>
      </aside>
      
      <main className="main-content">
        <header className="flex-between" style={{ marginBottom: '2rem' }}>
          <div>
            <h1 className="heading-1">Health Overview</h1>
            <p className="text-subtle">Welcome back. Your vitals look stable today.</p>
          </div>
          <div className="flex-center" style={{ gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-primary)', padding: '0.25rem 0.5rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <span className="text-subtle" style={{ fontSize: '0.875rem' }}>User:</span>
              <select 
                value={localStorage.getItem('user_id') || 'test_user_1'}
                onChange={(e) => {
                  localStorage.setItem('user_id', e.target.value);
                  window.location.reload();
                }}
                style={{ background: 'transparent', color: 'var(--text-primary)', border: 'none', outline: 'none', cursor: 'pointer', fontSize: '0.875rem' }}
              >
                <option value="test_user_1">Test User 1</option>
                <option value="test_user_2">Test User 2</option>
                <option value="prod_user">Production User</option>
              </select>
            </div>
            <span className="glass-panel" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
              <span style={{ color: 'var(--accent-success)', marginRight: '0.5rem' }}>●</span>
              Live Sync
            </span>
            <button className="btn" onClick={() => window.location.href = 'http://localhost:8000/api/import/fitbit/auth'}>Connect Fitbit</button>
            <label className="btn" style={{ cursor: 'pointer' }}>
              Scale Data (.csv)
              <input type="file" accept=".csv" style={{ display: 'none' }} onChange={handleScaleCsvUpload} />
            </label>
            <label className="btn" style={{ cursor: 'pointer' }}>
              Takeout (.zip)
              <input type="file" accept=".zip" style={{ display: 'none' }} onChange={handleTakeoutUpload} />
            </label>
            <button className="btn btn-primary" onClick={() => setShowLogModal(true)}>Add Log</button>
          </div>
        </header>
        
        <Dashboard />
      </main>
      
      <FloatingChat />

      {showLogModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ padding: '2rem', width: '400px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h2 className="heading-2" style={{ marginBottom: 0 }}>Add Health Log</h2>
            <p className="text-subtle">Enter your weight, body fat, or any notes. Aegis will parse it automatically.</p>
            <textarea 
              style={{ width: '100%', height: '100px', padding: '0.75rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', borderRadius: '8px' }}
              placeholder="e.g. Weighted 182.5 lbs today with 18% body fat"
              value={logText}
              onChange={e => setLogText(e.target.value)}
            />
            <div className="flex-between">
              <span style={{ fontSize: '0.875rem', color: 'var(--accent-success)' }}>{logStatus}</span>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn" onClick={() => setShowLogModal(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={submitLog}>Submit</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
