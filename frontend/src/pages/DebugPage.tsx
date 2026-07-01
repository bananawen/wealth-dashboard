import { useEffect, useState } from 'react';

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '='));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export default function DebugPage() {
  const [info, setInfo] = useState('loading...');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const payload = token ? decodeJwtPayload(token) : null;

    if (!token) {
      setInfo('Token: NONE\n請先登入，再使用目前帳號測試管理頁。');
      return;
    }

    const lines = [
      `Token: ${token.slice(0, 20)}...`,
      `User: ${String(payload?.sub ?? 'unknown')}`,
      `Role: ${String(payload?.role ?? 'missing')}`,
      `User ID: ${String(payload?.user_id ?? 'unknown')}`,
    ];

    fetch('/api/admin/logs?limit=3', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        const data = await response.json();
        lines.push(`Admin logs status: ${response.status}`);
        lines.push(`Logs: total=${data.total ?? 'n/a'} len=${data.logs?.length ?? 0} error=${data.error || 'none'}`);
        setInfo(lines.join('\n'));
      })
      .catch((error: Error) => {
        lines.push(`Admin logs error: ${error.message}`);
        setInfo(lines.join('\n'));
      });
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] p-8 text-[var(--text-primary)]">
      <h1 className="mb-4 text-2xl font-bold">DEBUG</h1>
      <pre className="whitespace-pre-wrap rounded bg-[var(--bg-secondary)] p-4 font-mono text-sm">{info}</pre>
      <div className="mt-4">
        <a href="/admin" className="text-blue-400 underline">Back to Admin</a>
      </div>
    </div>
  );
}
