import React, { useEffect, useState, useRef, useMemo } from 'react';

function Sparkline({ symbol }) {
  const [points, setPoints] = useState([]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const res = await fetch(`/api/ohlc?symbol=${symbol}&days=30`);
        if (!res.ok) return;
        const data = await res.json();
        const closes = (data.rows || []).map(r => r.close).filter(v => v != null);
        if (mounted) setPoints(closes);
      } catch (e) {
        // ignore
      }
    }
    load();
    return () => { mounted = false };
  }, [symbol]);

  const width = 80, height = 24;
  if (!points || points.length === 0) return <svg width={width} height={height} />;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const scaleX = (i) => (i / (points.length - 1)) * (width - 2) + 1;
  const scaleY = (v) => height - 2 - ((v - min) / (max - min || 1)) * (height - 4);
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(p)}`).join(' ');
  return (
    <svg width={width} height={height} style={{verticalAlign:'middle'}}>
      <path d={path} stroke="#1f77b4" strokeWidth="1" fill="none" strokeLinecap="round" />
    </svg>
  );
}

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(20);
  const [selected, setSelected] = useState(null);
  const chartRef = useRef(null);
  const [watchlistLocal, setWatchlistLocal] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tb_watchlist') || '[]'); } catch { return []; }
  });
  const [watchlistServer, setWatchlistServer] = useState([]);
  const [positions, setPositions] = useState([]);
  const [watchInput, setWatchInput] = useState('');
  const [filterText, setFilterText] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [sortBy, setSortBy] = useState('score');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { fetchWatchlist(); fetchPositions(); }, []);

  async function fetchData() {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`/api/screen?limit=${limit}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      setResults(data.results || []);
      if (!data.results || data.results.length === 0) setError('No candidates found.');
    } catch (e) {
      console.error(e); setError(e.message || String(e));
    } finally { setLoading(false); }
  }

  async function handleManualUpdate() {
    try {
      await fetch('/api/run_update', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({limit: limit}) });
      alert('Update started in background');
    } catch (e) { alert('Failed to start update'); }
  }

  async function fetchWatchlist() {
    try {
      const res = await fetch('/api/watchlist');
      if (!res.ok) return;
      const data = await res.json();
      setWatchlistServer(data.items || []);
    } catch (e) { console.error('watchlist load', e); }
  }

  async function addWatch(symbol) {
    try {
      const res = await fetch('/api/watchlist', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({symbol}) });
      if (!res.ok) throw new Error('failed');
      await fetchWatchlist();
    } catch(e) { console.error(e); }
  }

  async function removeWatch(id) {
    try {
      const res = await fetch(`/api/watchlist/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('failed');
      await fetchWatchlist();
    } catch(e){ console.error(e); }
  }

  async function fetchPositions(){
    try{
      const res = await fetch('/api/positions');
      if (!res.ok) return;
      const data = await res.json();
      setPositions(data.items || []);
    }catch(e){ console.error('positions', e); }
  }

  async function closePosition(pid){
    try{
      const res = await fetch(`/api/positions/${pid}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('failed');
      await fetchPositions();
    }catch(e){ console.error(e); }
  }

  async function handleSymbolClick(sym) {
    setSelected(sym);
    try {
      const res = await fetch(`/api/ohlc?symbol=${sym}&days=365`);
      if (!res.ok) {
        const text = await res.text();
        alert('Failed to load chart: ' + res.status + ' ' + text);
        return;
      }
      const data = await res.json();
      const dates = data.rows.map(r => r.date);
      if (!dates || dates.length === 0) {
        alert('No chart data available for ' + sym);
        return;
      }
      const trace = {
        x: dates,
        open: data.rows.map(r => r.open),
        high: data.rows.map(r => r.high),
        low: data.rows.map(r => r.low),
        close: data.rows.map(r => r.close),
        type: 'candlestick', xaxis: 'x', yaxis: 'y'
      };
      const sma20 = { x: dates, y: data.rows.map(r=>r.sma_20), mode:'lines', name:'SMA20', line:{color:'blue'}};
      const sma50 = { x: dates, y: data.rows.map(r=>r.sma_50), mode:'lines', name:'SMA50', line:{color:'orange'}};
      const layout = {
        title: sym,
        margin: { t: 30 },
        xaxis: {
          rangeslider: { visible: false },
          rangeselector: { buttons: [
            {count: 7, label: '7d', step: 'day', stepmode: 'backward'},
            {count: 1, label: '1m', step: 'month', stepmode: 'backward'},
            {count: 3, label: '3m', step: 'month', stepmode: 'backward'},
            {count: 1, label: 'YTD', step: 'year', stepmode: 'todate'},
            {step: 'all'}
          ]}
        }
      };
      if (window.Plotly && chartRef.current) {
        window.Plotly.newPlot(chartRef.current, [trace, sma20, sma50], layout, {displayModeBar: true});
      }
    } catch (e) { console.error(e); }
  }

  function toggleLocalWatch(sym) {
    const next = watchlistLocal.includes(sym) ? watchlistLocal.filter(s=>s!==sym) : [...watchlistLocal, sym];
    setWatchlistLocal(next);
    try { localStorage.setItem('tb_watchlist', JSON.stringify(next)); } catch(e){}
    // Keep server watchlist in sync (add only)
    if (!watchlistServer.find(w=>w.symbol===sym)) addWatch(sym);
  }

  async function quickEnter(r) {
    try {
      let entry_price = 0;
      try {
        const res = await fetch(`/api/ohlc?symbol=${r.symbol}&days=7`);
        if (res.ok) {
          const d = await res.json();
          const rows = d.rows || [];
          if (rows.length) entry_price = rows[rows.length - 1].close || entry_price;
        }
      } catch(e){}
      const payload = { symbol: r.symbol, entry_date: new Date().toISOString(), entry_price: entry_price, size: 1 };
      await fetch('/api/positions', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      alert(`Position entered for ${r.symbol}`);
      await fetchPositions();
    } catch (e) { alert('Failed to enter position'); }
  }

  const filtered = useMemo(() => {
    let arr = (results || []).slice();
    if (filterText) arr = arr.filter(r => r.symbol.toLowerCase().includes(filterText.toLowerCase()));
    if (minScore) arr = arr.filter(r => (r.score||0) >= Number(minScore));
    arr.sort((a,b) => {
      const va = a[sortBy] ?? 0; const vb = b[sortBy] ?? 0;
      if (va === vb) return 0;
      return sortDir === 'asc' ? (va < vb ? -1:1) : (va > vb ? -1:1);
    });
    return arr;
  }, [results, filterText, minScore, sortBy, sortDir]);

  function setSort(col) {
    if (sortBy === col) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortBy(col); setSortDir('desc'); }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="card">
          <div className="header"><div className="brand">TradingBuddy</div><div className="small muted">Screener</div></div>
          <div style={{marginBottom:8}}>
            <input className="search" placeholder="Add symbol to watchlist (e.g. AAPL)" value={watchInput} onChange={e=>setWatchInput(e.target.value.toUpperCase())} />
            <div style={{marginTop:8, display:'flex', gap:8}}>
              <button className="btn" onClick={()=>{ setWatchInput(''); fetchData(); }}>Refresh</button>
              <button className="btn primary" onClick={()=>{ if (watchInput) { addWatch(watchInput); setWatchInput(''); } }}>Add</button>
            </div>
          </div>
          <h4 className="small muted">Watchlist</h4>
          <div>
            {watchlistServer.length === 0 && <div className="muted small">No items. Add symbols above.</div>}
            {watchlistServer.map(w => (
              <div key={w.id} className="watch-item">
                <div style={{display:'flex',gap:8,alignItems:'center'}}>
                  <a href="#" onClick={(e)=>{e.preventDefault(); handleSymbolClick(w.symbol);}} className="sym">{w.symbol}</a>
                  <div className="small muted">{w.notes}</div>
                </div>
                <div style={{display:'flex',gap:6}}>
                  <button className="btn" onClick={()=>removeWatch(w.id)}>Remove</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="header"><div className="small muted">Positions</div><div className="small muted">{positions.length}</div></div>
          {positions.length === 0 && <div className="muted small">No open positions</div>}
          {positions.map(p => (
            <div key={p.id} className="pos-item">
              <div>
                <div style={{fontWeight:600}}>{p.symbol}</div>
                <div className="small muted">{p.entry_date.split('T')[0]} • {p.size} @ {p.entry_price}</div>
              </div>
              <div style={{display:'flex',flexDirection:'column',gap:6}}>
                <button className="btn" onClick={()=>closePosition(p.id)}>Close</button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <main>
        <div className="card">
          <div className="header">
            <div>
              <div className="brand">Top Candidates</div>
              <div className="small muted">Click a row to load the chart</div>
            </div>
            <div className="controls">
              <label className="small muted">Top <input style={{width:64,marginLeft:6}} type="number" value={limit} onChange={e=>setLimit(Number(e.target.value||0))} /></label>
              <button className="btn" onClick={fetchData} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh'}</button>
              <button className="btn" onClick={handleManualUpdate}>Run update</button>
            </div>
          </div>

          <div style={{marginTop:6}}>
            <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:8}}>
              <input className="search" placeholder="Filter symbol" value={filterText} onChange={e=>setFilterText(e.target.value)} />
              <input className="search" style={{width:110}} placeholder="Min score" type="number" value={minScore} onChange={e=>setMinScore(Number(e.target.value||0))} />
            </div>
            {error && <div style={{ color: 'crimson' }}>{error}</div>}

            <table>
              <thead>
                <tr>
                  <th>Sym</th>
                  <th onClick={()=>setSort('score')}>Score {sortBy==='score' ? (sortDir==='asc'?'▲':'▼') : ''}</th>
                  <th>%</th>
                  <th>RSI</th>
                  <th>SMA20</th>
                  <th>SMA50</th>
                  <th>Spark</th>
                  <th>Watch</th>
                  <th>Enter</th>
                </tr>
              </thead>
                <tbody>
                  {(() => {
                    const seen = new Set();
                    return filtered.filter(r => {
                      if (seen.has(r.symbol)) return false;
                      seen.add(r.symbol);
                      return true;
                    }).map(r => (
                      <tr key={r.symbol} style={{cursor:'pointer'}}>
                    <td><a href="#" onClick={(e)=>{e.preventDefault(); handleSymbolClick(r.symbol);}}>{r.symbol}</a></td>
                    <td style={{textAlign:'center'}}>{r.score}</td>
                    <td style={{textAlign:'center'}}>{r.pct_change}</td>
                    <td style={{textAlign:'center'}}>{r.rsi}</td>
                    <td style={{textAlign:'center'}}>{r.sma20}</td>
                    <td style={{textAlign:'center'}}>{r.sma50}</td>
                    <td style={{textAlign:'center'}}><div className="spark"><Sparkline symbol={r.symbol} /></div></td>
                    <td style={{textAlign:'center'}}><button className="btn" onClick={()=>toggleLocalWatch(r.symbol)}>{watchlistLocal.includes(r.symbol) ? 'Watching' : 'Watch'}</button></td>
                    <td style={{textAlign:'center'}}><button className="btn primary" onClick={()=>quickEnter(r)}>Enter</button></td>
                    </tr>
                  ))
                })()}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card chart-area" style={{marginTop:16}}>
          <h4 style={{margin:0}}>{selected ? `Chart: ${selected}` : 'Click a symbol to load chart'}</h4>
          <div ref={chartRef} style={{height:420, marginTop:12}}></div>
        </div>
      </main>
    </div>
  );
}

export default App;
