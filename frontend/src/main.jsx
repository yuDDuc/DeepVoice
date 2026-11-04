import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

const API=import.meta.env.VITE_API_URL||'http://localhost:8000';

function App(){
 const [token,setToken]=useState(localStorage.getItem('deepvoice_token')||'');
 const [email,setEmail]=useState(''); const [password,setPassword]=useState('');
 const [authMode,setAuthMode]=useState('login'); const [authError,setAuthError]=useState('');
 const [file,setFile]=useState(null); const [result,setResult]=useState(null); const [busy,setBusy]=useState(false);
 async function auth(){setAuthError('');try{const r=await fetch(`${API}/api/v1/auth/${authMode}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Authentication failed');localStorage.setItem('deepvoice_token',d.access_token);setToken(d.access_token)}catch(e){setAuthError(e.message)}}
 async function run(){if(!file)return;setBusy(true);setResult(null);const f=new FormData();f.append('file',file);const headers=token?{Authorization:`Bearer ${token}`}:{ };try{const r=await fetch(`${API}/api/v1/inference`,{method:'POST',headers,body:f});const d=await r.json();if(!r.ok)throw new Error(d.detail||'Inference failed');setResult(d)}catch(e){setResult({error:e.message})}finally{setBusy(false)}}
 return <main><header><h1>DeepVoice</h1><span>ASR + Machine Translation</span>{token?<button className="logout" onClick={()=>{localStorage.removeItem('deepvoice_token');setToken('')}}>Đăng xuất</button>:null}</header>
 {!token&&<section className="auth card"><h2>{authMode==='login'?'Đăng nhập':'Tạo tài khoản'}</h2><input type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)}/><input type="password" placeholder="Mật khẩu (tối thiểu 8 ký tự)" value={password} onChange={e=>setPassword(e.target.value)}/><button onClick={auth}>{authMode==='login'?'Đăng nhập':'Đăng ký'}</button><button className="link" onClick={()=>setAuthMode(authMode==='login'?'register':'login')}>{authMode==='login'?'Chưa có tài khoản? Đăng ký':'Đã có tài khoản? Đăng nhập'}</button>{authError&&<p className="error">{authError}</p>}<p className="hint">Local mode vẫn cho phép dịch không đăng nhập nếu <code>AUTH_REQUIRED=false</code>.</p></section>}
 <section className="card"><h2>Inference</h2><input type="file" accept="audio/*" onChange={e=>setFile(e.target.files[0])}/><button onClick={run} disabled={!file||busy}>{busy?'Đang xử lý…':'Dịch audio'}</button>{result?.error&&<p className="error">{result.error}</p>}{result&&!result.error&&<div className="result"><label>Transcript</label><p>{result.transcript}</p><label>Translation</label><p>{result.translation}</p><small>Latency: {result.metrics.latency_ms} ms · CPU: {result.metrics.after.cpu_percent ?? 'n/a'}% · RAM: {result.metrics.after.ram_percent ?? 'n/a'}%</small></div>}</section></main>
}
createRoot(document.getElementById('root')).render(<App/>);
