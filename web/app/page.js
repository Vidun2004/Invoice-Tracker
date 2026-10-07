"use client";
import { useEffect, useMemo, useState } from "react";
import { Camera, CheckCircle2, Inbox, LogOut, Receipt, RefreshCw } from "lucide-react";
import { supabase, nextStage } from "../lib/supabaseClient";

const CSS = `
.it-page{min-height:100vh;padding:12px 12px 96px}
.it-wrap{max-width:1040px;margin:0 auto}
.it-top{position:sticky;top:0;z-index:5;background:rgba(238,242,247,.92);backdrop-filter:blur(8px);padding:10px 0}
.it-brand{display:flex;align-items:center;gap:10px}
.it-logo{width:40px;height:40px;border-radius:12px;background:#0f172a;color:#fff;display:grid;place-items:center}
.it-logo svg{width:22px;height:22px}
.it-ic{width:16px;height:16px;vertical-align:-3px}
.it-ibtn{display:inline-flex;align-items:center;gap:8px;justify-content:center}
.it-title{font-size:18px;font-weight:800;margin:0}
.it-sub{font-size:12px;color:#64748b;margin:0}
.it-steps{display:flex;gap:6px;margin-top:10px}
.it-step{flex:1;font-size:12px;font-weight:700;padding:8px;border-radius:999px;background:#e2e8f0;color:#64748b;text-align:center}
.it-step.on{background:#0f172a;color:#fff}
.it-step.done{background:#dcfce7;color:#15803d}
.it-grid{display:grid;gap:12px;margin-top:12px;grid-template-columns:1fr}
@media(min-width:900px){.it-grid{grid-template-columns:1.1fr .9fr}.it-page{padding-bottom:24px}}
.it-card{background:#fff;border-radius:18px;padding:16px;box-shadow:0 1px 6px rgba(15,23,42,.08);border:1px solid #e6ebf2}
.it-h{font-size:15px;font-weight:800;margin:0 0 4px}
.it-p{font-size:13px;color:#64748b;margin:0 0 10px}
.it-search{width:100%;padding:13px 14px;border-radius:12px;border:1px solid #cbd5e1;font-size:16px;box-sizing:border-box;background:#f8fafc}
.it-refresh{width:100%;margin-top:8px;background:#0f172a;color:#fff;border:0;border-radius:12px;padding:13px;font-size:15px;font-weight:700;min-height:48px}
.it-refresh:disabled{opacity:.6}
.it-list{max-height:52vh;overflow:auto;margin-top:10px;display:flex;flex-direction:column;gap:8px}
.it-item{text-align:left;width:100%;padding:12px 14px;border-radius:14px;border:2px solid #e6ebf2;background:#f8fafc;cursor:pointer}
.it-item small{color:#64748b}
.it-item.sel{border-color:#2563eb;background:#eff6ff}
.it-item b{font-size:16px}
.it-empty{padding:24px;text-align:center;color:#64748b;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:14px}
.it-skel{height:64px;border-radius:14px;background:linear-gradient(90deg,#eef2f7,#e2e8f0,#eef2f7);background-size:200% 100%;animation:sh 1.2s infinite}
@keyframes sh{to{background-position:-200% 0}}
.it-drop{display:block;text-align:center;background:#0f172a;color:#fff;border-radius:14px;padding:16px;font-weight:800;cursor:pointer;min-height:52px}
.it-preview{width:100%;border-radius:14px;margin-top:10px;border:1px solid #e2e8f0}
.it-submit{width:100%;margin-top:10px;background:#2563eb;color:#fff;border:0;border-radius:14px;padding:15px;font-size:16px;font-weight:800;min-height:52px}
.it-submit:disabled{opacity:.45}
.it-bar{position:fixed;left:0;right:0;bottom:0;padding:10px 12px calc(10px + env(safe-area-inset-bottom));background:rgba(255,255,255,.95);border-top:1px solid #e2e8f0;backdrop-filter:blur(8px)}
@media(min-width:900px){.it-bar{position:static;background:none;border:0;padding:0;margin-top:10px}}
.it-err{background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;border-radius:12px;padding:10px 12px;font-size:14px;margin-top:10px}
.it-ok{background:#f0fdf4;border:1px solid #bbf7d0;color:#15803d;border-radius:12px;padding:10px 12px;font-size:14px;margin-top:10px}
.it-prog{height:8px;background:#e2e8f0;border-radius:99px;overflow:hidden;margin-top:10px}
.it-prog>div{height:100%;background:#2563eb;width:0%;transition:width .3s}
.it-signout{border:1px solid #cbd5e1;background:#fff;border-radius:10px;padding:10px 14px;min-height:44px;font-size:14px}
.spin{display:inline-block;width:16px;height:16px;border:2px solid #cbd5e1;border-top-color:#2563eb;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle}
.spin.w{border-top-color:#fff}
@keyframes spin{to{transform:rotate(360deg)}}
`;

async function compressImage(file) {
  try {
    const bmp = await createImageBitmap(file);
    const maxSide = 1280;
    const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.82));
    return blob || file;
  } catch {
    return file;
  }
}

const STEP_PCT = { "": 0, "1/4 Compressing photo…": 25, "2/4 Uploading photo…": 50, "3/4 Saving proof…": 75, "4/4 Marking SentToFinance…": 95 };

export default function Page() {
  const [session, setSession] = useState(null);
  const [authCheck, setAuthCheck] = useState(true);
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [q, setQ] = useState("");
  const [invoices, setInvoices] = useState([]);
  const [listBusy, setListBusy] = useState(false);
  const [sel, setSel] = useState(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState("");
  const [done, setDone] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setAuthCheck(false); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  async function login(e) {
    e.preventDefault();
    setMsg("");
    setLoginBusy(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
      if (error) setMsg(error.message);
    } finally {
      setLoginBusy(false);
    }
  }

  async function loadEligible() {
    setMsg("");
    setListBusy(true);
    try {
      const { data, error } = await supabase.from("eligible_for_finance").select("*").limit(100);
      if (error) return setMsg(error.message);
      setInvoices(data || []);
    } finally {
      setListBusy(false);
    }
  }

  useEffect(() => {
    if (session) {
      const pre = new URLSearchParams(window.location.search).get("invoice");
      if (pre) setQ(pre);
      loadEligible();
    }
  }, [session]);

  const filtered = useMemo(() => invoices.filter((r) =>
    !q || `${r.invoice_number} ${r.vendor_name}`.toLowerCase().includes(q.toLowerCase())), [invoices, q]);

  function onFile(e) {
    const f = e.target.files?.[0];
    setFile(f || null);
    setDone(null);
    setMsg("");
    if (f) setPreview(URL.createObjectURL(f));
  }

  async function submit() {
    if (!sel) return setMsg("Select an invoice first.");
    if (!file) return setMsg("Take or choose a photo first.");
    if (nextStage(sel.type, sel.current_stage) !== "SentToFinance")
      return setMsg(`Invoice is in ${sel.current_stage}, not eligible anymore. Refresh list.`);
    setBusy(true);
    setMsg("");
    try {
      const capturedAt = new Date().toISOString();
      const path = `proofs/${sel.invoice_number}/${Date.now()}.jpg`;
      setStep("1/4 Compressing photo…");
      const small = await compressImage(file);
      setStep("2/4 Uploading photo…");
      const { error: upErr } = await supabase.storage.from("finance-proofs").upload(path, small, {
        contentType: "image/jpeg", upsert: false,
      });
      if (upErr) throw upErr;
      setStep("3/4 Saving proof…");
      const { data: { user } } = await supabase.auth.getUser();
      await supabase.from("finance_proofs").insert({
        invoice_id: sel.id, photo_path: path, captured_at: capturedAt,
        uploaded_by: user?.id || null,
        device_info: navigator.userAgent.slice(0, 200),
      });
      setStep("4/4 Marking SentToFinance…");
      const { error: invErr } = await supabase.from("invoices").update({ current_stage: "SentToFinance" }).eq("id", sel.id);
      if (invErr) throw invErr;
      await supabase.from("audit_log").insert({
        invoice_id: sel.id, from_stage: sel.current_stage, to_stage: "SentToFinance",
        action: "stage_change", note: `photo proof ${path}`, source: "web", actor: user?.id || null,
      });
      setDone({ number: sel.invoice_number, at: new Date(capturedAt).toLocaleString(), path });
      setSel(null); setFile(null); setPreview(null);
      loadEligible();
    } catch (err) {
      setMsg(err.message);
    } finally {
      setBusy(false);
      setStep("");
    }
  }

  const css = <style dangerouslySetInnerHTML={{ __html: CSS }} />;
  const stepIdx = !sel ? 0 : !done ? 1 : 2;

  if (authCheck) {
    return <div className="it-page"><div className="it-wrap"><div className="it-card"><span className="spin" /> Checking session…</div></div>{css}</div>;
  }

  if (!session) {
    return (
      <div className="it-page"><div className="it-wrap">
        <div className="it-card" style={{ maxWidth: 420, margin: "8vh auto" }}>
          <div className="it-brand"><div className="it-logo"><Receipt size={22} /></div>
            <div><p className="it-title">Invoice Tracker</p><p className="it-sub">Finance proof · photo upload</p></div>
          </div>
          <form onSubmit={login} style={{ marginTop: 14 }}>
            <input className="it-search" placeholder="Email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <div style={{ height: 8 }} />
            <input className="it-search" type="password" placeholder="Password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} />
            <div style={{ height: 10 }} />
            <button className="it-submit" type="submit" disabled={loginBusy}>
              {loginBusy ? <span><span className="spin w" /> Signing in…</span> : "Sign in"}
            </button>
          </form>
          {msg && <div className="it-err">{msg}</div>}
        </div>
      </div>{css}</div>
    );
  }

  return (
    <div className="it-page"><div className="it-wrap">
      <div className="it-top">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="it-brand"><div className="it-logo"><Camera size={22} /></div>
            <div><p className="it-title">Send to Finance</p><p className="it-sub">Pick invoice → photo → auto SentToFinance</p></div>
          </div>
          <button className="it-signout it-ibtn" onClick={() => supabase.auth.signOut()}><LogOut className="it-ic" size={16} /> Sign out</button>
        </div>
        <div className="it-steps">
          <div className={`it-step ${stepIdx >= 0 ? "on" : ""}`}>1 · Pick</div>
          <div className={`it-step ${stepIdx >= 1 ? "on" : ""}`}>2 · Photo</div>
          <div className={`it-step ${done ? "done" : ""}`}>3 · Done</div>
        </div>
      </div>

      <div className="it-grid">
        <div className="it-card">
          <p className="it-h">Invoices ready for finance · {filtered.length}</p>
          <p className="it-p">{sel ? `Selected: ${sel.invoice_number}` : "Tap an invoice to select it."}</p>
          <input className="it-search" placeholder="Search number / vendor…" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="it-refresh it-ibtn" onClick={loadEligible} disabled={listBusy}>
            {listBusy ? "Loading invoices…" : <span><RefreshCw className="it-ic" size={16} /> Refresh list</span>}
          </button>
          <div className="it-list">
            {listBusy ? (<><div className="it-skel" /><div className="it-skel" /><div className="it-skel" /></>) :
              filtered.map((r) => (
                <button key={r.id} className={`it-item ${sel?.id === r.id ? "sel" : ""}`}
                  onClick={() => { setSel(r); setDone(null); setMsg(""); }}>
                  <b>{r.invoice_number}</b><br />
                  <small>{r.vendor_name} · {r.currency} {r.amount} · {r.type} · {r.current_stage}</small>
                </button>
              ))}
            {!listBusy && !filtered.length && (
              <div className="it-empty"><Inbox size={28} /><br />No eligible invoices.<br /><small>Standard needs GRN · Straight needs Created.</small></div>
            )}
          </div>
        </div>

        <div className="it-card">
          <p className="it-h">Photo proof {sel ? `· ${sel.invoice_number}` : ""}</p>
          <p className="it-p">Captured date/time + invoice number are saved automatically.</p>
          <label className="it-drop it-ibtn"><Camera className="it-ic" size={18} /> Take / choose photo
            <input type="file" accept="image/*" capture="environment" onChange={onFile} style={{ display: "none" }} />
          </label>
          {preview && <img src={preview} alt="preview" className="it-preview" />}
          {busy && <div className="it-prog"><div style={{ width: `${STEP_PCT[step] || 10}%` }} /></div>}
          {busy && <p className="it-p">{step}</p>}
          {msg && <div className="it-err">{msg}</div>}
          {done && <div className="it-ok"><CheckCircle2 className="it-ic" size={16} /> {done.number} sent to finance at {done.at}<br /><small>{done.path}</small></div>}
          <div className="it-bar">
            <button className="it-submit" onClick={submit} disabled={busy || !sel || !file}>
              {busy ? <span><span className="spin w" /> {step || "Uploading…"}</span> : "Upload & mark SentToFinance"}
            </button>
          </div>
        </div>
      </div>
      {css}
    </div></div>
  );
}
