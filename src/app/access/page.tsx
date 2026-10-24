"use client";
import { FormEvent, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function AccessForm() {
  const router = useRouter(); const params = useSearchParams(); const [password, setPassword] = useState(""); const [message, setMessage] = useState(""); const [loading, setLoading] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setLoading(true); setMessage(""); try { const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password }) }); if (!response.ok) { const data = await response.json(); setMessage(data.message ?? "設定上の理由によりログインできません。"); return; } const next = params.get("next"); router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/"); router.refresh(); } catch { setMessage("接続に失敗しました。再度お試しください。"); } finally { setLoading(false); } };
  return <main className="access-page"><section className="access-card" aria-labelledby="access-title"><p>PRIVATE PRESENTATION SITE</p><h1 id="access-title">KEIBA <i>AI</i></h1><h2>関係者限定アクセス</h2><p className="access-lead">発表会の共有パスワードを入力してください。</p><form onSubmit={submit}><label htmlFor="password">共通パスワード</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={loading}/><button type="submit" disabled={loading}>{loading ? "確認中…" : "サイトを閲覧する"}</button>{message && <p className="access-error" role="alert">{message}</p>}</form><small>アカウント登録は不要です。共有URLとパスワードを許可された関係者以外へ転送しないでください。</small></section></main>;
}

export default function AccessPage() { return <Suspense fallback={<main className="access-page" aria-busy="true"/>}><AccessForm/></Suspense>; }
