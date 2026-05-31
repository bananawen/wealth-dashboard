import { useState, useEffect } from 'react';
import { useLoginMutation } from '../store/apiSlice';

export default function DebugPage() {
  const [info, setInfo] = useState('loading...');
  const [login] = useLoginMutation();

  useEffect(() => {
    const token = localStorage.getItem('token');
    setInfo('Token: ' + (token ? token.slice(0, 20) + '...' : 'NONE'));

    login({ username: 'bananawen', password: 'Tzj5Eep2Too9' })
      .unwrap()
      .then(d => {
        setInfo('Login OK, token: ' + d.access_token.slice(0, 20) + '...');
        return fetch('/api/admin/logs?limit=3', {
          headers: { 'Authorization': 'Bearer ' + d.access_token }
        });
      })
      .then(r => r.json())
      .then(d => setInfo('Logs: total=' + d.total + ' len=' + d.logs.length + ' error=' + (d.error || 'none')))
      .catch((e: Error) => setInfo('Error: ' + e.message));
  }, [login]);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] p-8">
      <h1 className="text-2xl font-bold mb-4">DEBUG</h1>
      <pre className="bg-[var(--bg-secondary)] p-4 rounded text-sm font-mono whitespace-pre-wrap">{info}</pre>
      <div className="mt-4">
        <a href="/admin" className="text-blue-400 underline">Back to Admin</a>
      </div>
    </div>
  );
}
