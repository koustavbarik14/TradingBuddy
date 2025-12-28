import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import ScannerPage from './pages/ScannerPage';

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
  const [chartUrl, setChartUrl] = useState(null);
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

  function calculateRSI(closes, period=14){
    if (!closes || closes.length <= period) return [];
    let gains = 0, losses = 0;
    for (let i=1;i<=period;i++){ const diff = closes[i] - closes[i-1]; if (diff>0) gains += diff; else losses += Math.abs(diff); }
    let avgGain = gains/period, avgLoss = losses/period;
    const out = [];
    for (let i=period;i<closes.length;i++){
      if (i>period){ const diff = closes[i] - closes[i-1]; avgGain = (avgGain*(period-1) + Math.max(diff,0))/period; avgLoss = (avgLoss*(period-1) + Math.max(-diff,0))/period; }
      if (avgLoss === 0) out.push(100);
      else {
        const rs = avgGain/avgLoss; out.push(100 - (100 / (1 + rs)));
      }
    }
    return out;
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
    setChartUrl(null);
    try {
      // Request server-rendered PNG (uses finplot/mplfinance on server). Default indicators: EMA50, EMA200, RSI(14)
      const payload = { symbol: sym, days: 365, indicators: { ema: [50, 200], rsi: 14 } };
      const res = await fetch('/api/chart/render', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (!res.ok) {
        const text = await res.text();
        alert('Failed to render chart: ' + res.status + ' ' + text);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setChartUrl(url);
    } catch (e) { console.error(e); alert('Failed to render chart: '+e.message); }
  }
  
  /* Scanner embedded in React: uses /api/scanner and displays Plotly charts */
  function ScannerPanel() {
    const barRef = useRef(null);
    const heatRef = useRef(null);
    const [symbolsInput, setSymbolsInput] = useState('');
    useEffect(()=>{ setSymbolsInput(DEFAULT_TICKERS_JOINED()); }, []);

    function DEFAULT_TICKERS_JOINED(){
      // fallback universe similar to backend
      return ['AAPL','AMGN','AXP','BA','CAT','CRM','CSCO','CVX','DIS','DOW','GS','HD','HON','IBM','INTC','JNJ','JPM','KO','MCD','MMM','MRK','MSFT','NKE','PG','TRV','UNH','V','VZ','WBA','WMT'].join(',');
    }

    async function runScanner(){
      try{
        const symbols = symbolsInput.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean);
        const qs = new URLSearchParams({ symbols: symbols.join(',') });
        const res = await fetch(`/api/scanner?${qs.toString()}`);
        if (!res.ok) throw new Error('scanner failed');
        const data = await res.json();
        // Render a simple clickable list instead of Plotly charts
        const container = barRef.current;
        if (container) {
          container.innerHTML = '';
          const list = document.createElement('div');
          list.style.display = 'grid';
          list.style.gridTemplateColumns = 'repeat(auto-fit, minmax(120px,1fr))';
          list.style.gap = '8px';
          data.forEach(d => {
            const el = document.createElement('div');
            el.style.border = '1px solid #eee';
            el.style.padding = '8px';
            el.style.borderRadius = '6px';
            el.style.cursor = 'pointer';
            el.innerHTML = `<div style="font-weight:600">${d.symbol}</div><div style="color:#666">${(d.final_score||0).toFixed(3)}</div>`;
            el.onclick = () => showTickerChart(d.symbol);
            list.appendChild(el);
          });
          container.appendChild(list);
        }
        // heatmap area: show simple grid of symbols colored by score
        const heat = heatRef.current;
        if (heat) {
          heat.innerHTML = '';
          const grid = document.createElement('div');
          grid.style.display = 'grid';
          grid.style.gridTemplateColumns = 'repeat(6, 1fr)';
          grid.style.gap = '6px';
          data.forEach(d => {
            const cell = document.createElement('div');
            const v = d.final_score || 0;
            const green = Math.max(0, Math.round(150 * v));
            const red = Math.max(0, Math.round(150 * -v));
            cell.style.background = `rgb(${red},${green},50)`;
            cell.style.padding = '8px';
            cell.style.borderRadius = '4px';
            cell.style.color = '#fff';
            cell.style.fontWeight = '600';
            cell.style.textAlign = 'center';
            cell.style.cursor = 'pointer';
            cell.innerText = d.symbol;
            cell.onclick = () => showTickerChart(d.symbol);
            grid.appendChild(cell);
          });
          heat.appendChild(grid);
        }
        if (data.length) showTickerChart(data[0].symbol);
      }catch(e){ console.error('runScanner', e); alert('Scanner failed: '+e.message); }
    }

    async function showTickerChart(sym){
      try{
        // request server-rendered PNG for the ticker
        const payload = { symbol: sym, days: 365, indicators: { ema: [50,200], rsi: 14 } };
        const res = await fetch('/api/chart/render', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
        if (!res.ok) { console.error('render failed', await res.text()); return; }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const el = document.getElementById('scanner-ticker');
        if (el && url) {
          el.innerHTML = `<img src="${url}" style="max-width:100%"/>`;
        }
      }catch(e){ console.error(e); }
    }

    return (
      <div className="card">
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input className='search' value={symbolsInput} onChange={e=>setSymbolsInput(e.target.value)} />
          <button className='btn' onClick={runScanner}>Run Scanner</button>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12,marginTop:12}}>
          <div id='scanner-bar' ref={barRef} style={{minHeight:260}}></div>
          <div id='scanner-heat' ref={heatRef} style={{minHeight:260}}></div>
        </div>
        <div id='scanner-ticker' style={{minHeight:420,marginTop:12}}></div>
      </div>
    );
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

  function MainContent(){
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
                <Link to="/scanner" className="btn" style={{marginRight:8}}>Open Scanner</Link>
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

  return (
    <div>
      <nav style={{ padding: 12, background: '#fff', borderBottom: '1px solid #eee' }}>
        <Link to="/" style={{ marginRight: 12, fontWeight: 700 }}>Home</Link>
        <Link to="/scanner" style={{ marginRight: 12 }}>Scanner</Link>
      </nav>
      <div style={{ padding: 16 }}>
        <Routes>
          <Route path="/scanner" element={<ScannerPage />} />
          <Route path="/" element={<MainContent />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
