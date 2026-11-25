import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

function App() {
  const [health, setHealth] = useState('Đang kiểm tra kết nối…');
  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/health', { signal: controller.signal })
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(data => setHealth(data.status === 'ok' ? 'Backend sẵn sàng' : 'Backend chưa sẵn sàng'))
      .catch(e => { if (e.name !== 'AbortError') setHealth('Chưa kết nối được backend'); });
    return () => controller.abort();
  }, []);
  return <main><p className="eyebrow">API TESTING TOOL</p><h1>Không gian kiểm thử API</h1>
    <p>Khung hệ thống đã sẵn sàng để phát triển các lượt kiểm thử.</p>
    <section aria-label="Kết nối"><h2>Trạng thái hệ thống</h2><p role="status">{health}</p></section>
    <section><h2>Bước tiếp theo</h2><p>Quản lý đặc tả OpenAPI và chạy kiểm thử sẽ được bổ sung trong các mốc tiếp theo.</p></section>
  </main>;
}
createRoot(document.getElementById('root')).render(<App />);
