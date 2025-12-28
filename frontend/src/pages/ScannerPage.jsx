import React, { useEffect, useRef, useState } from 'react';

export default function ScannerPage() {
  const barRef = useRef(null);
  const heatRef = useRef(null);
  const [symbolsInput, setSymbolsInput] = useState('AAPL,MSFT,GOOG');
  const [lastError, setLastError] = useState(null);
  // Indicator config UI state
  const [ema50, setEma50] = useState(true);
  const [ema200, setEma200] = useState(true);
  const [rsiEnabled, setRsiEnabled] = useState(true);
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [configName, setConfigName] = useState('');
  const [configs, setConfigs] = useState([]);
  const [renderedUrl, setRenderedUrl] = useState(null);

  async function runScanner() {
    setLastError(null);
    try {
      const symbols = symbolsInput.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      const qs = new URLSearchParams({ symbols: symbols.join(',') });
      const res = await fetch(`/api/scanner?${qs.toString()}`);
      if (!res.ok) throw new Error('scanner failed');
      const data = await res.json();

      // Build simple clickable list and heatgrid instead of Plotly
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
          el.onclick = () => { renderChart(d.symbol); };
          list.appendChild(el);
        });
        container.appendChild(list);
      }
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
            cell.onclick = () => { renderChart(d.symbol); };
          grid.appendChild(cell);
        });
        heat.appendChild(grid);
      }

      if (data.length) {
        // use server-rendered PNG by default
        renderChart(data[0].symbol);
      }
    } catch (e) {
      console.error(e); setLastError(String(e));
    }
  }

  // Load saved chart configs from server
  async function loadConfigs(){
    try{
      const res = await fetch('/api/chart/configs');
      if (!res.ok) return;
      const d = await res.json();
      setConfigs(d.items || []);
    }catch(e){ console.error('loadConfigs', e); }
  }

  // no TradingView: use finplot-backed server rendering

  // Save current UI indicator selection as a named config
  async function saveConfig(){
    if (!configName || !configName.trim()) { alert('Please provide a name for the config'); return; }
    const indicators = { sma: [], ema: [], rsi: null };
    if (ema50) indicators.ema.push(50);
    if (ema200) indicators.ema.push(200);
    if (rsiEnabled) indicators.rsi = Number(rsiPeriod) || 14;
    const payload = { name: configName.trim(), config: indicators };
    try{
      const res = await fetch('/api/chart/config', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || 'failed');
      }
      await loadConfigs();
      setConfigName('');
      alert('Config saved');
    }catch(e){ console.error('saveConfig', e); alert('Failed to save config: '+e.message); }
  }

  async function loadConfig(name){
    try{
      const res = await fetch(`/api/chart/config/${encodeURIComponent(name)}`);
      if (!res.ok) { alert('Failed to load config'); return; }
      const d = await res.json();
      const cfg = d.config || {};
      // apply
      setEma50((cfg.ema||[]).includes(50));
      setEma200((cfg.ema||[]).includes(200));
      setRsiEnabled(Boolean(cfg.rsi));
      setRsiPeriod(cfg.rsi || 14);
      alert('Config applied to UI');
    }catch(e){ console.error('loadConfig', e); alert('Failed to load config'); }
  }

  async function deleteConfig(name){
    if (!confirm(`Delete config ${name}?`)) return;
    try{
      const res = await fetch(`/api/chart/config/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('delete failed');
      await loadConfigs();
    }catch(e){ console.error('deleteConfig', e); alert('Failed to delete'); }
  }

  // Render a chart PNG using either the named config or current UI selection
  async function renderChart(symbol, useConfigName=null){
    setRenderedUrl(null);
    setLastError(null);
    try{
      const payload = { symbol, days: 365 };
      if (useConfigName) payload.config_name = useConfigName;
      else {
        const indicators = { ema: [], rsi: null };
        if (ema50) indicators.ema.push(50);
        if (ema200) indicators.ema.push(200);
        if (rsiEnabled) indicators.rsi = Number(rsiPeriod) || 14;
        payload.indicators = indicators;
      }
      const res = await fetch('/api/chart/render', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      if (!res.ok){ const txt = await res.text(); throw new Error(txt || 'render failed'); }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setRenderedUrl(url);
    }catch(e){ console.error('renderChart', e); setLastError(String(e)); alert('Render failed: '+e.message); }
  }

  function calculateRSI(closes, period = 14) {
    if (!closes || closes.length <= period) return [];
    let gains = 0, losses = 0;
    for (let i = 1; i <= period; i++) { const diff = closes[i] - closes[i - 1]; if (diff > 0) gains += diff; else losses += Math.abs(diff); }
    let avgGain = gains / period, avgLoss = losses / period;
    const out = [];
    for (let i = period; i < closes.length; i++) {
      if (i > period) { const diff = closes[i] - closes[i - 1]; avgGain = (avgGain * (period - 1) + Math.max(diff, 0)) / period; avgLoss = (avgLoss * (period - 1) + Math.max(-diff, 0)) / period; }
      if (avgLoss === 0) out.push(100); else { const rs = avgGain / avgLoss; out.push(100 - (100 / (1 + rs))); }
    }
    return out;
  }

  useEffect(() => { runScanner(); }, []);
  useEffect(()=>{ loadConfigs(); }, []);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <input style={{ flex: 1, padding: 8 }} value={symbolsInput} onChange={e => setSymbolsInput(e.target.value)} />
        <button onClick={runScanner} style={{ padding: '8px 12px' }}>Run Scanner</button>
  {/* TradingView removed: using server-rendered finplot images */}
      </div>

      {/* Indicator config UI */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <label><input type="checkbox" checked={ema50} onChange={e=>setEma50(e.target.checked)} /> EMA 50</label>
          <label><input type="checkbox" checked={ema200} onChange={e=>setEma200(e.target.checked)} /> EMA 200</label>
          <label style={{display:'flex',alignItems:'center',gap:6}}><input type="checkbox" checked={rsiEnabled} onChange={e=>setRsiEnabled(e.target.checked)} /> RSI</label>
          <input style={{width:64}} value={rsiPeriod} onChange={e=>setRsiPeriod(Number(e.target.value||14))} />
        </div>

        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          <input placeholder='Config name' value={configName} onChange={e=>setConfigName(e.target.value)} />
          <button className='btn' onClick={saveConfig}>Save Config</button>
          <button className='btn' onClick={()=>{ const s = symbolsInput.split(',')[0].trim().toUpperCase(); renderChart(s); }}>Render Current</button>
        </div>
      </div>

      {/* Saved configs list and rendered image */}
      <div style={{ marginBottom: 12 }}>
        <div style={{fontWeight:700}}>Saved Configs</div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:8}}>
          {configs.map(c => (
            <div key={c.name} style={{border:'1px solid #eee',padding:8,borderRadius:6}}>
              <div style={{fontWeight:600}}>{c.name}</div>
              <div style={{fontSize:12,color:'#666'}}>{c.created_at}</div>
              <div style={{display:'flex',gap:6,marginTop:6}}>
                <button className='btn' onClick={()=>loadConfig(c.name)}>Load</button>
                <button className='btn' onClick={()=>renderChart(symbolsInput.split(',')[0].trim().toUpperCase(), c.name)}>Render</button>
                <button className='btn' onClick={()=>deleteConfig(c.name)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div ref={barRef} style={{ minHeight: 260 }}></div>
        <div ref={heatRef} style={{ minHeight: 260 }}></div>
      </div>

      <div style={{ marginTop: 12 }}>
        {lastError && <div style={{ color: 'crimson', marginTop: 8 }}>{lastError}</div>}
      </div>
    </div>
  );
}
